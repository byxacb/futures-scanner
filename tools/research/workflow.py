#!/usr/bin/env python3
"""完整研究工作流 - 基于 100 本书知识库

流程：
1. 扫描55个品种技术面
2. 抓取最新新闻
3. 查找基本面数据（库存、持仓量、基差）
4. 多维度评估（技术+基本面+情绪+风控）
5. 评分排序
6. 推送操作建议

每一步都基于 100 本书的规则。
"""

import sys
import os
import json
import httpx
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

# ============================================================
# 第一步：品种池定义
# ============================================================
PRODUCTS = {
    # 黑色系
    "RB": {"name": "螺纹钢", "symbol": "RB0", "sector": "黑色"},
    "HC": {"name": "热卷", "symbol": "HC0", "sector": "黑色"},
    "I":  {"name": "铁矿石", "symbol": "I0", "sector": "黑色"},
    "J":  {"name": "焦炭", "symbol": "J0", "sector": "黑色"},
    "JM": {"name": "焦煤", "symbol": "JM0", "sector": "黑色"},
    "SS": {"name": "不锈钢", "symbol": "SS0", "sector": "黑色"},
    "SF": {"name": "硅铁", "symbol": "SF0", "sector": "黑色"},
    "SM": {"name": "锰硅", "symbol": "SM0", "sector": "黑色"},
    # 有色
    "CU": {"name": "铜", "symbol": "CU0", "sector": "有色"},
    "AL": {"name": "铝", "symbol": "AL0", "sector": "有色"},
    "ZN": {"name": "锌", "symbol": "ZN0", "sector": "有色"},
    "PB": {"name": "铅", "symbol": "PB0", "sector": "有色"},
    "NI": {"name": "镍", "symbol": "NI0", "sector": "有色"},
    "SN": {"name": "锡", "symbol": "SN0", "sector": "有色"},
    # 贵金属
    "AU": {"name": "黄金", "symbol": "AU0", "sector": "贵金属"},
    "AG": {"name": "白银", "symbol": "AG0", "sector": "贵金属"},
    # 能化
    "SC": {"name": "原油", "symbol": "SC0", "sector": "能化"},
    "FU": {"name": "燃料油", "symbol": "FU0", "sector": "能化"},
    "BU": {"name": "沥青", "symbol": "BU0", "sector": "能化"},
    "RU": {"name": "橡胶", "symbol": "RU0", "sector": "能化"},
    "SP": {"name": "纸浆", "symbol": "SP0", "sector": "能化"},
    "TA": {"name": "PTA", "symbol": "TA0", "sector": "能化"},
    "MA": {"name": "甲醇", "symbol": "MA0", "sector": "能化"},
    "FG": {"name": "玻璃", "symbol": "FG0", "sector": "能化"},
    "SA": {"name": "纯碱", "symbol": "SA0", "sector": "能化"},
    "EG": {"name": "乙二醇", "symbol": "EG0", "sector": "能化"},
    "EB": {"name": "苯乙烯", "symbol": "EB0", "sector": "能化"},
    "PP": {"name": "聚丙烯", "symbol": "PP0", "sector": "能化"},
    "V":  {"name": "PVC", "symbol": "V0", "sector": "能化"},
    "L":  {"name": "塑料", "symbol": "L0", "sector": "能化"},
    "PG": {"name": "液化气", "symbol": "PG0", "sector": "能化"},
    # 农产品
    "M":  {"name": "豆粕", "symbol": "M0", "sector": "农产品"},
    "Y":  {"name": "豆油", "symbol": "Y0", "sector": "农产品"},
    "P":  {"name": "棕榈油", "symbol": "P0", "sector": "农产品"},
    "C":  {"name": "玉米", "symbol": "C0", "sector": "农产品"},
    "CS": {"name": "淀粉", "symbol": "CS0", "sector": "农产品"},
    "CF": {"name": "棉花", "symbol": "CF0", "sector": "农产品"},
    "SR": {"name": "白糖", "symbol": "SR0", "sector": "农产品"},
    "OI": {"name": "菜油", "symbol": "OI0", "sector": "农产品"},
    "RM": {"name": "菜粕", "symbol": "RM0", "sector": "农产品"},
    "AP": {"name": "苹果", "symbol": "AP0", "sector": "农产品"},
    "CJ": {"name": "红枣", "symbol": "CJ0", "sector": "农产品"},
    "PK": {"name": "花生", "symbol": "PK0", "sector": "农产品"},
    "PF": {"name": "短纤", "symbol": "PF0", "sector": "农产品"},
    "UR": {"name": "尿素", "symbol": "UR0", "sector": "农产品"},
    # 金融期货
    "IF": {"name": "沪深300", "symbol": "IF0", "sector": "金融"},
    "IC": {"name": "中证500", "symbol": "IC0", "sector": "金融"},
    "IH": {"name": "上证50", "symbol": "IH0", "sector": "金融"},
    "IM": {"name": "中证1000", "symbol": "IM0", "sector": "金融"},
    "T":  {"name": "10年国债", "symbol": "T0", "sector": "金融"},
    "TF": {"name": "5年国债", "symbol": "TF0", "sector": "金融"},
    "TS": {"name": "2年国债", "symbol": "TS0", "sector": "金融"},
    "TL": {"name": "30年国债", "symbol": "TL0", "sector": "金融"},
    # 广期所
    "SI": {"name": "工业硅", "symbol": "SI0", "sector": "新能源"},
    "LC": {"name": "碳酸锂", "symbol": "LC0", "sector": "新能源"},
}


# ============================================================
# 第二步：技术面分析
# ============================================================
def technical_analysis(symbol: str, days: int = 120) -> dict:
    """技术面分析：均线、RSI、MACD、唐奇安、ADX、ATR。"""
    try:
        import akshare as ak
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

        # 均线
        ma5 = np.mean(close[-5:])
        ma10 = np.mean(close[-10:])
        ma20 = np.mean(close[-20:])
        ma60 = np.mean(close[-60:]) if len(close) >= 60 else ma20

        # ATR
        tr_list = []
        for i in range(1, len(close)):
            tr = max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))
            tr_list.append(tr)
        atr = np.mean(tr_list[-14:]) if len(tr_list) >= 14 else np.mean(tr_list)
        atr_pct = atr / close[-1] * 100

        # RSI
        deltas = np.diff(close[-15:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        rsi = 100 - (100 / (1 + rs))

        # 唐奇安通道
        don_high = np.max(high[-20:])
        don_low = np.min(low[-20:])

        # MACD
        ema12 = np.mean(close[-12:])
        ema26 = np.mean(close[-26:])
        macd_hist = ema12 - ema26

        # 成交量分析
        vol_avg = np.mean(volume[-20:])
        vol_last = volume[-1]
        vol_ratio = vol_last / vol_avg if vol_avg > 0 else 1

        # 趋势判断
        trend = "up" if ma20 > ma60 and close[-1] > ma20 else \
                "down" if ma20 < ma60 and close[-1] < ma20 else "neutral"

        return {
            "price": close[-1],
            "ma5": ma5, "ma10": ma10, "ma20": ma20, "ma60": ma60,
            "atr": atr, "atr_pct": round(atr_pct, 2),
            "rsi": round(rsi, 1),
            "donchian_high": don_high, "donchian_low": don_low,
            "macd_hist": round(macd_hist, 2),
            "vol_ratio": round(vol_ratio, 2),
            "trend": trend,
            "adx": 0,  # 需要额外计算
        }
    except Exception as e:
        return None


# ============================================================
# 第三步：新闻面分析
# ============================================================
def news_analysis(product_name: str) -> dict:
    """抓取最新新闻，用关键词匹配分析。"""
    try:
        from news.fetch_news import fetch_mysteel_futures_news
        items = fetch_mysteel_futures_news(keywords=[product_name], limit=5)
        if not items:
            return {"sentiment": "neutral", "count": 0, "titles": []}

        # 简单情绪分析
        bullish_words = ["上涨", "突破", "新高", "需求", "减产", "挺价", "缺口"]
        bearish_words = ["下跌", "暴跌", "库存", "过剩", "减产", "需求弱", "低迷"]

        bull_count = 0
        bear_count = 0
        for item in items:
            title = item.title
            for w in bullish_words:
                if w in title:
                    bull_count += 1
            for w in bearish_words:
                if w in title:
                    bear_count += 1

        sentiment = "bullish" if bull_count > bear_count else \
                    "bearish" if bear_count > bull_count else "neutral"

        return {
            "sentiment": sentiment,
            "count": len(items),
            "titles": [item.title for item in items[:3]],
        }
    except Exception:
        return {"sentiment": "neutral", "count": 0, "titles": []}


# ============================================================
# 第四步：综合评估（100 本书铁律）
# ============================================================
def evaluate_product(code: str, info: dict, tech: dict, news: dict) -> dict:
    """综合评估：技术面 + 新闻面 + 100 本书铁律。

    评分维度：
    - 趋势方向（30分）
    - 突破确认（20分）
    - 盈亏比（20分）
    - 新闻面（15分）
    - 波动率（15分）

    100 本书铁律应用：
    - #6 顺势而为
    - #7 放量突破
    - #14 盈亏比≥2:1
    - #19 评分公式偏爱低波动
    """
    score = 0
    reasons = []
    direction = "wait"

    price = tech["price"]
    ma20 = tech["ma20"]
    ma60 = tech["ma60"]
    atr = tech["atr"]
    rsi = tech["rsi"]
    don_high = tech["donchian_high"]
    don_low = tech["donchian_low"]
    macd_hist = tech["macd_hist"]
    vol_ratio = tech["vol_ratio"]
    atr_pct = tech["atr_pct"]

    # === 铁律 #6：顺势而为 ===
    if ma20 > ma60 and price > ma20:
        score += 30
        direction = "buy"
        reasons.append("铁律#6 上升趋势（价格>MA20>MA60）")
    elif ma20 < ma60 and price < ma20:
        score += 25
        direction = "sell"
        reasons.append("铁律#6 下降趋势（价格<MA20<MA60）")
    elif price > ma20:
        score += 15
        direction = "buy"
        reasons.append("价格在MA20上方")
    elif price < ma20:
        score += 10
        direction = "sell"
        reasons.append("价格在MA20下方")

    # === 铁律 #7：放量突破 ===
    if price >= don_high * 0.99:
        if vol_ratio >= 1.2:
            score += 20
            reasons.append(f"铁律#7 放量突破（量比{vol_ratio:.1f}倍）")
        else:
            score += 5
            reasons.append("突破但未放量，谨慎")

    # RSI
    if rsi > 70:
        score -= 10
        reasons.append(f"RSI{rsi:.0f}超买，回调风险")
    elif rsi < 30:
        score -= 10
        reasons.append(f"RSI{rsi:.0f}超卖，反弹机会")

    # MACD 动量
    if direction == "buy" and macd_hist > 0:
        score += 10
        reasons.append("MACD多头动量")
    elif direction == "sell" and macd_hist < 0:
        score += 10
        reasons.append("MACD空头动量")

    # === 铁律 #14：盈亏比 ≥ 2:1 ===
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

    risk = abs(price - stop_loss)
    reward = abs(target - price)
    rr = reward / risk if risk > 0 else 0

    if rr < 2:
        score -= 15
        reasons.append(f"盈亏比{rr:.1f}:1<2:1，铁律#14不满足")
    else:
        score += 10
        reasons.append(f"盈亏比{rr:.1f}:1 ✓")

    # === 新闻面 ===
    if news["sentiment"] == "bullish" and direction == "buy":
        score += 15
        reasons.append(f"新闻面偏多（{news['count']}条）")
    elif news["sentiment"] == "bearish" and direction == "sell":
        score += 15
        reasons.append(f"新闻面偏空（{news['count']}条）")
    elif news["count"] > 0:
        reasons.append(f"新闻面中性（{news['count']}条）")

    # === 铁律 #19：波动率适中 ===
    if atr_pct > 3:
        score -= 10
        reasons.append(f"波动率{atr_pct}%偏高，评分公式扣分")
    elif atr_pct < 0.5:
        score -= 5
        reasons.append(f"波动率{atr_pct}%偏低，利润空间小")

    # 盈亏比
    risk = abs(price - stop_loss)
    reward = abs(target - price)
    rr = reward / risk if risk > 0 else 0

    return {
        "score": min(max(score, 0), 100),
        "direction": direction,
        "reasons": reasons,
        "stop_loss": stop_loss,
        "target": target,
        "rr": round(rr, 1),
        "atr_pct": atr_pct,
        "news": news,
    }


# ============================================================
# 第五步：评分排序 + 推送
# ============================================================
def format_message(opportunities: list) -> str:
    """大白话格式，按掘金雷达条件单界面生成逐步操作指引。"""
    if not opportunities:
        return ""

    # 合约代码映射
    CODE_MAP = {
        "锌": "ZN2605", "螺纹钢": "RB2610", "热卷": "HC2610", "铁矿石": "I2609",
        "焦炭": "J2609", "焦煤": "JM2609", "不锈钢": "SS2606", "硅铁": "SF2609",
        "锰硅": "SM2609", "铜": "CU2606", "铝": "AL2606", "铅": "PB2606",
        "镍": "NI2606", "锡": "SN2606", "黄金": "AU2606", "白银": "AG2606",
        "原油": "SC2606", "燃料油": "FU2609", "沥青": "BU2606", "橡胶": "RU2609",
        "纸浆": "SP2609", "PTA": "TA2609", "甲醇": "MA2609", "玻璃": "FG2609",
        "纯碱": "SA2609", "乙二醇": "EG2609", "苯乙烯": "EB2606", "聚丙烯": "PP2609",
        "PVC": "V2609", "塑料": "L2609", "液化气": "PG2606", "豆粕": "M2609",
        "豆油": "Y2609", "棕榈油": "P2609", "玉米": "C2609", "淀粉": "CS2609",
        "棉花": "CF2609", "白糖": "SR2609", "菜油": "OI2609", "菜粕": "RM2609",
        "苹果": "AP2610", "红枣": "CJ2609", "花生": "PK2610", "短纤": "PF2606",
        "尿素": "UR2609", "沪深300": "IF2605", "中证500": "IC2605",
        "上证50": "IH2605", "中证1000": "IM2605", "10年国债": "T2606",
        "5年国债": "TF2606", "2年国债": "TS2606", "30年国债": "TL2606",
        "工业硅": "SI2607", "碳酸锂": "LC2607",
    }

    lines = []
    for i, opp in enumerate(opportunities[:5], 1):
        name = opp["name"]
        is_buy = opp["direction"] == "buy"
        contract_code = CODE_MAP.get(name, opp.get("code", ""))
        entry = opp["entry"]
        stop_loss = opp["stop_loss"]
        target = opp["target"]

        lines.append(f"{'='*25}")
        lines.append(f"机会{i}：{name}（{contract_code}）")
        lines.append(f"{'='*25}")
        lines.append(f"确信度 {opp['score']}分/100 | 盈亏比 {opp['rr']}:1")
        lines.append(f"{'─'*25}")
        lines.append("")

        # === 开仓条件单 ===
        lines.append("【开仓】打开掘金雷达 → 条件单 → 指定价格开仓")
        lines.append("")
        if is_buy:
            lines.append(f"1. 合约 → {contract_code}")
            lines.append(f"2. 当行情价格 ≤ {entry}")
            lines.append(f"3. 委托方向 → 买入开仓")
        else:
            lines.append(f"1. 合约 → {contract_code}")
            lines.append(f"2. 当行情价格 ≥ {entry}")
            lines.append(f"3. 委托方向 → 卖出开仓")
        lines.append(f"4. 委托价格 → 对手价")
        lines.append(f"5. 委托数量 → 根据资金定（单品种≤30%）")
        lines.append(f"6. 有效期 → 持续有效")
        lines.append(f"7. 点提交")
        lines.append("")

        # === 止损条件单 ===
        lines.append("【止损】返回 → 条件单 → 指定价格止损")
        lines.append("")
        if is_buy:
            lines.append(f"1. 合约 → {contract_code}")
            lines.append(f"2. 当行情下跌至 {stop_loss}")
        else:
            lines.append(f"1. 合约 → {contract_code}")
            lines.append(f"2. 当行情上涨至 {stop_loss}")
        lines.append(f"3. 委托价格 → 对手价")
        lines.append(f"4. 平仓数量 → 和开仓数量一样")
        lines.append(f"5. 有效期 → 持续有效")
        lines.append(f"6. 点提交")
        lines.append("")

        # === 止盈条件单 ===
        lines.append("【止盈】返回 → 条件单 → 指定价格止盈")
        lines.append("")
        if is_buy:
            lines.append(f"1. 合约 → {contract_code}")
            lines.append(f"2. 当行情上涨至 {target}")
        else:
            lines.append(f"1. 合约 → {contract_code}")
            lines.append(f"2. 当行情下跌至 {target}")
        lines.append(f"3. 委托价格 → 对手价")
        lines.append(f"4. 平仓数量 → 和开仓数量一样")
        lines.append(f"5. 有效期 → 持续有效")
        lines.append(f"6. 点提交")
        lines.append("")

        lines.append(f"【为什么做】{' | '.join(opp['reasons'])}")
        lines.append("")

    lines.append("="*25)
    lines.append("铁律提醒")
    lines.append("="*25)
    lines.append("• 铁律#5：止损必须挂，不挂不下单")
    lines.append("• 铁律#3：单品种最多花30%的钱")
    lines.append("• 铁律#14：盈亏比≥2:1才做")
    lines.append("• 不确定就不做，等下一个机会")

    return "\n".join(lines)


def send_bark(title: str, content: str) -> bool:
    """推送到 Bark。"""
    bark_url = os.environ.get("BARK_URL", "")
    if not bark_url:
        return False
    from urllib.parse import quote
    bark = bark_url.rstrip("/")
    url = f"{bark}/{quote(title, safe='')}/{quote(content[:500], safe='')}?sound=anticipate&group=期货比赛&isArchive=1&level=timeSensitive"
    try:
        with httpx.Client(timeout=10, follow_redirects=True) as c:
            r = c.get(url)
            return r.json().get("code") == 200
    except:
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
        return False
    msg = MIMEText(content, "plain", "utf-8")
    msg["Subject"] = title
    msg["From"] = formataddr(("期货机器人", user))
    msg["To"] = to
    try:
        srv = smtplib.SMTP_SSL(host, port, timeout=15)
        srv.login(user, password)
        srv.sendmail(user, [to], msg.as_string())
        srv.quit()
        return True
    except:
        return False


# ============================================================
# 主流程
# ============================================================
def run_workflow():
    """执行完整工作流。"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始扫描 {len(PRODUCTS)} 个品种...")

    opportunities = []

    for code, info in PRODUCTS.items():
        symbol = info["symbol"]
        name = info["name"]

        # Step 1: 技术面分析
        tech = technical_analysis(symbol)
        if not tech:
            continue

        # Step 2: 新闻面分析
        news = news_analysis(name)

        # Step 3: 综合评估
        result = evaluate_product(code, info, tech, news)

        # Step 4: 筛选高确信信号
        if result["score"] >= 60 and result["direction"] in ("buy", "sell"):
            opportunities.append({
                "code": code,
                "name": name,
                "sector": info["sector"],
                "direction": result["direction"],
                "score": result["score"],
                "entry": round(tech["price"], 0),
                "stop_loss": result["stop_loss"],
                "target": result["target"],
                "rr": result["rr"],
                "reasons": result["reasons"],
                "atr_pct": result["atr_pct"],
            })

    # 按确信度排序
    opportunities.sort(key=lambda x: x["score"], reverse=True)

    print(f"扫描完成，发现 {len(opportunities)} 个机会")

    # 推送
    if opportunities:
        message = format_message(opportunities)
        title = f"发现 {len(opportunities)} 个交易机会"
        print(message)
        send_bark(title, message)
        send_email(title, message)
    else:
        print("暂无高确信信号，不推送")

    # 保存结果
    result_file = Path(__file__).parent.parent.parent / "daily" / f"{datetime.now().strftime('%Y-%m-%d')}_scan.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "count": len(opportunities),
            "opportunities": opportunities,
        }, f, ensure_ascii=False, indent=2)

    return opportunities


if __name__ == "__main__":
    run_workflow()
