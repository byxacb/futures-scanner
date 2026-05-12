"""新闻情绪分析 - 用用户提供的 LLM API 给品种相关新闻打情绪分

流程：
1. fetch_news(keywords): 抓主流财经媒体头条 + 过滤含关键词的
2. analyze_sentiment(headlines, symbol): 调 LLM 返回 -1.0 到 +1.0 的情绪分 + 简短理由

支持的 LLM：DeepSeek（默认）、智谱、豆包。
API Key 从 .env 读取，绝不硬编码。
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import httpx

logger = logging.getLogger(__name__)


def _load_env():
    """从 tools/.env 加载环境变量。.env 始终覆盖 shell——
    因为 .env 是用户为本项目专门配置的，shell 里的同名变量经常是其它用途。"""
    env_file = Path(__file__).parent.parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()


_load_env()


@dataclass
class SentimentResult:
    symbol: str
    score: float  # -1.0 (极空) 到 +1.0 (极多)
    confidence: float  # 0-1，LLM 自评把握度
    summary: str  # 1-2 句话总结新闻面
    top_factors: list[str]  # 关键因素
    headlines_used: int


def call_deepseek(messages: list[dict], model: str = "deepseek-chat") -> str:
    """调 DeepSeek Chat API。"""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY 未设置。请填入 tools/.env")

    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 600,
        "response_format": {"type": "json_object"},
    }
    with httpx.Client(timeout=30) as client:
        r = client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


def call_zhipu(messages: list[dict], model: str = "glm-4-flash") -> str:
    """调智谱 GLM-4."""
    api_key = os.getenv("ZHIPU_API_KEY")
    if not api_key:
        raise RuntimeError("ZHIPU_API_KEY 未设置")
    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 600,
    }
    with httpx.Client(timeout=30) as client:
        r = client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


def call_anthropic_compatible(
    messages: list[dict],
    model: str | None = None,
    base_url: str | None = None,
) -> str:
    """调 Anthropic Messages API 兼容协议的 provider。

    支持的服务：
    - 官方 Anthropic（base_url=https://api.anthropic.com）
    - 任何兼容 Messages API 的代理/第三方（如小米 MiMo via token-plan）

    环境变量：
    - ANTHROPIC_API_KEY: 你的 key
    - ANTHROPIC_BASE_URL: 不填默认官方；填了就用代理（如 https://token-plan-cn.xiaomimimo.com/anthropic）
    - ANTHROPIC_MODEL: 模型名（如 mimo-v2.5-pro 或 claude-3-5-sonnet）

    重要：
    - 用户必须自己在 .env 填 key，绝不硬编码
    - Messages API 把 "system" 消息拆出来作为单独的 system 字段
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY 未设置。请填入 tools/.env")

    base = base_url or os.getenv("ANTHROPIC_BASE_URL") or "https://api.anthropic.com"
    base = base.rstrip("/")
    url = f"{base}/v1/messages"
    use_model = model or os.getenv("ANTHROPIC_MODEL") or "claude-3-5-sonnet-latest"

    # Messages API 把 system 拆开
    system_prompt = None
    chat_messages = []
    for m in messages:
        if m["role"] == "system":
            system_prompt = m["content"]
        else:
            chat_messages.append(m)

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": use_model,
        "max_tokens": 800,
        "temperature": 0.1,
        "messages": chat_messages,
    }
    if system_prompt:
        payload["system"] = system_prompt

    with httpx.Client(timeout=60) as client:
        r = client.post(url, headers=headers, json=payload)
        if r.status_code >= 400:
            raise RuntimeError(f"Anthropic-compatible API 错误 {r.status_code}: {r.text[:500]}")
        data = r.json()
        # 解析 content blocks
        blocks = data.get("content", [])
        if not blocks:
            raise RuntimeError(f"返回 content 为空: {data}")
        # 第一个 text block
        for b in blocks:
            if b.get("type") == "text":
                return b["text"]
        raise RuntimeError(f"返回无 text block: {blocks}")


def call_llm(
    messages: list[dict],
    provider: Literal["deepseek", "zhipu", "anthropic"] = "deepseek",
) -> str:
    if provider == "deepseek":
        return call_deepseek(messages)
    elif provider == "zhipu":
        return call_zhipu(messages)
    elif provider == "anthropic":
        return call_anthropic_compatible(messages)
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def analyze_sentiment(
    symbol: str,
    headlines: list[str],
    variety_name: str | None = None,
    provider: Literal["deepseek", "zhipu", "anthropic"] = "deepseek",
) -> SentimentResult:
    """对一批新闻标题给品种打情绪分。

    LLM 严格按 JSON 格式输出，不能含 markdown。
    """
    if not headlines:
        return SentimentResult(
            symbol=symbol,
            score=0.0,
            confidence=0.0,
            summary="无相关新闻",
            top_factors=[],
            headlines_used=0,
        )

    variety_display = variety_name or symbol
    prompt = f"""你是一名中国期货市场分析师。请根据下面这些新闻标题，对【{variety_display}】品种打一个情绪分。

新闻标题（{len(headlines)} 条）：
{chr(10).join(f"{i+1}. {h}" for i, h in enumerate(headlines))}

请严格按以下 JSON 格式输出（不要 markdown 代码块）：
{{
  "score": <数字, -1.0 到 +1.0，越多越看涨>,
  "confidence": <数字, 0 到 1, 你对结论的把握度>,
  "summary": "<一两句话总结当前新闻面情绪>",
  "top_factors": ["关键因素1", "关键因素2", "关键因素3"]
}}

注意：
- 客观，不要预测未来，只总结当下新闻的情绪倾向
- 如果新闻中性或矛盾，score 给 0
- 如果信息不足或不相关，confidence 给 < 0.3"""

    raw = call_llm([{"role": "user", "content": prompt}], provider=provider)

    try:
        # 容错：去掉可能的 markdown 包裹
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        data = json.loads(cleaned.strip())
        return SentimentResult(
            symbol=symbol,
            score=float(data.get("score", 0)),
            confidence=float(data.get("confidence", 0)),
            summary=str(data.get("summary", "")),
            top_factors=list(data.get("top_factors", [])),
            headlines_used=len(headlines),
        )
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error("LLM 输出解析失败: %s\n原文：%s", e, raw)
        return SentimentResult(
            symbol=symbol,
            score=0.0,
            confidence=0.0,
            summary=f"LLM 解析失败: {e}",
            top_factors=[],
            headlines_used=len(headlines),
        )


def fetch_news_headlines(keywords: list[str], limit: int = 20) -> list[str]:
    """从公开财经媒体抓含关键词的头条。

    这是占位实现 - 真实版需要爬财联社/华尔街见闻/东方财富。
    比赛期间可以人工把头条粘贴到一个文件，或用 RSS。
    """
    # TODO: 真实实现
    # - 财联社：https://www.cls.cn/depth?id=1003
    # - 华尔街见闻：https://wallstreetcn.com/news/global
    # - 东方财富：https://finance.eastmoney.com/news.html
    # 都没有官方 API，需要 BeautifulSoup 爬。比赛前再补。
    logger.warning("fetch_news_headlines 是占位实现。请手动喂入 headlines 或扩展爬虫。")
    return []


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_headlines = [
        "央行宣布降准 0.5 个百分点 释放长期资金约 1 万亿元",
        "钢联数据：螺纹社库连续 3 周下降 钢厂利润修复",
        "国常会：加快推进重大基础设施项目落地",
    ]
    print("测试需要在 .env 中配置 DEEPSEEK_API_KEY")
    try:
        result = analyze_sentiment(
            symbol="rb",
            headlines=test_headlines,
            variety_name="螺纹钢",
        )
        print(result)
    except RuntimeError as e:
        print(f"跳过 LLM 测试：{e}")
