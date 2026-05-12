"""抓取 mysteel 期货新闻标题 - 每日简报前置数据源

流程：
1. 抓 mysteel 首页/新闻页的期货相关文章链接
2. 对每篇文章提取标题 + 前 200 字摘要
3. 过滤含关键词的
4. 返回结构化数据给 morning.py 使用

调用方式：
  python3 -m tools.news.fetch_news --keywords 螺纹钢,螺纹,钢材
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser

import httpx

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.texts = []
        self._skip = False
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip = True
    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = False
    def handle_data(self, data):
        if not self._skip:
            t = data.strip()
            if len(t) > 10:
                self.texts.append(t)


@dataclass
class NewsItem:
    title: str
    url: str
    summary: str
    date: str


def fetch_mysteel_futures_news(
    keywords: list[str] | None = None,
    limit: int = 15,
) -> list[NewsItem]:
    """从 mysteel 新闻页抓取期货相关文章。

    Args:
        keywords: 过滤关键词列表，如 ['螺纹钢','螺纹','钢材']
        limit: 最多返回几条
    """
    if keywords is None:
        keywords = ["螺纹钢", "螺纹", "黑色", "期货", "钢材", "铁矿"]

    url = "https://news.mysteel.com/"
    items = []

    try:
        r = httpx.get(url, timeout=10, follow_redirects=True, headers=HEADERS)
        # 提取文章链接和标题
        pattern = r'href="(https://news\.mysteel\.com/a/[^"]+)"\s+title="([^"]+)"'
        matches = re.findall(pattern, r.text)

        seen_urls = set()
        for article_url, title in matches:
            if article_url in seen_urls:
                continue
            seen_urls.add(article_url)

            # 关键词过滤
            if not any(kw in title for kw in keywords):
                continue

            # 从 URL 提取日期
            date_match = re.search(r'/(\d{6})(\d{2})/', article_url)
            date_str = ""
            if date_match:
                ym = date_match.group(1)
                day = date_match.group(2)
                date_str = f"20{ym[:2]}-{ym[2:]}-{day}"

            # 抓文章摘要（前 200 字）
            summary = _fetch_article_summary(article_url)

            items.append(NewsItem(
                title=title,
                url=article_url,
                summary=summary,
                date=date_str,
            ))

            if len(items) >= limit:
                break

    except Exception as e:
        print(f"⚠️ mysteel 抓取失败: {e}")

    return items


def _fetch_article_summary(url: str, max_chars: int = 500) -> str:
    """抓单篇文章前 500 字作为摘要。"""
    try:
        r = httpx.get(url, timeout=8, follow_redirects=True, headers=HEADERS)
        parser = _TextExtractor()
        parser.feed(r.text)
        # 跳过导航/广告，取中间段
        content = " ".join(parser.texts)
        # 简单清理
        content = re.sub(r'©.*?保留所有权利', '', content)
        content = re.sub(r'免责声明.*', '', content)
        return content[:max_chars].strip()
    except Exception:
        return ""


def format_news_for_llm(items: list[NewsItem]) -> str:
    """格式化新闻列表，适合喂给 LLM 做情绪分析。"""
    if not items:
        return "暂无相关新闻"
    lines = []
    for i, item in enumerate(items, 1):
        lines.append(f"{i}. [{item.date}] {item.title}")
        if item.summary:
            lines.append(f"   摘要：{item.summary[:200]}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    kw = sys.argv[1].split(",") if len(sys.argv) > 1 else ["螺纹钢"]
    print(f"关键词：{kw}\n")
    items = fetch_mysteel_futures_news(keywords=kw)
    print(f"找到 {len(items)} 条相关新闻：\n")
    for item in items:
        print(f"[{item.date}] {item.title}")
        print(f"  URL: {item.url}")
        if item.summary:
            print(f"  摘要: {item.summary[:150]}")
        print()
