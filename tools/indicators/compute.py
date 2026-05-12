"""技术指标计算 - 自实现以避免外部库版本问题

提供：
- atr(df, period=14): 平均真实波幅
- ma(df, period): 简单移动均线
- ema(df, period): 指数移动均线
- macd(df, fast=12, slow=26, signal=9): MACD
- rsi(df, period=14): 相对强弱
- bollinger(df, period=20, std=2): 布林带
- donchian(df, period=20): 唐奇安通道（海龟用）
- adx(df, period=14): 趋势强度

所有函数接受 DataFrame (含 open/high/low/close/volume) 并返回 Series 或新 DataFrame。
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def true_range(df: pd.DataFrame) -> pd.Series:
    """True Range = max(H-L, |H-prev_C|, |L-prev_C|)"""
    high_low = df["high"] - df["low"]
    high_pc = (df["high"] - df["close"].shift(1)).abs()
    low_pc = (df["low"] - df["close"].shift(1)).abs()
    return pd.concat([high_low, high_pc, low_pc], axis=1).max(axis=1)


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """ATR - 平均真实波幅，Wilder 平滑"""
    tr = true_range(df)
    return tr.ewm(alpha=1.0 / period, adjust=False).mean()


def ma(df: pd.DataFrame, period: int, col: str = "close") -> pd.Series:
    return df[col].rolling(period).mean()


def ema(df: pd.DataFrame, period: int, col: str = "close") -> pd.Series:
    return df[col].ewm(span=period, adjust=False).mean()


def macd(
    df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9
) -> pd.DataFrame:
    """MACD - 返回 dif/dea/hist 三列"""
    ema_fast = ema(df, fast)
    ema_slow = ema(df, slow)
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    hist = (dif - dea) * 2
    return pd.DataFrame({"dif": dif, "dea": dea, "hist": hist})


def rsi(df: pd.DataFrame, period: int = 14, col: str = "close") -> pd.Series:
    """RSI - 相对强弱"""
    delta = df[col].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def bollinger(
    df: pd.DataFrame, period: int = 20, std: float = 2.0
) -> pd.DataFrame:
    mid = ma(df, period)
    sd = df["close"].rolling(period).std()
    return pd.DataFrame({
        "bb_mid": mid,
        "bb_upper": mid + std * sd,
        "bb_lower": mid - std * sd,
        "bb_width": (2 * std * sd) / mid,
    })


def donchian(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """唐奇安通道 - 海龟交易法核心信号"""
    return pd.DataFrame({
        "donchian_high": df["high"].rolling(period).max(),
        "donchian_low": df["low"].rolling(period).min(),
        "donchian_mid": (df["high"].rolling(period).max() + df["low"].rolling(period).min()) / 2,
    })


def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """ADX - 平均趋向指数。>25 趋势市，<20 震荡市"""
    high = df["high"]
    low = df["low"]
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm.shift(0)) & (minus_dm > 0), 0.0)
    tr = true_range(df)
    atr_ = tr.ewm(alpha=1.0 / period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1.0 / period, adjust=False).mean() / atr_
    minus_di = 100 * minus_dm.ewm(alpha=1.0 / period, adjust=False).mean() / atr_
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1.0 / period, adjust=False).mean()


def signal_summary(df: pd.DataFrame) -> dict:
    """对一条 K 线序列计算所有关键指标的当前值 + 信号判定。

    返回字典适合塞进每日简报。
    """
    if len(df) < 60:
        return {"error": "数据不足 60 根 K 线"}

    df = df.copy()
    df["atr14"] = atr(df, 14)
    df["ma20"] = ma(df, 20)
    df["ma60"] = ma(df, 60)
    df["rsi14"] = rsi(df, 14)
    df[["dif", "dea", "hist"]] = macd(df)
    df[["bb_mid", "bb_upper", "bb_lower", "bb_width"]] = bollinger(df)
    df[["dc_high", "dc_low", "dc_mid"]] = donchian(df, 20)
    df["adx14"] = adx(df, 14)

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # 趋势判定
    trend = "up" if last["ma20"] > last["ma60"] else "down" if last["ma20"] < last["ma60"] else "sideways"
    regime = "trend" if last["adx14"] > 25 else "range" if last["adx14"] < 20 else "transition"

    # 信号
    breakout_up = last["close"] >= df["dc_high"].iloc[-2]  # 突破前 20 日新高
    breakout_dn = last["close"] <= df["dc_low"].iloc[-2]
    volume_up = last["volume"] > df["volume"].iloc[-20:-1].mean() * 1.2

    macd_cross_up = prev["dif"] <= prev["dea"] and last["dif"] > last["dea"]
    macd_cross_dn = prev["dif"] >= prev["dea"] and last["dif"] < last["dea"]

    return {
        "close": round(float(last["close"]), 2),
        "atr14": round(float(last["atr14"]), 2),
        "ma20": round(float(last["ma20"]), 2),
        "ma60": round(float(last["ma60"]), 2),
        "rsi14": round(float(last["rsi14"]), 1),
        "macd_hist": round(float(last["hist"]), 2),
        "bb_upper": round(float(last["bb_upper"]), 2),
        "bb_lower": round(float(last["bb_lower"]), 2),
        "bb_width_pct": round(float(last["bb_width"]) * 100, 2),
        "dc_high20": round(float(df["dc_high"].iloc[-2]), 2),
        "dc_low20": round(float(df["dc_low"].iloc[-2]), 2),
        "adx14": round(float(last["adx14"]), 1),
        "trend": trend,
        "regime": regime,
        "signals": {
            "breakout_up_20d": bool(breakout_up),
            "breakout_dn_20d": bool(breakout_dn),
            "volume_confirmed": bool(volume_up),
            "macd_cross_up": bool(macd_cross_up),
            "macd_cross_dn": bool(macd_cross_dn),
            "rsi_overbought": bool(last["rsi14"] > 70),
            "rsi_oversold": bool(last["rsi14"] < 30),
        },
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "..")
    from data.fetch_market import get_daily_kline

    df = get_daily_kline("rb")
    summary = signal_summary(df)
    import json
    print(json.dumps(summary, indent=2, ensure_ascii=False))
