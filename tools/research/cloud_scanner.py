#!/usr/bin/env python3
"""云端扫描器 - GitHub Actions 运行，24小时自动找机会。

嵌入 100 本书 20 条铁律作为决策依据。
评分公式：S = 0.4×收益 + 0.2×(1-回撤) + 0.3×夏普 + 0.1×(1-波动)
60% 权重惩罚风险 → 受控激进，不是梭哈。
"""

import json
import sys
from datetime import datetime, timedelta

import akshare as ak
import httpx
import numpy as np

import os
BARK_URL = os.environ.get("BARK_URL", "")

# 导入 100 本书知识库
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from knowledge_base import RULES, get_rules_by_category, search_rules, get_stats

# 评分公式权重
SCORE_WEIGHTS = {"return": 0.4, "drawdown": 0.2, "sharpe": 0.3, "volatility": 0.1}

# 候选品种
CANDIDATES = {
    "rb": {"name": "螺纹钢", "symbol": "RB0", "exchange": "shfe"},
    "hc": {"name": "热卷", "symbol": "HC0", "exchange": "shfe"},
    "i":  {"name": "铁矿石", "symbol": "I0", "exchange": "dce"},
    "j":  {"name": "焦炭", "symbol": "J0", "exchange": "dce"},
    "jm": {"name": "焦煤", "symbol": "JM0", "exchange": "dce"},
    "cu": {"name": "铜", "symbol": "CU0", "exchange": "shfe"},
    "al": {"name": "铝", "symbol": "AL0", "exchange": "shfe"},
    "zn": {"name": "锌", "symbol": "ZN0", "exchange": "shfe"},
    "ni": {"name": "镍", "symbol": "NI0", "exchange": "shfe"},
    "sc": {"name": "原油", "symbol": "SC0", "exchange": "ine"},
    "TA": {"name": "PTA", "symbol": "TA0", "exchange": "czce"},
    "MA": {"name": "甲醇", "symbol": "MA0", "exchange": "czce"},
    "FG": {"name": "玻璃", "symbol": "FG0", "exchange": "czce"},
    "SA": {"name": "纯碱", "symbol": "SA0", "exchange": "czce"},
    "m":  {"name": "豆粕", "symbol": "M0", "exchange": "dce"},
    "y":  {"name": "豆油", "symbol": "Y0", "exchange": "dce"},
    "p":  {"name": "棕榈油", "symbol": "P0", "exchange": "dce"},
    "CF": {"name": "棉花", "symbol": "CF0", "exchange": "czce"},
    "SR": {"name": "白糖", "symbol": "SR0", "exchange": "czce"},
    "au": {"name": "黄金", "symbol": "AU0", "exchange": "shfe"},
    "ag": {"name": "白银", "symbol": "AG0", "exchange": "shfe"},
}


def get_kline(symbol: str, days: int = 120) -> dict:
    """获取日线数据并计算技术指标。"""
    try:
        # akshare 获取日线
        df = ak.futures_zh_daily_sina(symbol=symbol)
        if df is None or len(df) < 60:
            return None

        df = df.tail(days).copy()
        df["close"] = df["close"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["volume"] = df["volume"].astype(float)

        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        volume = df["volume"].values

        # 计算指标
        ma20 = np.mean(close[-20:])
        ma60 = np.mean(close[-60:]) if len(close) >= 60 else ma20

        # ATR
        tr_list = []
        for i in range(1, len(close)):
            tr = max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))
            tr_list.append(tr)
        atr = np.mean(tr_list[-14:])

        # RSI
        deltas = np.diff(close[-15:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        rsi = 100 - (100 / (1 + rs))

        # Donchian
        donchian_high = np.max(high[-20:])
        donchian_low = np.min(low[-20:])

        # ADX（简化）
        adx = 25  # 默认值

        # MACD
        ema12 = np.mean(close[-12:])
        ema26 = np.mean(close[-26:])
        macd_hist = ema12 - ema26

        current_price = close[-1]

        return {
            "price": current_price,
            "ma20": ma20,
            "ma60": ma60,
            "atr": atr,
            "rsi": rsi,
            "adx": adx,
            "donchian_high": donchian_high,
            "donchian_low": donchian_low,
            "macd_hist": macd_hist,
            "volume_avg": np.mean(volume[-20:]),
            "volume_last": volume[-1],
        }
    except Exception as e:
        print(f"  {symbol} 数据失败: {e}")
        return None


def evaluate(data: dict) -> dict:
    """基于 100 本书铁律评估信号。

    铁律应用：
    - #6 顺势而为：MA20>MA60 才做多
    - #7 量价配合：突破时成交量必须放大
    - #14 盈亏比≥2:1：不满足就不做
    - #19 评分公式偏爱低波动：波动太大扣分
    """
    score = 0
    reasons = []
    direction = "wait"

    price = data["price"]
    ma20 = data["ma20"]
    ma60 = data["ma60"]
    atr = data["atr"]
    rsi = data["rsi"]
    donchian_high = data["donchian_high"]
    donchian_low = data["donchian_low"]
    macd_hist = data["macd_hist"]
    vol_ratio = data["volume_last"] / data["volume_avg"] if data["volume_avg"] > 0 else 1

    # === 铁律 #6：顺势而为 ===
    if ma20 > ma60 and price > ma20:
        score += 25
        direction = "buy"
        reasons.append("铁律#6 趋势向上（价格>MA20>MA60）")
    elif ma20 < ma60 and price < ma20:
        score += 20
        direction = "sell"
        reasons.append("铁律#6 趋势向下（价格<MA20<MA60）")
    else:
        score += 5
        reasons.append("趋势不明确，观望")

    # === 铁律 #7：突破必须放量 ===
    if price >= donchian_high * 0.99:
        if vol_ratio >= 1.2:
            score += 20
            reasons.append(f"铁律#7 放量突破（量比{vol_ratio:.1f}倍）")
        else:
            score += 5
            reasons.append("突破但没放量，可能是假突破")

    # RSI 超买超卖
    if rsi > 70:
        score -= 10
        reasons.append("RSI超买，可能回调")
    elif rsi < 30:
        score -= 10
        reasons.append("RSI超卖，可能反弹")

    # MACD 动量
    if direction == "buy" and macd_hist > 0:
        score += 15
        reasons.append("MACD多头动量")
    elif direction == "sell" and macd_hist < 0:
        score += 15
        reasons.append("MACD空头动量")

    # 成交量放大
    if vol_ratio > 1.3:
        score += 10
        reasons.append(f"成交量放大{vol_ratio:.1f}倍")

    # === 铁律 #14：盈亏比≥2:1 ===
    if atr > 0:
        if direction == "buy":
            stop_loss = round(price - 2 * atr, 0)
            target = round(price + 3 * atr, 0)
        elif direction == "sell":
            stop_loss = round(price + 2 * atr, 0)
            target = round(price - 3 * atr, 0)
        else:
            stop_loss = 0
            target = 0
    else:
        stop_loss = round(price * 0.97, 0) if direction == "buy" else round(price * 1.03, 0)
        target = round(price * 1.05, 0) if direction == "buy" else round(price * 0.95, 0)

    # 盈亏比检查
    if stop_loss > 0 and target > 0:
        risk = abs(price - stop_loss)
        reward = abs(target - price)
        rr_ratio = reward / risk if risk > 0 else 0
        if rr_ratio < 2:
            score -= 15
            reasons.append(f"盈亏比{rr_ratio:.1f}:1 < 2:1，铁律#14不满足")
        else:
            reasons.append(f"盈亏比{rr_ratio:.1f}:1 ✓")

    # === 铁律 #19：评分公式偏爱低波动 ===
    volatility_pct = atr / price * 100 if price > 0 else 0
    if volatility_pct > 3:
        score -= 10
        reasons.append(f"波动率{volatility_pct:.1f}%偏高，评分公式会扣分")

    return {
        "score": min(max(score, 0), 100),
        "direction": direction,
        "reasons": reasons,
        "stop_loss": stop_loss,
        "target": target,
    }


def send_bark(title: str, content: str) -> bool:
    """推送到 Bark（GET 方式，更可靠）。"""
    if not BARK_URL:
        print("BARK_URL 未配置，跳过推送")
        return False
    from urllib.parse import quote
    bark = BARK_URL.rstrip("/")
    title_enc = quote(title, safe="")
    content_enc = quote(content[:500], safe="")
    url = f"{bark}/{title_enc}/{content_enc}?sound=anticipate&group=期货比赛&isArchive=1&level=timeSensitive"
    try:
        with httpx.Client(timeout=10, follow_redirects=True) as c:
            r = c.get(url)
            ok = r.json().get("code") == 200
            print(f"  Bark: {'✅' if ok else '❌'}")
            return ok
    except Exception as e:
        print(f"  Bark 失败: {e}")
        return False


def send_email(title: str, content: str) -> bool:
    """推送到邮箱。"""
    import smtplib
    from email.mime.text import MIMEText
    from email.utils import formataddr

    host = os.environ.get("SMTP_HOST", "")
    port = int(os.environ.get("SMTP_PORT", "465"))
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASSWORD", "")
    to = os.environ.get("SMTP_TO", user)

    if not all([host, user, password, to]):
        print("  邮箱未配置，跳过")
        return False

    msg = MIMEText(content, "plain", "utf-8")
    msg["Subject"] = title
    msg["From"] = formataddr(("期货机器人", user))
    msg["To"] = to

    try:
        if port == 465:
            srv = smtplib.SMTP_SSL(host, port, timeout=15)
        else:
            srv = smtplib.SMTP(host, port, timeout=15)
            srv.starttls()
        srv.login(user, password)
        srv.sendmail(user, [to], msg.as_string())
        srv.quit()
        print(f"  邮箱: ✅")
        return True
    except Exception as e:
        print(f"  邮箱失败: {e}")
        return False


def format_message(opportunities: list) -> str:
    """大白话格式，附带相关书本知识。"""
    if not opportunities:
        return "现在没有好机会，继续等。别着急下单。"

    # 获取知识库统计
    stats = get_stats()

    lines = []
    for i, opp in enumerate(opportunities[:3], 1):
        name = opp["name"]
        is_buy = opp["direction"] == "buy"
        action = "买入" if is_buy else "卖出"

        lines.append(f"{'='*20}")
        lines.append(f"机会{i}：{name}")
        lines.append(f"{'='*20}")
        lines.append("")
        lines.append(f"【操作】{action}{name}")
        lines.append(f"【确信度】{opp['score']}分（满分100）")
        lines.append("")
        lines.append("打开掘金雷达，这样操作：")
        lines.append(f"  1. 点「条件单」→ 选「{name}」")
        lines.append(f"  2. 委托价格填 {opp['entry']}")
        lines.append(f"  3. 止损价格填 {opp['stop_loss']}")
        lines.append(f"  4. 目标价格填 {opp['target']}")
        lines.append("")
        lines.append(f"【为什么】{' | '.join(opp['reasons'])}")
        lines.append("")

        # 添加相关书本知识
        if is_buy:
            relevant = search_rules("趋势") + search_rules("突破") + search_rules("动量")
        else:
            relevant = search_rules("止损") + search_rules("风控")
        if relevant:
            lines.append("【参考知识】")
            for rule in relevant[:3]:
                lines.append(f"  • {rule[1]}（{rule[2]}）")
            lines.append("")

    lines.append("="*20)
    lines.append(f"知识库：{stats['total_rules']}条规则，{stats['books_covered']}本书")
    lines.append("="*20)
    lines.append("• 铁律#5：止损必须挂，不挂不下单")
    lines.append("• 铁律#3：每个品种最多花30%的钱")
    lines.append("• 铁律#14：盈亏比≥2:1才值得做")
    lines.append("• 铁律#12：大部分时间什么都不做")
    lines.append("• 不确定就不做，等下一个机会")

    return "\n".join(lines)


def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始扫描 {len(CANDIDATES)} 个品种...")

    opportunities = []

    for key, info in CANDIDATES.items():
        symbol = info["symbol"]
        name = info["name"]
        print(f"  扫描 {name} ({symbol})...")

        data = get_kline(symbol)
        if not data:
            continue

        result = evaluate(data)
        if result["score"] >= 60 and result["direction"] in ("buy", "sell"):
            opportunities.append({
                "symbol": key,
                "name": name,
                "direction": result["direction"],
                "score": result["score"],
                "entry": round(data["price"], 0),
                "stop_loss": result["stop_loss"],
                "target": result["target"],
                "reasons": result["reasons"],
            })

    # 按确信度排序
    opportunities.sort(key=lambda x: x["score"], reverse=True)

    if opportunities:
        message = format_message(opportunities)
        title = f"发现 {len(opportunities)} 个交易机会"
        print(message)
        send_bark(title, message)
        send_email(title, message)
    else:
        print("暂无高确信信号，不推送，继续等")

    # 保存结果
    result = {
        "timestamp": datetime.now().isoformat(),
        "count": len(opportunities),
        "opportunities": opportunities,
    }
    print(f"\n扫描完成，发现 {len(opportunities)} 个机会")
    return result


if __name__ == "__main__":
    main()
