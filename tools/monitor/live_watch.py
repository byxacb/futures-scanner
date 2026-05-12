"""盘中实时监控 - 在 09:00-15:00 期间循环

任务：
1. 每 30 秒拉一次品种池实时报价
2. 比对盘前简报中的关键价位（止损/突破位/加仓位）
3. 触发时桌面通知（macOS 用 pync，其它平台打印）
4. 把触发事件追加到 daily 的"实时事件"段

约定：
- 价位文件 `daily/YYYY-MM-DD_watchlist.json` 由 morning.py 或手动编辑生成
- 触发后不会自动下单——只通知用户

用法：
  python -m tools.monitor.live_watch
  python -m tools.monitor.live_watch --interval 30 --duration 21600
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from data.fetch_market import get_realtime_quote  # noqa: E402

logger = logging.getLogger(__name__)


def desktop_notify(title: str, message: str, level: str = "warn") -> None:
    """通知：macOS 桌面 + Server酱/Bark/邮件多通道。"""
    # 1. macOS 桌面
    try:
        import pync
        pync.notify(message, title=title)
    except ImportError:
        print(f"\n🔔 [{datetime.now().strftime('%H:%M:%S')}] {title}: {message}\n")

    # 2. 手机推送
    try:
        from notify.sender import notify as push_notify
        push_notify(title, message, level=level)
    except Exception as e:
        logger.debug("手机推送失败（不致命）: %s", e)


def load_watchlist(date: str) -> list[dict]:
    """从 daily/YYYY-MM-DD_watchlist.json 加载关键价位。

    schema:
    [
      {"symbol": "rb", "type": "breakout_long", "trigger": 3580},
      {"symbol": "rb", "type": "stop_long", "trigger": 3450},
      ...
    ]
    """
    path = PROJECT_ROOT / "daily" / f"{date}_watchlist.json"
    if not path.exists():
        logger.warning("无 watchlist 文件 %s——只做行情监控", path)
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def check_triggers(quote: dict, watches: list[dict]) -> list[dict]:
    """对一个品种的实时报价检查所有触发条件。"""
    triggered = []
    if "error" in quote or quote["price"] == 0:
        return triggered
    price = quote["price"]

    for w in watches:
        if w.get("triggered"):
            continue
        t = w["type"]
        trig = w["trigger"]

        is_triggered = False
        if t in ("breakout_long", "stop_short", "take_profit_short"):
            is_triggered = price >= trig
        elif t in ("breakout_short", "stop_long", "take_profit_long"):
            is_triggered = price <= trig

        if is_triggered:
            triggered.append({**w, "triggered_price": price, "triggered_at": datetime.now().isoformat()})
            w["triggered"] = True
    return triggered


def append_event(date: str, event: dict) -> None:
    """触发事件追加到 daily 文件。"""
    path = PROJECT_ROOT / "daily" / f"{date}.md"
    line = (
        f"\n- 🔔 {event['triggered_at'][11:19]} **{event['symbol']}** "
        f"{event['type']} 触发 @{event['triggered_price']} (目标 {event['trigger']})"
    )
    if not path.exists():
        path.write_text(f"# {date} 实时事件\n{line}\n", encoding="utf-8")
    else:
        with path.open("a", encoding="utf-8") as f:
            f.write(line)


def loop(interval: int, duration: int) -> None:
    date = datetime.now().strftime("%Y-%m-%d")
    watches = load_watchlist(date)
    if not watches:
        logger.warning("watchlist 为空。请生成 daily/%s_watchlist.json 或直接退出。", date)

    symbols = sorted({w["symbol"] for w in watches})
    if not symbols:
        return

    end_at = time.time() + duration
    while time.time() < end_at:
        for symbol in symbols:
            quote = get_realtime_quote(symbol)
            sym_watches = [w for w in watches if w["symbol"] == symbol]
            triggers = check_triggers(quote, sym_watches)
            for t in triggers:
                # 止损是 urgent，加仓提示是 warn
                lvl = "urgent" if "stop" in t["type"] else "warn"
                desktop_notify(
                    title=f"⚠️ {t['symbol']} {t['type']}",
                    message=f"现价 {t['triggered_price']}，触发位 {t['trigger']}\n{t.get('note', '')}",
                    level=lvl,
                )
                append_event(date, t)
                logger.info("触发：%s", t)
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=30, help="轮询间隔（秒）")
    parser.add_argument("--duration", type=int, default=6 * 3600, help="总时长（秒），默认 6h")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    loop(args.interval, args.duration)


if __name__ == "__main__":
    main()
