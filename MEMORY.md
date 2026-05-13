# MEMORY.md（技术决策与跨会话状态）

> 本文件记录项目的技术决策、重要变更和当前状态。每个任务结束前必须更新。

---

## 当前状态（2026-05-12）

- **阶段**：比赛进行中（第2个交易日）
- **比赛软件**：国贸期货掘金雷达（微信小程序）
- **账户**：100万虚拟金，已开赛
- **当前持仓**：RB2610 多单12手，成本3290，止损建议上移至3260
- **API Key**：MiMo via token-plan 已配置在 .env，端到端通
- **新增**：lessons_learned.md（工具/策略复盘日志）、multi_perspective_analysis.md（多视角分析框架）

## 当前状态（2026-05-13）

- 用户最新核心诉求：云端每5分钟必须“真分析”，不是固定文案重复推送
- 已修复 `tools/research/cloud_scanner.py`：
  1. 引入 `ak.futures_zh_spot` 实时价格（优先）驱动触发
  2. 开仓触发改为突破价：做多用 `>= trigger`，做空用 `<= trigger`
  3. 增加“仅可执行才推送”逻辑，避免无操作价值噪音
  4. 增加盈亏比硬过滤：`rr_ratio < 2` 一律不推送
  5. Bark 解析容错增强（非 JSON 响应也能判定）
  6. 每轮写 `daily/last_scan_debug.json`，记录 `news_count/data_ok/spot_ok`
- 本地验证证据：
  - 运行 `python3 -u tools/research/cloud_scanner.py`
  - 输出显示：联网抓到新闻 31 条；扫描 55 品种；实时价字段持续刷新
  - 最新 debug 文件：
    - `timestamp`: 2026-05-13T14:22:14
    - `news_count`: 31
    - `data_ok`: 18
    - `spot_ok`: 17
    - `count`: 0（本轮无可执行机会，因此按规则不推送）

## 已交付清单（150+ 文件）

| 模块 | 文件数 | 说明 |
|------|--------|------|
| 顶层配置 | 3 | CLAUDE.md / MEMORY.md / 对话.md |
| rules/ | 2 | 比赛规则原文 + 评分公式数学拆解 |
| primer/ | 6 | 零基础课程 6 课（合约/开平仓/止损/技术/基本面/心理） |
| books/ | 102 | 100 本投资书提炼 + _index + _consensus（20 条铁律） |
| products/ | 16 | 6 大交易所 15 个主流品种手册 + 索引 |
| strategy/ | 4 | master_playbook / position_sizing / stop_loss_rules / daily_workflow |
| tools/ | 20 | Python 工具链（data/indicators/risk/news/briefing/monitor）+ score_simulator |

## 关键技术决策

### 2026-05-11 项目启动

**决策 1：策略取向 = 受控激进**
- 评分公式 60% 权重在惩罚风险（回撤 20% + 夏普 30% + 波动率 10%）
- 数学：激进策略前 4 概率 5-10% + 30% 概率穿仓 0 分；受控激进前 4 概率 15-20%
- 实现：基础仓 30-40%、单品种 ≤10%、单笔 1%、高确信叠加 1.5x

**决策 2：知识库 = Markdown 笔记库**
- 100 篇书目笔记 + _consensus.md 共识总结
- 不爬盗版（违法+硬规则），靠维基 + Goodreads + 训练记忆

**决策 3：盯盘工具 = Python + akshare + LLM API**
- akshare 免费拉国内期货行情
- DeepSeek/智谱/豆包 任一可用 LLM 做新闻情绪
- API Key 走 .env，永不硬编码

**决策 4：用户必须亲自下单**
- Claude 安全规则不允许替用户操作账户
- 我只生成建议，用户在比赛软件执行

**决策 5：单笔风险率 = 1%（比 master_playbook 写得更严）**
- 海龟原版用 2%，但本次比赛 100 万本金 + 100 天周期 + 评分公式重风险
- 用 1% 让"100 单容错"，回撤可控

### 2026-05-11 工具链验证（已 pass）

- `indicators.compute.signal_summary`：✅ 跑通，ATR/MA/MACD/RSI/布林/唐奇安/ADX 全部计算正确
- `risk.position_calc.calc_position`：✅ 跑通，rb @3500 ATR=50 → 10 手 / 42000 保证金 / 4.2% / risk_pct=1.0%
- `risk.position_calc.validate_portfolio`：✅ 跑通，组合违规检测正常
- `risk.score_simulator`：✅ 跑通，三档画像分别得 50.14 / 71.80 / 78.86 分
- 待跑通：`data.fetch_market`（需要 akshare 实装）、`news.sentiment`（需要 API Key）、`briefing.morning/evening`（依赖前两者）

## 关键文件指针

- `CLAUDE.md` — 项目级最高准则
- `rules/评分公式拆解.md` — 策略数学基础
- `strategy/master_playbook.md` — **主策略宪法**
- `strategy/daily_workflow.md` — 每日操作流程
- `books/_consensus.md` — 100 本书共识 20 条铁律
- `tools/briefing/morning.py` — 盘前简报入口
- `tools/risk/score_simulator.py` — 评分公式自估工具

## 评分模型验证（score_simulator 自测）

| 画像 | 收益 | 回撤 | 夏普 | 波动 | 综合分 | 估算 |
|------|-----|-----|------|-----|--------|------|
| 激进满仓 | 60% | 40% | 0.8 | 50% | 50.14 | <1% 前 4 |
| 稳健 | 15% | 5% | 2.0 | 12% | 71.80 | 2-5% 前 4 |
| 目标（基础） | 25% | 8% | 2.0 | 15% | 73.50 | 2-5% 前 4 |
| **目标（理想）** | **35%** | **7%** | **2.5** | **14%** | **78.86** | **5-10% 前 4** |

→ 想突破 80 分进入"高概率前 4"区，需要 35%+ 收益 + ≤7% 回撤 + ≥2.5 夏普

## 已踩坑的教训

1. **2026-05-11**：`signal_summary` 返回 numpy bool 不能 JSON 序列化 → 修复用 `bool()` 强转
2. **2026-05-11**：`score_simulator` 文档字符串里嵌引号导致语法错误 → 简化文档字符串
3. **2026-05-11**：用户在聊天中直接粘贴 API Key → 已警告其重置 key 并改填到 `.env`；同时给 `sentiment.py` 加 `anthropic-compatible` provider，支持小米 MiMo via token-plan 代理；写 `tools/SETUP_API.md` 给用户对照配置

## 2026-05-11 LLM 配置变更

- 默认 provider 从 `deepseek` 改为 `anthropic`（兼容 Anthropic Messages API）
- 用户使用：小米 MiMo via `token-plan-cn.xiaomimimo.com/anthropic`，模型 `mimo-v2.5-pro`
- 接入方式：环境变量 `ANTHROPIC_API_KEY` / `ANTHROPIC_BASE_URL` / `ANTHROPIC_MODEL`
- 实际 key 待用户重置后填入 `tools/.env`（聊天暴露的那个不要用了）

## 待办与悬念

### 已解决（2026-05-11）

- ✅ 比赛软件：**国贸期货掘金雷达**（微信小程序）
- ✅ 比赛已开始
- ✅ 账户已开通，100 万模拟金
- ✅ LLM API Key 用户授权使用聊天暴露的那个（已写入 .env，端到端通了）
- ✅ akshare 数据源工作正常（修了 sina API 适配）
- ✅ launchd 定时任务已注册（08:30 盘前 + 15:15 盘后）

### 当前阻塞（待用户确认）

- [ ] 掘金雷达是否支持条件单/止损单——决定 Plan A vs Plan B
- [ ] rb 当前主力合约月份（RB2510/2601/2605/2610?）
- [ ] 是否需要把 books/ 转为 Obsidian vault

### 工具链待补（按优先级）

1. [ ] `analysis/backtest.py` 历史回测主策略
2. [ ] `analysis/account_track.py` 净值/回撤自动追踪
3. [ ] `briefing/weekly.py` 周复盘脚本
4. [ ] `briefing/morning.py` 集成 fetch_news.py 新闻情绪
5. [ ] `monitor/live_watch.py` 桌面通知扩展到 Windows / Linux

### 新增文件（2026-05-12）

- ✅ `tools/news/fetch_news.py` — mysteel 新闻抓取（WebFetch 直连方案验证通过）
- ✅ `strategy/multi_perspective_analysis.md` — 多视角分析框架（经济学+技术+风控+基本面+心理学）
- ✅ `lessons_learned.md` — 工具/策略复盘日志（持续更新）
- ✅ `daily/2026-05-12.md` — 首次多视角分析日志

### 知识库可扩展

- [ ] 把 100 本书转 Obsidian wikilink 知识图谱
- [ ] 加 D 档中文书的具体案例研究（如付海棠 2010 棉花、林广茂 2010 豆粕）
- [ ] 加期权专题（如果用户后期想做期权）
