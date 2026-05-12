"""盘后复盘 - 15:00 收盘后跑

任务：
1. 拉今日各品种行情更新 daily 简报的"收盘"部分
2. 引导用户填写"今日交易"列表（手工，因为 Claude 不接管账户）
3. 自动生成"明日预案"框架

用法：
  python -m tools.briefing.evening                # 默认从 config 读品种池
  python -m tools.briefing.evening --interactive  # 交互式询问交易记录
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

logger = logging.getLogger(__name__)

DEFAULT_UNIVERSE = ["rb", "m", "au", "IF", "sc"]


def build_recap_section(symbols: list[str]) -> list[dict]:
    out = []
    for s in symbols:
        try:
            df = get_daily_kline(s, use_cache=False)
            today = df.iloc[-1]
            yesterday = df.iloc[-2]
            change = (today["close"] - yesterday["close"]) / yesterday["close"] * 100
            volume_change = (today["volume"] - yesterday["volume"]) / yesterday["volume"] * 100 if yesterday["volume"] else 0
            sm = signal_summary(df)
            out.append({
                "symbol": s,
                "close": round(float(today["close"]), 2),
                "change_pct": round(change, 2),
                "volume": int(today["volume"]),
                "volume_change_pct": round(volume_change, 1),
                "oi": int(today.get("open_interest", 0)),
                "trend": sm["trend"],
                "regime": sm["regime"],
                "rsi14": sm["rsi14"],
            })
        except Exception as e:
            logger.error("%s 复盘失败: %s", s, e)
            out.append({"symbol": s, "error": str(e)})
    return out


def format_evening(recap: list[dict], date: str) -> str:
    out = [f"# {date} 盘后复盘\n"]
    out.append(f"_生成于 {datetime.now().strftime('%H:%M:%S')}_\n")

    out.append("## 今日行情\n")
    out.append("| 品种 | 收盘 | 涨跌% | 量变% | RSI | 趋势 | 市态 |")
    out.append("|------|-----|------|-------|-----|------|------|")
    for r in recap:
        if "error" in r:
            out.append(f"| {r['symbol']} | ❌ | — | — | — | — | {r['error']} |")
            continue
        out.append(
            f"| {r['symbol']} | {r['close']} | {r['change_pct']:+.2f}% | "
            f"{r['volume_change_pct']:+.1f}% | {r['rsi14']} | {r['trend']} | {r['regime']} |"
        )
    out.append("")

    out.append("## 今日交易明细\n")
    out.append("> 请填写真实交易记录（手动）\n")
    out.append("### 交易 1（示例）")
    out.append("- 品种 + 合约：")
    out.append("- 方向 + 手数：")
    out.append("- 开仓价 / 平仓价：")
    out.append("- 进场理由：")
    out.append("- 止损价 / 是否触发：")
    out.append("- 盈亏（元）：")
    out.append("- 是否按计划执行：✅ / ❌")
    out.append("- 教训/经验：")
    out.append("")

    out.append("## 账户状态\n")
    out.append("- 净值（元）：")
    out.append("- 当日盈亏：")
    out.append("- 累计回撤（峰值到现在）：")
    out.append("- 当前持仓：")
    out.append("")

    out.append("## 心理自评（1-10）\n")
    out.append("- 平静度：")
    out.append("- 纪律性：")
    out.append("- 是否触发任何"红线"事件：")
    out.append("")

    out.append("## 明日预案\n")
    out.append("- 主关注品种 + 关键价位：")
    out.append("- 重大事件 / 数据公布：")
    out.append("- 现有持仓的止损/止盈调整：")
    out.append("- 计划开仓的新品种：")
    out.append("")
    out.append("---")
    out.append("\n复盘文件由 evening.py 生成。诚实记录每一笔——这是积累经验最重要的环节。")

    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", type=str, default=",".join(DEFAULT_UNIVERSE))
    parser.add_argument("--out", type=str, default=None)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    date = datetime.now().strftime("%Y-%m-%d")
    recap = build_recap_section(symbols)
    md = format_evening(recap, date)

    out_path = Path(args.out) if args.out else PROJECT_ROOT / "daily" / f"{date}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        existing = out_path.read_text(encoding="utf-8")
        md = existing + "\n\n---\n\n" + md
    out_path.write_text(md, encoding="utf-8")
    print(f"✅ 复盘已写入 {out_path}")

    # 推送到手机
    try:
        from notify.sender import notify  # noqa: E402
        push_lines = [f"# 📉 {date} 盘后复盘\n", "## 今日行情速览\n"]
        for r in recap:
            if "error" in r:
                continue
            push_lines.append(
                f"- **{r['symbol']}**: {r['close']} ({r['change_pct']:+.2f}%) | "
                f"量变 {r['volume_change_pct']:+.1f}% | RSI {r['rsi14']}"
            )
        push_lines.append(f"\n📝 复盘填写：daily/{date}.md")
        notify(
            title=f"📊 {date} 盘后复盘",
            content="\n".join(push_lines),
            level="info",
        )
    except Exception as e:
        print(f"⚠️ 推送失败: {e}")


if __name__ == "__main__":
    main()
