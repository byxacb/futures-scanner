# tools/ — 期货比赛盯盘工具链

## 快速开始

```bash
# 1. 装依赖
cd /Users/bianyawen/Desktop/期货
pip install -r tools/requirements.txt

# 2. 配置 API Key（仅当要用新闻情绪功能）
cp tools/.env.example tools/.env
# 编辑 .env 填入 DEEPSEEK_API_KEY

# 3. 跑一次盘前简报测试
cd tools
python -m briefing.morning --symbols rb,m,au,IF,sc

# 4. 收盘后跑复盘
python -m briefing.evening --symbols rb,m,au,IF,sc

# 5. 盘中监控（需先有 watchlist.json）
python -m monitor.live_watch
```

## 模块

| 模块 | 作用 |
|------|------|
| `data/fetch_market.py` | akshare 行情抓取（日 K + 实时） |
| `indicators/compute.py` | ATR/MA/MACD/RSI/布林/唐奇安/ADX |
| `risk/position_calc.py` | 仓位 + 组合校验 |
| `news/sentiment.py` | LLM 情绪打分（需 API Key） |
| `briefing/morning.py` | 盘前简报生成 |
| `briefing/evening.py` | 盘后复盘框架 |
| `monitor/live_watch.py` | 盘中实时监控 + 桌面通知 |

## 自测

每个文件都有 `if __name__ == "__main__"` 自测块，可以单独跑：

```bash
python -m data.fetch_market           # 拉螺纹钢日 K
python -m indicators.compute          # 算技术指标
python -m risk.position_calc          # 仓位算法演示
python -m news.sentiment              # LLM 情绪（需 Key）
```

## 安全

- ⚠️ `.env` 永远不要 commit（已在 `.gitignore`）
- ⚠️ API Key 只在 `.env` 中，代码里读环境变量
- ⚠️ 本工具不下单——只生成建议，由你在比赛软件操作

## 计划增强（按优先级）

1. [ ] `news/fetch_news.py` 真实爬虫（财联社+华尔街见闻）
2. [ ] `briefing/morning.py` 集成 LLM 情绪
3. [ ] `risk/account_track.py` 自动更新当前净值（手动录入也行）
4. [ ] `analysis/backtest.py` 历史数据回测主策略
5. [ ] `analysis/score_simulator.py` 评分公式自估（输入收益/回撤/夏普/波动）
