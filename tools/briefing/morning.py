"""盘前简报生成 - 每个交易日 08:00 跑

输出：daily/YYYY-MM-DD.md 的盘前部分。

流程：
1. 读取品种池（config.toml）
2. 拉每个品种最近 90 天 K 线 + 计算技术信号
3. 调用 calc_position 给出"今日最大手数"参考
4. （可选）调 LLM 给新闻情绪打分
5. 把所有结果写入 daily 文件
6. 总结：是否有"高确信信号"？

用法：
  python -m tools.briefing.morning            # 用 config.toml 配置
  python -m tools.briefing.morning --symbols rb,m,au
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from data.fetch_market import get_daily_kline  # noqa: E402
from indicators.compute import signal_summary  # noqa: E402
from risk.position_calc import SPECS, calc_position  # noqa: E402

logger = logging.getLogger(__name__)


DEFAULT_UNIVERSE = ["rb", "m", "au", "IF", "sc"]


def evaluate_signal_quality(summary: dict) -> tuple[str, str, list[str]]:
    """给信号打分：none/weak/medium/strong + 方向 + 满足条件列表"""
    if "error" in summary:
        return "none", "—", [summary["error"]]

    sig = summary["signals"]
    conditions_met = []
    direction = "—"

    # 多头条件
    long_score = 0
    if sig["breakout_up_20d"]:
        long_score += 2
        conditions_met.append("✓ 突破 20 日新高")
    if summary["trend"] == "up":
        long_score += 1
        conditions_met.append("✓ MA20>MA60 上升趋势")
    if sig["volume_confirmed"] and (sig["breakout_up_20d"] or sig["macd_cross_up"]):
        long_score += 1
        conditions_met.append("✓ 成交量放大")
    if sig["macd_cross_up"]:
        long_score += 1
        conditions_met.append("✓ MACD 金叉")
    if summary["regime"] == "trend":
        long_score += 1
        conditions_met.append("✓ ADX>25 趋势市")

    # 空头条件
    short_score = 0
    short_conditions = []
    if sig["breakout_dn_20d"]:
        short_score += 2
        short_conditions.append("✓ 突破 20 日新低")
    if summary["trend"] == "down":
        short_score += 1
        short_conditions.append("✓ MA20<MA60 下降趋势")
    if sig["volume_confirmed"] and (sig["breakout_dn_20d"] or sig["macd_cross_dn"]):
        short_score += 1
        short_conditions.append("✓ 成交量放大")
    if sig["macd_cross_dn"]:
        short_score += 1
        short_conditions.append("✓ MACD 死叉")
    if summary["regime"] == "trend":
        short_score += 1
        short_conditions.append("✓ ADX>25 趋势市")

    if long_score >= short_score:
        score = long_score
        direction = "long"
        conditions = conditions_met
    else:
        score = short_score
        direction = "short"
        conditions = short_conditions

    if score >= 5:
        quality = "strong"
    elif score >= 3:
        quality = "medium"
    elif score >= 2:
        quality = "weak"
    else:
        quality = "none"
        direction = "—"

    return quality, direction, conditions


def build_symbol_section(
    symbol: str, account_equity: float = 1_000_000
) -> dict:
    """组装一个品种的简报数据。"""
    try:
        df = get_daily_kline(symbol)
        summary = signal_summary(df)
        quality, direction, conditions = evaluate_signal_quality(summary)

        position_info = None
        if direction in ("long", "short") and quality in ("medium", "strong"):
            try:
                position_info = calc_position(
                    symbol=symbol,
                    direction=direction,
                    account_equity=account_equity,
                    entry_price=summary["close"],
                    atr=summary["atr14"],
                    high_confidence=(quality == "strong"),
                ).to_dict()
            except Exception as e:
                logger.warning("calc_position 失败 %s: %s", symbol, e)

        return {
            "symbol": symbol,
            "name": SPECS.get(symbol, {}).get("name", symbol),
            "summary": summary,
            "quality": quality,
            "direction": direction,
            "conditions_met": conditions,
            "position": position_info,
        }
    except Exception as e:
        logger.error("品种 %s 简报失败: %s", symbol, e)
        return {"symbol": symbol, "error": str(e)}


def format_markdown(sections: list[dict], date: str) -> str:
    """把所有品种 sections 渲染成 markdown."""
    out = [f"# {date} 盘前简报\n"]
    out.append(f"_生成于 {datetime.now().strftime('%H:%M:%S')}_\n")

    # 高确信汇总
    strong_signals = [s for s in sections if s.get("quality") == "strong"]
    if strong_signals:
        out.append("## ⭐ 高确信信号\n")
        for s in strong_signals:
            out.append(f"- **{s['name']} {s['symbol']}** {s['direction']} —— {', '.join(s['conditions_met'])}")
        out.append("")
    else:
        out.append("## 今日无高确信信号 - 空仓 / 持有现有头寸\n")

    out.append("## 各品种技术面\n")
    for s in sections:
        if "error" in s:
            out.append(f"### {s['symbol']} ❌ {s['error']}\n")
            continue
        sm = s["summary"]
        out.append(f"### {s['name']} ({s['symbol']})")
        out.append(f"- 收盘 {sm['close']} | ATR(14) {sm['atr14']} | 趋势 {sm['trend']} | 市态 {sm['regime']} (ADX {sm['adx14']})")
        out.append(f"- MA20 {sm['ma20']} | MA60 {sm['ma60']} | RSI {sm['rsi14']} | MACD柱 {sm['macd_hist']}")
        out.append(f"- 唐奇安通道：上 {sm['dc_high20']} / 下 {sm['dc_low20']} | 布林宽度 {sm['bb_width_pct']}%")
        out.append(f"- **信号质量**：{s['quality']} ({s['direction']})")
        if s["conditions_met"]:
            for c in s["conditions_met"]:
                out.append(f"  - {c}")
        if s["position"]:
            p = s["position"]
            out.append(f"- **仓位建议**：最大 {p['max_lots']} 手 | 止损 @{p['stop_price']} | 保证金占用 {p['margin_pct']}%")
            for w in p["warnings"]:
                out.append(f"  - {w}")
        out.append("")

    out.append("## 行动清单\n")
    out.append("- [ ] 检查现有持仓的止损单是否还在原位")
    out.append("- [ ] 看简报中高确信信号 → 决定是否开仓")
    out.append("- [ ] 看今日有无重大数据/事件（FOMC/CPI/非农/钢联/政策）")
    out.append("- [ ] 09:00 开盘前 5 分钟挂好限价单+止损单")
    out.append("")
    out.append("---")
    out.append("\n本简报由 morning.py 自动生成。请结合个人判断使用，最终下单由用户本人在比赛软件完成。")

    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", type=str, default=",".join(DEFAULT_UNIVERSE))
    parser.add_argument("--account", type=float, default=1_000_000)
    parser.add_argument("--out", type=str, default=None)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    date = datetime.now().strftime("%Y-%m-%d")

    sections = [build_symbol_section(s, args.account) for s in symbols]
    md = format_markdown(sections, date)

    out_path = Path(args.out) if args.out else PROJECT_ROOT / "daily" / f"{date}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 如果文件已存在（夜盘已写过），把简报追加而不是覆盖
    if out_path.exists():
        existing = out_path.read_text(encoding="utf-8")
        md = existing + "\n\n---\n\n" + md
    out_path.write_text(md, encoding="utf-8")

    print(f"✅ 简报已写入 {out_path}")

    # 推送到手机
    try:
        from notify.sender import notify  # noqa: E402
        # 摘要：只发高确信信号那段，整个简报太长
        strong = [s for s in sections if s.get("quality") == "strong"]
        if strong:
            push_lines = [f"# 📈 {date} 盘前简报\n", "## ⭐ 今日高确信信号\n"]
            for s in strong:
                p = s.get("position") or {}
                push_lines.append(
                    f"**{s['name']} {s['symbol']}** → {s['direction']}\n"
                    f"- 收 {s['summary']['close']} | ATR {s['summary']['atr14']}\n"
                    f"- 建议 {p.get('max_lots', '?')} 手 | 止损 @{p.get('stop_price', '?')}"
                )
        else:
            push_lines = [f"# {date} 盘前简报\n", "**今日无高确信信号**——默认空仓"]
        push_lines.append(f"\n详情：daily/{date}.md")
        notify(
            title=f"📊 {date} 盘前简报",
            content="\n".join(push_lines),
            level="info",
        )
    except Exception as e:
        print(f"⚠️ 推送失败（不影响简报生成）: {e}")


if __name__ == "__main__":
    main()
