# HANDOFF.md（项目交接 - 给下一任 agent）

> **下一任 agent 必读**。读完本文件 + 全局 `~/.claude/CLAUDE.md` + 项目 `CLAUDE.md` + `MEMORY.md` + `对话.md` 才能开始执行新任务。

---

## 0. 项目身份（30 秒了解）

- **项目**：第二届国贸期货杯·厦门大学（模拟期货交易比赛）
- **用户身份**：厦大在校生，**完全零基础**，要拿**一等奖**（前 4）
- **比赛软件**：国贸期货掘金雷达（**微信小程序**，不是 PC 软件）
- **账户**：100 万虚拟金，**禁止出入金**，穿仓即出局
- **比赛交易品种**：上期所/大商所/郑商所/中金所/能源中心/广期所 所有期货+期权
- **手续费 ×2、保证金 +3%**（比赛规则）
- **评分公式**：收益率 40% + 最大回撤 20% + 夏普 30% + 波动率 10% → **60% 在惩罚风险**
- **比赛状态**：**已开始**（2026-05-11 确认）

---

## 1. 核心战略（不可妥协）

### 数学事实

激进满仓策略（60% 收益、40% 回撤、0.8 夏普、50% 波动率）→ 综合得分 **50.14** → 前 4 概率 **<1%**
受控激进（35% 收益、7% 回撤、2.5 夏普、14% 波动率）→ 综合得分 **78.86** → 前 4 概率 **5-10%**

**结论**：不是"赚得多"赢，是"综合得分高"赢——而综合得分公式偏爱低回撤+高夏普。

### 主策略 = 受控激进

- 基础仓位 30-40%（不满仓）
- 单笔风险 **1%** 账户净值（不是 2%）
- 单品种保证金占用 ≤10%
- 单方向（多/空合计）≤40%
- 总保证金 ≤70%
- 高确信信号叠加到 60-70%
- 趋势跟踪为主（20 日唐奇安通道突破 + MA20/60 + 量增 + ADX>25 + 新闻面情绪）
- ATR 仓位法（止损 = 2×ATR、加仓金字塔每 +1×ATR 加 1 单位、最多 4 单位）

### 用户反复说"我不怕风险"——必须诚实回应

不是讨好他。每次他说要激进，给他看 score_simulator 的数字：激进满仓 vs 受控激进得分差 28 分。坚持执行 master_playbook。

---

## 2. 项目文件结构（每个文件干嘛用的）

```
/Users/bianyawen/Desktop/期货/
│
├── CLAUDE.md                    # 项目最高准则。继承全局 CLAUDE.md，加项目专属硬约束
├── MEMORY.md                    # 技术决策与跨会话状态记忆。每次任务结束必更新
├── 对话.md                      # 用户原话+Claude 回复要点记录
├── HANDOFF.md                   # ← 本文件 ←
├── AUTOMATION.md                # launchd 定时任务说明（启停、查日志）
│
├── rules/
│   ├── 比赛规则.md              # 原文存档，禁止修改
│   └── 评分公式拆解.md           # 公式数学推导。WHY 受控激进 = 最优策略
│
├── primer/                      # 零基础课程（用户必读）
│   ├── 01_合约与保证金.md        # 合约乘数、保证金率、杠杆
│   ├── 02_多空开平仓.md          # 4 种操作、限价/市价、止损
│   ├── 03_止损与仓位管理.md      # ATR 仓位法、凯利公式（核心）
│   ├── 04_技术分析入门.md        # K 线、MA、MACD、RSI、布林、ADX
│   ├── 05_基本面框架.md          # 各板块基本面驱动
│   └── 06_交易心理与日常.md      # 心理陷阱、复盘模板、红线触发
│
├── books/                       # 100 本投资经典提炼
│   ├── _index.md                # 100 本目录 + 5 档优先级（S/A/B/C/D）
│   ├── _consensus.md            # ★★ 100 本共识的 20 条铁律 ★★
│   ├── 001_股票作手回忆录_Livermore.md
│   ├── 002_海龟交易法则_Faith.md
│   ├── 003_金融怪杰1_Schwager.md
│   ├── 004-010 (S 档 7 本)
│   ├── 011-030 (A 档 20 本)
│   ├── 031-060 (B 档 30 本)
│   ├── 061-090 (C 档 30 本)
│   └── 091-100 (D 档 10 本中文实战派)
│
├── products/                    # 期货品种手册
│   ├── _index.md                # 全品种索引+流动性评级
│   ├── 螺纹钢_rb.md             # 主力池：黑色
│   ├── 豆粕_m.md                # 主力池：农产品
│   ├── 沪金_au.md               # 主力池：贵金属（避险对冲）
│   ├── 沪深300_IF.md            # 主力池：金融指数（注：合约大不易做）
│   ├── 原油_sc.md               # 主力池：能化（独立头寸）
│   └── 候补 10 个 (hc/i/y/p/cu/ag/FG/MA/IH/T)
│
├── strategy/                    # ★ 主策略文档 ★
│   ├── master_playbook.md       # 主策略宪法（每条规则必须在 books/_consensus 里有 3 本以上书源）
│   ├── position_sizing.md       # 仓位计算手册（每次开仓必查）
│   ├── stop_loss_rules.md       # 5 种止损 + 紧急止损红线
│   └── daily_workflow.md        # 每日工作流（08:00-23:00 时间表）
│
├── tools/                       # Python 盯盘工具链
│   ├── requirements.txt         # pip 依赖（akshare、pandas、httpx 等）
│   ├── .env                     # ⚠️ API Key/邮箱密码/Bark URL（已 .gitignore）
│   ├── .env.example             # .env 模板
│   ├── .gitignore               # 排除 .env 和 cache/
│   ├── config.example.toml      # 默认配置模板
│   ├── README.md                # 工具链使用说明
│   ├── SETUP_API.md             # API Key 配置指南
│   │
│   ├── data/fetch_market.py     # akshare 期货行情抓取
│   ├── indicators/compute.py    # 技术指标（ATR/MA/MACD/RSI/布林/唐奇安/ADX）+ signal_summary
│   ├── risk/position_calc.py    # 仓位计算 + 组合校验（含 28 个品种 SPECS 表）
│   ├── risk/score_simulator.py  # 评分公式自估
│   ├── news/sentiment.py        # LLM 新闻情绪打分（小米 MiMo via token-plan）
│   ├── briefing/morning.py      # 盘前简报（自动写 daily/ + 推送）
│   ├── briefing/evening.py      # 盘后复盘（自动写 daily/ + 推送）
│   ├── monitor/live_watch.py    # 盘中实时监控（30s 轮询 + Bark 推送）
│   └── notify/sender.py         # 推送通道（Bark + 邮件）
│
└── daily/                       # 每日交易日志（开赛后自动生长）
    ├── 2026-05-11.md            # 首日盘前简报
    ├── 2026-05-11_trade_plan.md # 首日交易计划
    ├── 2026-05-11_watchlist.json # 监控关键价位
    └── cron.log/.out/.err        # launchd 任务日志
```

---

## 3. 已配置的自动化（重要）

### launchd 定时任务

```bash
launchctl list | grep futures
# 应该看到 2 个：
# com.bianyawen.futures.morning  → 周一-五 08:30 自动跑 morning.py
# com.bianyawen.futures.evening  → 周一-五 15:15 自动跑 evening.py
```

控制：见 `AUTOMATION.md`

### 推送通道（已验证可工作）

| 通道 | 配置 | 用途 |
|------|------|------|
| **Bark**（iOS）| BARK_URL=https://api.day.app/S3QnU9QTHddi3XB8Pc8E8o | 实时止损/突破告警 |
| **QQ 邮件** | SMTP_HOST=smtp.qq.com / USER=3137457185@qq.com | 长简报存档 |

测试：`python3 -c "import sys; sys.path.insert(0,'tools'); from notify.sender import notify; notify('测试','内容')"`

### LLM API（已验证可工作）

- 端点：`https://token-plan-cn.xiaomimimo.com/anthropic`（小米 MiMo 走 Anthropic 兼容协议）
- 模型：`mimo-v2.5-pro`
- 用途：新闻情绪打分
- 注意：用户在聊天里暴露过 key 但表示不在意——`.env` 已写入。如重置可直接改 `.env`

---

## 4. 用户当前持仓 / 挂单状态

### 已挂条件单（2026-05-11 晚 提交到掘金雷达）

```
合约：RB2610（螺纹钢 2026 年 10 月合约）
方向：买入开仓（做多）
触发条件：当行情价格 ≥ 3275
委托价格类型：指定价 3290（限价上限）
数量：12 手
有效期：当日（明天 2026-05-12 日盘有效）
预计保证金占用：~28,400 元 / 占账户 ~2.84%
```

### 信号依据

- 突破 20 日新高（3285）
- MA20(3176) > MA60(3127) 上升趋势
- 成交量放大 ≥ 20 日均量 × 1.2
- ADX 32.2 → 强趋势市
- LLM 新闻情绪 +0.60 / 把握度 0.90
- **风险**：RSI 已 77.5 接近超买，所以起步只开 12 手（不上系统 25 手上限）

### 明早需做的（开仓成交后）

```
立刻挂"指定价格止损"：
- 合约 RB2610
- 止损触发价 3227（约 -2×ATR，依实际成交价微调）
- 手数 12（全平）
- 类型：市价平仓
```

### 加仓阶梯（成交后浮盈到达即操作）

| 浮盈价位 | 操作 | 全仓止损上移到 |
|---------|------|---------------|
| 3299（+29 = 1×ATR） | 再开多 4 手 | 3243 |
| 3328（+58 = 2×ATR） | 再开多 4 手 | 3270（成本线） |
| 3357（+87 = 3×ATR） | 再开多 4 手满 24 手 | 3299 |

### 红线（触发任一立即执行）

- 单日浮亏 -3%（=30,000 元）→ 全平 + 当日停手
- 单笔亏损达 -2% 账户（=20,000 元）→ 紧急止损（不等技术位）
- 出现重大利空 → 立即评估、必要时减半

---

## 5. 每日工作流（开赛后日常）

| 时间 | 谁做 | 做什么 |
|------|------|--------|
| 08:30 | launchd 自动 | 跑 morning.py → 生成 `daily/YYYY-MM-DD.md` → 推送 Bark+邮件 |
| 08:30-08:50 | 用户+agent | 用户看简报截图发 agent；agent 判定是否符合 master_playbook |
| 08:55 | 用户 | 跑 `python3 -m tools.monitor.live_watch`（带 watchlist.json） |
| 09:00 | 比赛软件 | 条件单自动执行 |
| 09:01 | 用户+agent | 截图持仓发 agent；agent 指导挂止损 + 加仓位置 |
| 09:00-15:00 | live_watch 监控 | 触发关键价 → Bark 推送 → 用户去掘金雷达手动平仓/加仓 |
| 15:15 | launchd 自动 | 跑 evening.py → 复盘框架 + 推送 |
| 15:15-15:30 | 用户+agent | 用户填复盘心得；agent 校对哪笔单是策略错 vs 执行错 |
| 周日 20:00 | 用户+agent | 跑 score_simulator 自估得分；调整品种池 |

---

## 6. 不可妥协的硬规则（继承自全局 + 项目 CLAUDE.md）

1. **绝不替用户下单**——只生成建议，用户在掘金雷达手动操作
2. **绝不索要账号密码**
3. **绝不给出会导致穿仓的建议**——单品种 ≤30%（master_playbook 用 10%）、无止损不下、马丁加仓严禁
4. **诚实底线**——没把握说"不确定"；亏了诚实归因；不甩锅市场
5. **不抓盗版书 / 不绕版权**——只用维基/Goodreads/SSRN/公版/训练记忆
6. **API Key 绝不硬编码**——只在 .env 里
7. **绝不承诺前 4**——只能"提高前 4 概率到 15-20%"

---

## 7. 用户性格档案（agent 必须知道）

- **完全零基础**：未做过实盘期货，但有比赛账户，要交易
- **耐心阈值低**：曾说"听我的话""我要全自动""你就告诉我每天买什么卖什么"——倾向于跳过学习直接执行
- **反复表达"不怕风险"**：每次都要用 score_simulator 数字反驳，不能讨好
- **API Key 暴露过 1 次**：用户授权使用（已写入 .env），下次需提醒重置
- **手机比电脑勤**：所以已配 Bark + 邮件双通道推送

---

## 8. 已踩坑的教训（避免重复）

1. **akshare sina 接口变更**——`futures_main_sina` 不可用，改用 `futures_zh_daily_sina("RB0")` 主连
2. **shell 环境变量预设干扰 .env**——`_load_env` 已改为强制覆盖
3. **signal_summary 返回 numpy bool 不能 JSON 序列化**——已用 `bool()` 强转
4. **AnthropicAPI 走代理**——必须 .env 强覆盖 ANTHROPIC_BASE_URL 否则走官方
5. **PTA 在 akshare 里代号 TA 不是 PTA**——已加 SYMBOL_ALIAS 映射
6. **IF/sc 单手亏损 > 1% 风险预算**——100 万账户做不动，已在 master_playbook 标注

---

## 9. 下一步（agent 接手后第一步该做的）

1. **读完本文件 + CLAUDE.md + MEMORY.md + 对话.md**（10 分钟）
2. **去 `daily/` 看最新一份简报和交易记录**
3. **等用户报告 RB2610 是否触发**——触发了立刻指导挂止损
4. **明早 08:30 后**：让用户截图新简报，按 master_playbook 评估今日决策
5. **不允许偏离 master_playbook**——除非有 books/_consensus 至少 3 本书的证据支持调整

---

## 10. 紧急联系/恢复

- 比赛规则疑问：陈老师 18065717659
- 工具报错：cd /Users/bianyawen/Desktop/期货 && cat daily/cron.err
- 单元自测：`python3 -m tools.risk.position_calc`（应输出仓位 10 手等正确数字）
- 拉行情自测：`python3 -c "import sys;sys.path.insert(0,'tools');from data.fetch_market import get_daily_kline; print(get_daily_kline('rb').tail(3))"`
- 推送自测：`python3 -m tools.notify.sender "测试" "内容"`

---

最后：**评分公式 60% 在惩罚风险**——这一句话比所有书都重要。每次决策前问自己"这会让回撤变大还是变小？让夏普升还是降？"
