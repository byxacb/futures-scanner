"""期货行情抓取 - akshare 免费数据源

提供：
- get_daily_kline(symbol, start, end): 日线 K 线
- get_realtime_quote(symbol): 实时行情
- get_main_contract(variety): 当前主力合约代码
- get_position_rank(symbol, date): 期货公司持仓排行（多空 Top20）

约定：
- symbol 用品种代码（如 'rb', 'm', 'IF'）或合约代码（如 'rb2510'）
- 函数自动判断并补全主力合约

数据缓存：~/Desktop/期货/tools/data/cache/<symbol>_<type>.csv
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _import_akshare():
    """延迟 import 避免 akshare 未安装时整个模块崩。"""
    try:
        import akshare as ak
        return ak
    except ImportError as e:
        raise RuntimeError(
            "akshare 未安装。请运行 `pip install -r tools/requirements.txt`"
        ) from e


# PTA 在 akshare 里用 "TA"，其它都和品种代码大写后一致
SYMBOL_ALIAS = {
    "PTA": "TA",
}


def _to_main_continuous(variety: str) -> str:
    """品种代码转主连合约格式（akshare 用 RB0/M0/IF0 这种）。"""
    v = variety.upper()
    v = SYMBOL_ALIAS.get(v, v)
    if any(c.isdigit() for c in v):
        return v  # 已经是具体合约
    return f"{v}0"


def get_main_contract(variety: str) -> str:
    """返回主连合约代码（不是当月主力，而是主连）。"""
    return _to_main_continuous(variety)


def get_daily_kline(
    symbol: str,
    start: str | None = None,
    end: str | None = None,
    use_cache: bool = True,
) -> pd.DataFrame:
    """获取日线 K 线。

    Args:
        symbol: 'rb' / 'RB' / 'rb0' / 'RB2510' 都接受
        start: 'YYYYMMDD'，默认 1 年前
        end: 'YYYYMMDD'，默认今天
        use_cache: 是否用本地缓存（12 小时内）

    Returns:
        DataFrame columns: date, open, high, low, close, volume, open_interest
    """
    ak = _import_akshare()

    if start is None:
        start = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
    if end is None:
        end = datetime.now().strftime("%Y%m%d")

    contract = _to_main_continuous(symbol)
    cache_file = CACHE_DIR / f"{contract}_daily.csv"
    if use_cache and cache_file.exists():
        mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if datetime.now() - mtime < timedelta(hours=12):
            logger.debug("using cached kline for %s", contract)
            df = pd.read_csv(cache_file, parse_dates=["date"])
            return df[df["date"].between(start, end)].reset_index(drop=True)

    try:
        df = ak.futures_zh_daily_sina(symbol=contract)
    except Exception as e:
        raise RuntimeError(f"获取 {contract} K 线失败: {e}") from e

    if len(df) == 0:
        raise RuntimeError(f"{contract} 返回空数据，可能代码错误")

    df = df.rename(columns={"hold": "open_interest"})
    df["date"] = pd.to_datetime(df["date"])
    df.to_csv(cache_file, index=False)
    start_dt = pd.to_datetime(start)
    end_dt = pd.to_datetime(end)
    return df[df["date"].between(start_dt, end_dt)].reset_index(drop=True)


def get_realtime_quote(symbol: str) -> dict:
    """获取实时行情（盘中调用）。

    Returns:
        {symbol, price, bid, ask, volume, oi, change_pct, ts}
    """
    ak = _import_akshare()
    contract = symbol if any(c.isdigit() for c in symbol) else get_main_contract(symbol)
    try:
        df = ak.futures_zh_spot(symbol=contract, market="CF", adjust="0")
        row = df.iloc[0]
        price = float(row.get("current_price", 0) or row.get("最新价", 0))
        last_settle = float(row.get("last_settle_price", 0) or row.get("昨结算", 0))
        change_pct = round((price - last_settle) / last_settle * 100, 2) if last_settle > 0 else 0
        return {
            "symbol": contract,
            "price": price,
            "bid": float(row.get("bid_price", 0) or row.get("买一价", 0)),
            "ask": float(row.get("ask_price", 0) or row.get("卖一价", 0)),
            "volume": int(row.get("volume", 0) or row.get("成交量", 0)),
            "oi": int(row.get("hold", 0) or row.get("持仓量", 0)),
            "change_pct": change_pct,
            "ts": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error("实时行情失败 %s: %s", contract, e)
        return {"symbol": contract, "error": str(e)}


def get_position_rank(symbol: str, date: str | None = None) -> pd.DataFrame:
    """期货公司持仓排行（多空 Top20）。日终数据。

    Args:
        symbol: 合约代码
        date: 'YYYYMMDD'，默认昨天
    """
    ak = _import_akshare()
    if date is None:
        date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    try:
        df = ak.futures_dce_position_rank(date=date) if symbol.lower() in ["m", "y", "p", "i", "c", "j", "jm"] \
            else ak.futures_shfe_position_rank(date=date)
        return df[df["合约"] == symbol] if "合约" in df.columns else df
    except Exception as e:
        logger.warning("持仓排行失败: %s", e)
        return pd.DataFrame()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # 自测：拉一下螺纹钢日线
    df = get_daily_kline("rb")
    print(df.tail(10))
    print(f"\n最近 ATR(14): {(df['high'] - df['low']).tail(14).mean():.2f}")
