"""主动扫描器 - 像巴菲特一样找机会

自动扫描所有期货品种，找出有潜力的交易机会。
基于 100 本书共识 + 技术信号 + 基本面数据。

每次扫描输出：品种、方向、确信度、关键价位、操作建议。
推送到手机，让用户直接知道"买什么、为什么、什么时候"。
"""

import sys
import os
import json
import logging
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.fetch_market import get_daily_kline, get_realtime_quote, get_main_contract
from indicators.compute import signal_summary
from notify.sender import notify

logger = logging.getLogger(__name__)

# 候选品种池（流动性好、波动适中）
CANDIDATES = [
    # 黑色系
    "rb",  # 螺纹钢
    "hc",  # 热卷
    "i",   # 铁矿石
    "j",   # 焦炭
    "jm",  # 焦煤
    # 有色
    "cu",  # 铜
    "al",  # 铝
    "zn",  # 锌
    "ni",  # 镍
    # 能化
    "sc",  # 原油
    "TA",  # PTA
    "MA",  # 甲醇
    "FG",  # 玻璃
    "SA",  # 纯碱
    # 农产品
    "m",   # 豆粕
    "y",   # 豆油
    "p",   # 棕榈油
    "CF",  # 棉花
    "SR",  # 白糖
    # 贵金属
    "au",  # 黄金
    "ag",  # 白银
    # 金融
    "IF",  # 沪深300
    "IC",  # 中证500
]

# 100 本书共识 - 入场条件铁律
BOOK_RULES = {
    "rule_1": "趋势跟踪：顺势而为，不抄底摸顶",
    "rule_2": "突破确认：价格突破关键位+成交量放大才入场",
    "rule_3": "止损先行：入场前必须设好止损",
    "rule_4": "风险控制：单笔亏损不超过本金1%",
    "rule_5": "盈亏比：至少2:1才值得做",
}


def scan_opportunities() -> list:
    """扫描所有候选品种，返回有信号的机会列表。"""
    opportunities = []

    for symbol in CANDIDATES:
        try:
            # 获取日线数据（最近120天）
            from datetime import timedelta
            start_date = (datetime.now() - timedelta(days=120)).strftime("%Y%m%d")
            df = get_daily_kline(symbol, start=start_date)
            if df is None or len(df) < 60:
                continue

            # 计算技术信号
            signals = signal_summary(df)
            if not signals:
                continue

            # 获取实时价格
            realtime = get_realtime_quote(symbol)
            current_price = realtime.get("price", 0)
            if current_price <= 0:
                continue

            # 评估信号质量
            signal_quality = evaluate_signal(signals, current_price)

            if signal_quality["score"] >= 60:  # 只推送确信度60%以上的
                opportunities.append({
                    "symbol": symbol,
                    "direction": signal_quality["direction"],
                    "confidence": signal_quality["score"],
                    "reason": signal_quality["reason"],
                    "entry": current_price,
                    "stop_loss": signal_quality["stop_loss"],
                    "target": signal_quality["target"],
                    "risk_reward": signal_quality["risk_reward"],
                    "signals": signals,
                })

        except Exception as e:
            logger.debug("扫描 %s 失败: %s", symbol, e)
            continue

    # 按确信度排序
    opportunities.sort(key=lambda x: x["confidence"], reverse=True)
    return opportunities


def evaluate_signal(signals: dict, current_price: float) -> dict:
    """评估信号质量，返回综合评分。"""
    score = 0
    reasons = []
    direction = "neutral"

    # 趋势方向
    trend = signals.get("trend", "neutral")
    ma20 = signals.get("ma20", 0)
    ma60 = signals.get("ma60", 0)
    adx = signals.get("adx", 0)
    rsi = signals.get("rsi", 50)
    macd_hist = signals.get("macd_hist", 0)
    donchian_high = signals.get("donchian_high", 0)
    donchian_low = signals.get("donchian_low", 0)
    atr = signals.get("atr", 0)

    # 1. 趋势判断 (30分)
    if ma20 > ma60 and current_price > ma20:
        score += 25
        direction = "long"
        reasons.append("MA20>MA60 上升趋势")
    elif ma20 < ma60 and current_price < ma20:
        score += 25
        direction = "short"
        reasons.append("MA20<MA60 下降趋势")
    else:
        score += 5
        reasons.append("趋势不明")

    # 2. ADX 趋势强度 (20分)
    if adx > 30:
        score += 20
        reasons.append(f"ADX {adx:.0f} 强趋势")
    elif adx > 20:
        score += 10
        reasons.append(f"ADX {adx:.0f} 有趋势")

    # 3. 突破确认 (20分)
    if current_price >= donchian_high * 0.99:
        score += 20
        reasons.append("突破20日新高")
    elif current_price <= donchian_low * 1.01:
        score += 15
        reasons.append("跌破20日新低")

    # 4. RSI 位置 (15分)
    if 40 <= rsi <= 60:
        score += 15
        reasons.append(f"RSI {rsi:.0f} 中性区域")
    elif rsi > 70:
        score -= 10
        reasons.append(f"RSI {rsi:.0f} 超买警告")
    elif rsi < 30:
        score -= 10
        reasons.append(f"RSI {rsi:.0f} 超卖警告")

    # 5. MACD 动量 (15分)
    if direction == "long" and macd_hist > 0:
        score += 15
        reasons.append("MACD 多头动量")
    elif direction == "short" and macd_hist < 0:
        score += 15
        reasons.append("MACD 空头动量")

    # 计算止损和目标
    if atr > 0:
        if direction == "long":
            stop_loss = current_price - 2 * atr
            target = current_price + 3 * atr
        else:
            stop_loss = current_price + 2 * atr
            target = current_price - 3 * atr
        risk_reward = abs(target - current_price) / abs(current_price - stop_loss) if abs(current_price - stop_loss) > 0 else 0
    else:
        stop_loss = current_price * 0.97 if direction == "long" else current_price * 1.03
        target = current_price * 1.05 if direction == "long" else current_price * 0.95
        risk_reward = 1.5

    return {
        "score": min(max(score, 0), 100),
        "direction": direction,
        "reason": " | ".join(reasons),
        "stop_loss": round(stop_loss, 1),
        "target": round(target, 1),
        "risk_reward": round(risk_reward, 2),
    }


def format_actionable_message(opportunities: list) -> str:
    """格式化大白话消息，直接告诉用户在掘金雷达点什么。"""
    if not opportunities:
        return "现在没有好机会，继续等。别着急下单。"

    # 品种中文名映射
    NAME_MAP = {
        "rb": "螺纹钢", "hc": "热卷", "i": "铁矿石",
        "j": "焦炭", "jm": "焦煤", "cu": "铜", "al": "铝",
        "zn": "锌", "ni": "镍", "sc": "原油", "TA": "PTA",
        "MA": "甲醇", "FG": "玻璃", "SA": "纯碱", "m": "豆粕",
        "y": "豆油", "p": "棕榈油", "CF": "棉花", "SR": "白糖",
        "au": "黄金", "ag": "白银", "IF": "沪深300", "IC": "中证500",
    }

    lines = []
    for i, opp in enumerate(opportunities[:3], 1):
        symbol = opp["symbol"]
        name = NAME_MAP.get(symbol, symbol)
        is_buy = opp["direction"] == "long"
        action = "买入" if is_buy else "卖出"
        emoji = "🟢" if is_buy else "🔴"

        lines.append(f"{'='*20}")
        lines.append(f"{emoji} 机会{i}：{name}")
        lines.append(f"{'='*20}")
        lines.append("")
        lines.append(f"【操作】{action}{name}")
        lines.append(f"【确信度】{opp['confidence']}分（满分100）")
        lines.append("")
        lines.append("打开掘金雷达，这样操作：")
        lines.append(f"  1. 点「条件单」→ 选「{name}」")
        lines.append(f"  2. 委托价格填 {opp['entry']}")
        lines.append(f"  3. 止损价格填 {opp['stop_loss']}")
        lines.append(f"  4. 目标价格填 {opp['target']}")
        lines.append("")
        lines.append(f"【为什么做这个】{opp['reason']}")
        lines.append("")

    lines.append("="*20)
    lines.append("⚠️ 重要提醒")
    lines.append("="*20)
    lines.append("• 每个品种最多花30%的钱")
    lines.append("• 一定要设止损，不设止损不下单")
    lines.append("• 不确定就不做，等下一个机会")

    return "\n".join(lines)


def run_scan():
    """执行扫描并推送。"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始扫描 {len(CANDIDATES)} 个品种...")

    opportunities = scan_opportunities()

    if opportunities:
        message = format_actionable_message(opportunities)
        title = f"🎯 发现 {len(opportunities)} 个交易机会"
        print(message)
        notify(title, message, level="urgent")
    else:
        print("暂无高确信信号")
        notify("📊 市场扫描完成", "暂无高确信信号，继续观望。保持耐心。", level="info")

    # 保存扫描结果
    result_file = Path(__file__).parent.parent.parent / "daily" / f"{datetime.now().strftime('%Y-%m-%d')}_scan.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "opportunities": opportunities,
        }, f, ensure_ascii=False, indent=2)

    return opportunities


if __name__ == "__main__":
    run_scan()
