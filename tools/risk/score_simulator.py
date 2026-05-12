"""评分公式自估工具 - 输入账户表现，输出综合得分和估算排名

公式：
S = 0.4 × R_score + 0.2 × DD_score + 0.3 × Sharpe_score + 0.1 × Vol_score

每个子项都是"绝对部分 + 排名部分"的混合。
但官方比赛 N（总账户数）和你自己的排名 M 是未知的——
所以本工具用"假设 N=1000、给定百分位排名"的方式做估算。

用法：
  python -m tools.risk.score_simulator --return-pct 15 --drawdown-pct 5 --sharpe 2.0 --vol-pct 12
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass


@dataclass
class ScoreEstimate:
    return_score: float
    drawdown_score: float
    sharpe_score: float
    volatility_score: float
    total: float
    estimated_rank_top4_prob: str
    notes: list[str]


# 经验值：参考往届比赛数据 + 模拟比赛常见分布
# return_pct → 估算排名百分位（前 X%）
BENCHMARK_RETURN = [
    (50, 1),   # 收益 >50% → 前 1%
    (30, 5),
    (20, 10),
    (15, 20),
    (10, 35),
    (5, 50),
    (0, 65),
    (-5, 80),
    (-15, 95),
]

# drawdown_pct → 排名百分位（越小越好）
BENCHMARK_DRAWDOWN = [
    (2, 5),
    (5, 15),
    (10, 30),
    (15, 50),
    (20, 70),
    (30, 90),
]

# Sharpe 比率 → 排名百分位
BENCHMARK_SHARPE = [
    (3.0, 2),
    (2.5, 5),
    (2.0, 10),
    (1.5, 20),
    (1.0, 40),
    (0.5, 60),
    (0.0, 80),
]

# 波动率 → 排名百分位（越小越好）
BENCHMARK_VOLATILITY = [
    (5, 5),
    (10, 20),
    (15, 40),
    (20, 60),
    (30, 80),
    (50, 95),
]


def percentile_lookup(value: float, table: list[tuple[float, float]], reverse: bool = False) -> float:
    """根据 value 在 table 里线性插值得到百分位（0-100，越小越好）"""
    if reverse:
        table = sorted(table, key=lambda x: x[0])
        for i, (v, p) in enumerate(table):
            if value <= v:
                if i == 0:
                    return p
                prev_v, prev_p = table[i - 1]
                return prev_p + (p - prev_p) * (value - prev_v) / (v - prev_v)
        return table[-1][1]
    else:
        table = sorted(table, key=lambda x: -x[0])
        for i, (v, p) in enumerate(table):
            if value >= v:
                if i == 0:
                    return p
                prev_v, prev_p = table[i - 1]
                return prev_p + (p - prev_p) * (value - prev_v) / (v - prev_v)
        return table[-1][1]


def score_return(return_pct: float, your_max_return_pct: float = None) -> float:
    """收益率得分：30% 绝对 + 70% 排名"""
    if your_max_return_pct is None:
        your_max_return_pct = max(return_pct, 100)
    abs_part = (return_pct / your_max_return_pct * 100) * 0.30 if your_max_return_pct > 0 else 0
    percentile = percentile_lookup(return_pct, BENCHMARK_RETURN)
    rank_score = (100 - percentile)  # percentile 越小排名越前，转成得分
    rank_part = rank_score * 0.70
    return abs_part + rank_part


def score_drawdown(drawdown_pct: float) -> float:
    """最大回撤得分：80% 回撤排名 + 20% 修复期排名"""
    percentile = percentile_lookup(drawdown_pct, BENCHMARK_DRAWDOWN, reverse=True)
    rank_score = 100 - percentile
    # 修复期排名暂时和回撤排名相同（假设回撤小修复也快）
    return rank_score * 0.80 + rank_score * 0.20


def score_sharpe(sharpe: float, your_max_sharpe: float = None) -> float:
    """夏普比率得分：30% 绝对 + 70% 排名"""
    if your_max_sharpe is None:
        your_max_sharpe = max(sharpe, 4.0)
    abs_part = (sharpe / your_max_sharpe * 100) * 0.30 if your_max_sharpe > 0 else 0
    percentile = percentile_lookup(sharpe, BENCHMARK_SHARPE)
    rank_score = 100 - percentile
    rank_part = rank_score * 0.70
    return abs_part + rank_part


def score_volatility(vol_pct: float) -> float:
    """波动率得分：100% 看排名（越低越好）"""
    percentile = percentile_lookup(vol_pct, BENCHMARK_VOLATILITY, reverse=True)
    return 100 - percentile


def estimate_top4_prob(total_score: float) -> str:
    """根据综合得分粗估前 4 概率。"""
    if total_score >= 85:
        return "20-30%（很有可能进总榜前 4）"
    elif total_score >= 80:
        return "10-20%（有戏，但需要持续保持）"
    elif total_score >= 75:
        return "5-10%（在鼓励奖 12-50 名区间，需要进一步降回撤+提收益）"
    elif total_score >= 70:
        return "2-5%（鼓励奖中段，距前 4 较远）"
    elif total_score >= 60:
        return "<2%（鼓励奖后段）"
    else:
        return "<1%（建议复盘策略）"


def estimate(
    return_pct: float,
    drawdown_pct: float,
    sharpe: float,
    vol_pct: float,
) -> ScoreEstimate:
    r_score = score_return(return_pct)
    d_score = score_drawdown(drawdown_pct)
    s_score = score_sharpe(sharpe)
    v_score = score_volatility(vol_pct)

    total = 0.4 * r_score + 0.2 * d_score + 0.3 * s_score + 0.1 * v_score

    notes = []
    if return_pct < 0:
        notes.append("⚠️ 当前为亏损状态——按比赛规则可能影响多个分项")
    if drawdown_pct > 10:
        notes.append("⚠️ 回撤偏大——比赛公式严重惩罚，建议降仓")
    if sharpe < 1.0:
        notes.append("⚠️ 夏普 <1，风险调整收益偏弱——夏普占 30% 权重")
    if vol_pct > 25:
        notes.append("⚠️ 波动率偏高——降低单笔风险或减少品种数量")
    if drawdown_pct < 5 and sharpe > 2.0:
        notes.append("✅ 风控优秀——这是评分公式偏爱的画像")

    return ScoreEstimate(
        return_score=round(r_score, 2),
        drawdown_score=round(d_score, 2),
        sharpe_score=round(s_score, 2),
        volatility_score=round(v_score, 2),
        total=round(total, 2),
        estimated_rank_top4_prob=estimate_top4_prob(total),
        notes=notes,
    )


def main():
    parser = argparse.ArgumentParser(description="比赛评分公式自估")
    parser.add_argument("--return-pct", type=float, required=True, help="累计收益率（百分比，如 15）")
    parser.add_argument("--drawdown-pct", type=float, required=True, help="最大回撤（百分比，正数，如 5）")
    parser.add_argument("--sharpe", type=float, required=True, help="夏普比率，如 2.0")
    parser.add_argument("--vol-pct", type=float, required=True, help="年化波动率（百分比，如 12）")
    args = parser.parse_args()

    result = estimate(args.return_pct, args.drawdown_pct, args.sharpe, args.vol_pct)
    print("=" * 50)
    print("📊 比赛评分公式自估")
    print("=" * 50)
    print(f"  输入：")
    print(f"    收益率：{args.return_pct:+.1f}%")
    print(f"    最大回撤：{args.drawdown_pct:.1f}%")
    print(f"    夏普比率：{args.sharpe:.2f}")
    print(f"    波动率：{args.vol_pct:.1f}%")
    print()
    print(f"  各项得分（满分 100）：")
    print(f"    收益率分（40% 权重）：{result.return_score:.1f}")
    print(f"    回撤分  （20% 权重）：{result.drawdown_score:.1f}")
    print(f"    夏普分  （30% 权重）：{result.sharpe_score:.1f}")
    print(f"    波动分  （10% 权重）：{result.volatility_score:.1f}")
    print(f"  ─────────────────────────────")
    print(f"  综合得分：{result.total:.2f} / 100")
    print(f"  前 4 概率估算：{result.estimated_rank_top4_prob}")
    print()
    if result.notes:
        print("  建议：")
        for n in result.notes:
            print(f"    {n}")
    print("=" * 50)
    print("\n⚠️ 这是估算值。真实排名取决于实际参赛人数和分布。")
    print("   官方排名公布后，请校准本工具的 BENCHMARK 表。")


if __name__ == "__main__":
    main()
