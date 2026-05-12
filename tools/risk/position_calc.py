"""仓位计算器 - master_playbook 第四节的代码实现

接口：
- calc_position(symbol, direction, account_equity, atr, ...) -> dict
- batch_calc(symbols, account_equity) -> dict
- validate_portfolio(positions, account_equity) -> dict

合约乘数与保证金率内置 - 与 products/ 目录的手册同步。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

# 品种规格表（合约乘数 + 估算保证金率 = 交易所 + 3%）
# 来源：上期所/大商所/郑商所/中金所/能源中心/广期所 公开规则
SPECS = {
    # 黑色
    "rb": {"multiplier": 10, "margin_rate": 0.12, "name": "螺纹钢"},
    "hc": {"multiplier": 10, "margin_rate": 0.12, "name": "热卷"},
    "i": {"multiplier": 100, "margin_rate": 0.13, "name": "铁矿石"},
    "j": {"multiplier": 100, "margin_rate": 0.15, "name": "焦炭"},
    "jm": {"multiplier": 60, "margin_rate": 0.15, "name": "焦煤"},
    # 农产品
    "m": {"multiplier": 10, "margin_rate": 0.11, "name": "豆粕"},
    "y": {"multiplier": 10, "margin_rate": 0.12, "name": "豆油"},
    "p": {"multiplier": 10, "margin_rate": 0.12, "name": "棕榈油"},
    "c": {"multiplier": 10, "margin_rate": 0.10, "name": "玉米"},
    "SR": {"multiplier": 10, "margin_rate": 0.11, "name": "白糖"},
    "CF": {"multiplier": 5, "margin_rate": 0.12, "name": "棉花"},
    # 有色
    "cu": {"multiplier": 5, "margin_rate": 0.12, "name": "沪铜"},
    "al": {"multiplier": 5, "margin_rate": 0.12, "name": "沪铝"},
    "zn": {"multiplier": 5, "margin_rate": 0.13, "name": "沪锌"},
    "ni": {"multiplier": 1, "margin_rate": 0.16, "name": "沪镍"},
    # 贵金属
    "au": {"multiplier": 1000, "margin_rate": 0.12, "name": "沪金"},
    "ag": {"multiplier": 15, "margin_rate": 0.12, "name": "沪银"},
    # 能化
    "sc": {"multiplier": 1000, "margin_rate": 0.13, "name": "原油"},
    "MA": {"multiplier": 10, "margin_rate": 0.11, "name": "甲醇"},
    "PTA": {"multiplier": 5, "margin_rate": 0.10, "name": "PTA"},
    "FG": {"multiplier": 20, "margin_rate": 0.12, "name": "玻璃"},
    "ru": {"multiplier": 10, "margin_rate": 0.13, "name": "橡胶"},
    # 金融
    "IF": {"multiplier": 300, "margin_rate": 0.15, "name": "沪深300"},
    "IH": {"multiplier": 300, "margin_rate": 0.15, "name": "上证50"},
    "IC": {"multiplier": 200, "margin_rate": 0.15, "name": "中证500"},
    "IM": {"multiplier": 200, "margin_rate": 0.15, "name": "中证1000"},
    "TS": {"multiplier": 20000, "margin_rate": 0.03, "name": "2年期国债"},
    "TF": {"multiplier": 10000, "margin_rate": 0.04, "name": "5年期国债"},
    "T":  {"multiplier": 10000, "margin_rate": 0.05, "name": "10年期国债"},
}

# 高相关组合 - 同向加和受限
CORRELATION_GROUPS = {
    "black": ["rb", "hc", "i", "j", "jm"],
    "ag_oil": ["m", "y", "p"],
    "nonferrous": ["cu", "al", "zn", "ni"],
    "precious": ["au", "ag"],
    "equity_idx": ["IF", "IH", "IC", "IM"],
    "bond": ["TS", "TF", "T"],
}


@dataclass
class PositionResult:
    symbol: str
    name: str
    direction: str
    max_lots: int
    stop_distance: float
    entry_price: float
    stop_price: float
    margin_per_lot: float
    margin_used: float
    margin_pct: float
    risk_amount: float
    risk_pct: float
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


def calc_position(
    symbol: str,
    direction: Literal["long", "short"],
    account_equity: float,
    entry_price: float,
    atr: float,
    risk_pct: float = 0.01,
    atr_multiplier: float = 2.0,
    high_confidence: bool = False,
    single_symbol_cap: float = 0.10,
) -> PositionResult:
    """计算单一头寸的最大开仓手数。

    Args:
        symbol: 品种代码（不带月份）如 'rb'
        direction: 'long' 或 'short'
        account_equity: 当前账户净值
        entry_price: 计划入场价
        atr: 日线 ATR(14)
        risk_pct: 单笔风险率（默认 1%）
        atr_multiplier: 止损距离 = atr_multiplier × ATR
        high_confidence: True 则风险率 ×1.5
        single_symbol_cap: 单品种保证金占用上限（默认 10%）

    Returns:
        PositionResult
    """
    if symbol not in SPECS:
        raise ValueError(f"未知品种 {symbol}。请先在 SPECS 表中登记。")

    spec = SPECS[symbol]
    multiplier = spec["multiplier"]
    margin_rate = spec["margin_rate"]

    if high_confidence:
        risk_pct = risk_pct * 1.5

    risk_amount = account_equity * risk_pct
    stop_distance = atr_multiplier * atr
    loss_per_lot = stop_distance * multiplier

    if loss_per_lot <= 0:
        raise ValueError(f"止损距离无效：atr={atr}, multiplier={atr_multiplier}")

    raw_max = risk_amount / loss_per_lot
    margin_per_lot = entry_price * multiplier * margin_rate

    # 应用单品种上限
    single_symbol_max_lots = math.floor(
        (account_equity * single_symbol_cap) / margin_per_lot
    )
    max_lots = min(math.floor(raw_max), single_symbol_max_lots)
    max_lots = max(0, max_lots)

    margin_used = max_lots * margin_per_lot
    margin_pct = margin_used / account_equity if account_equity > 0 else 0
    actual_risk = max_lots * loss_per_lot
    actual_risk_pct = actual_risk / account_equity if account_equity > 0 else 0

    if direction == "long":
        stop_price = entry_price - stop_distance
    else:
        stop_price = entry_price + stop_distance

    warnings = []
    if max_lots == 0:
        warnings.append("⚠️ 该品种单手亏损已超过风险预算——本次跳过")
    if raw_max > single_symbol_max_lots:
        warnings.append(
            f"⚠️ 风险预算允许 {math.floor(raw_max)} 手，但单品种上限限制到 {single_symbol_max_lots} 手"
        )

    return PositionResult(
        symbol=symbol,
        name=spec["name"],
        direction=direction,
        max_lots=max_lots,
        stop_distance=round(stop_distance, 2),
        entry_price=round(entry_price, 2),
        stop_price=round(stop_price, 2),
        margin_per_lot=round(margin_per_lot, 2),
        margin_used=round(margin_used, 2),
        margin_pct=round(margin_pct * 100, 2),
        risk_amount=round(actual_risk, 2),
        risk_pct=round(actual_risk_pct * 100, 3),
        warnings=warnings,
    )


def validate_portfolio(
    positions: list[dict],
    account_equity: float,
) -> dict:
    """校验整体组合是否满足风控红线。

    Args:
        positions: [{symbol, direction, lots, entry_price}, ...]
        account_equity: 当前净值

    Returns:
        {total_margin_pct, long_margin_pct, short_margin_pct, group_violations, ok}
    """
    total_margin = 0
    long_margin = 0
    short_margin = 0
    group_margin: dict[str, float] = {}

    for pos in positions:
        symbol = pos["symbol"]
        if symbol not in SPECS:
            continue
        spec = SPECS[symbol]
        margin_per_lot = pos["entry_price"] * spec["multiplier"] * spec["margin_rate"]
        pos_margin = margin_per_lot * pos["lots"]
        total_margin += pos_margin

        if pos["direction"] == "long":
            long_margin += pos_margin
        else:
            short_margin += pos_margin

        for group_name, members in CORRELATION_GROUPS.items():
            if symbol in members:
                key = f"{group_name}_{pos['direction']}"
                group_margin[key] = group_margin.get(key, 0) + pos_margin

    total_pct = total_margin / account_equity
    long_pct = long_margin / account_equity
    short_pct = short_margin / account_equity

    violations = []
    if total_pct > 0.70:
        violations.append(f"总保证金 {total_pct:.1%} 超过 70% 上限")
    if long_pct > 0.40:
        violations.append(f"多头总保证金 {long_pct:.1%} 超过 40% 单方向上限")
    if short_pct > 0.40:
        violations.append(f"空头总保证金 {short_pct:.1%} 超过 40% 单方向上限")

    for key, m in group_margin.items():
        pct = m / account_equity
        cap = 0.10 if "precious" in key else 0.15
        if pct > cap:
            violations.append(f"{key} 板块同向保证金 {pct:.1%} 超过 {cap:.0%}")

    return {
        "total_margin_pct": round(total_pct * 100, 2),
        "long_margin_pct": round(long_pct * 100, 2),
        "short_margin_pct": round(short_pct * 100, 2),
        "group_margin_pct": {k: round(v / account_equity * 100, 2) for k, v in group_margin.items()},
        "violations": violations,
        "ok": len(violations) == 0,
    }


if __name__ == "__main__":
    # 自测
    result = calc_position(
        symbol="rb",
        direction="long",
        account_equity=1_000_000,
        entry_price=3500,
        atr=50,
    )
    print("螺纹钢做多 100 万账户：")
    print(result.to_dict())

    portfolio = validate_portfolio(
        positions=[
            {"symbol": "rb", "direction": "long", "lots": 10, "entry_price": 3500},
            {"symbol": "m", "direction": "long", "lots": 12, "entry_price": 3500},
            {"symbol": "au", "direction": "short", "lots": 1, "entry_price": 580},
        ],
        account_equity=1_000_000,
    )
    print("\n组合校验：")
    print(portfolio)
