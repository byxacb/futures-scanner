# FuturesBot - iOS 期货交易助手

## 快速开始（3 分钟）

### Step 1：安装 Xcode
App Store 搜索 "Xcode" → 安装（约 12GB，30 分钟）

### Step 2：创建项目
1. 打开 Xcode → File → New → Project
2. 选 **iOS** → **App**
3. Product Name: **FuturesBot**
4. Interface: **SwiftUI**
5. Language: **Swift**
6. Storage: **None**
7. 保存到 `/Users/bianyawen/Desktop/期货/FuturesBot/`（覆盖刚才创建的空目录）
8. 勾选 "Create Git repository" → 可选

### Step 3：替换源文件
1. 在 Xcode 左侧项目导航中，删除自动生成的 `ContentView.swift`
2. 把 `FuturesBot/` 目录下的所有 `.swift` 文件拖到 Xcode 项目中
   - 勾选 "Copy items if needed"
   - 勾选 "Add to targets: FuturesBot"
3. 文件结构：
   ```
   FuturesBot/
   ├── App/
   │   ├── FuturesBotApp.swift
   │   └── ContentView.swift
   ├── Models/
   │   └── Quote.swift
   ├── Services/
   │   ├── SinaAPI.swift
   │   ├── IndicatorEngine.swift
   │   ├── PositionCalculator.swift
   │   ├── SignalEngine.swift
   │   ├── LLMClient.swift
   │   ├── NotificationService.swift
   │   └── MarketService.swift
   └── Views/
       ├── Dashboard/DashboardView.swift
       ├── Monitor/MonitorView.swift
       ├── Trading/TradeDecisionView.swift
       ├── Chat/ChatView.swift
       ├── Settings/SettingsView.swift
       └── Knowledge/KnowledgeView.swift
   ```

### Step 4：添加 ATS 例外
Sina 期货行情 API 用的是 HTTP（不是 HTTPS），需要在 Info.plist 添加例外：

1. 点击项目名 → Info → 添加 Key: **App Transport Security Settings**
2. 展开它 → 添加 **Allow Arbitrary Loads** = **YES**

### Step 5：真机运行
1. iPhone 连接 Mac（USB 线）
2. Xcode 顶部选你的 iPhone 设备
3. 点 ▶️ 运行
4. iPhone 上：设置 → 通用 → VPN 与设备管理 → 信任你的开发者证书
5. 首次运行需要在 iPhone 上"设置 → 通用 → VPN 与设备管理"里信任证书

### Step 6：配置 API
App 打开后：
1. 点底部 **设置** tab
2. 填入 LLM API Key（小米 MiMo）
3. 填入 Bark URL（如果要推送）
4. 点 **保存**

---

## 功能清单

| 功能 | 状态 | 说明 |
|------|------|------|
| 实时行情 | ✅ | 5 个主力品种 + 28 个全品种支持 |
| K 线图 | ✅ | Swift Charts 日 K + MA 均线 |
| 技术指标 | ✅ | ATR/MA/MACD/RSI/布林/ADX/唐奇安 |
| 信号引擎 | ✅ | master_playbook 信号判定逻辑 |
| 仓位计算 | ✅ | 28 品种规格表 + 仓位公式 |
| LLM 对话 | ✅ | 接入 MiMo API，预置策略 prompt |
| 交易决策卡 | ✅ | 今日买什么卖什么 + 止损价 |
| 本地通知 | ✅ | 每日 08:30 盘前 + 15:15 盘后 |
| Bark 推送 | ✅ | 实时止损/突破告警 |
| 知识库浏览 | ✅ | 20 条铁律 + 策略 + 品种 + 书籍 |
| Keychain 存储 | ✅ | API Key 安全存储 |

---

## 技术栈

- **SwiftUI** + **Swift 5.9** + **iOS 16.0+**
- **Swift Charts**（K 线图）
- **URLSession**（网络请求，无第三方依赖）
- **UNUserNotificationCenter**（本地通知）
- **Keychain**（API Key 安全存储）

**零第三方依赖** — 全部用 Apple 原生框架。

---

## 知识库迁移

从电脑端 `books/` / `strategy/` / `products/` 迁移到 iOS App 内嵌：

| 来源 | iOS 位置 | 大小 |
|------|---------|------|
| 100 本书提炼 | `KnowledgeView` 硬编码 | ~5KB |
| 20 条铁律 | `KnowledgeView.consensusRules` | ~2KB |
| 策略规则 | `SignalEngine.swift` | ~1KB |
| 品种手册摘要 | `KnowledgeView.productsList` | ~1KB |
| 合约规格 | `PositionCalculator.specs` | ~2KB |
| **总计** | | **~11KB** |

---

## 从电脑端工具链对应的 Swift 模块

| Python 文件 | Swift 文件 | 功能 |
|------------|-----------|------|
| `data/fetch_market.py` | `Services/SinaAPI.swift` | 行情抓取 |
| `indicators/compute.py` | `Services/IndicatorEngine.swift` | 技术指标 |
| `risk/position_calc.py` | `Services/PositionCalculator.swift` | 仓位计算 |
| `risk/score_simulator.py` | 内嵌在 TradeDecisionView | 评分公式 |
| `news/sentiment.py` | `Services/LLMClient.swift` + ChatView | LLM 情绪分析 |
| `briefing/morning.py` | `Services/MarketService.swift` + DashboardView | 简报生成 |
| `monitor/live_watch.py` | `Services/MarketService.swift` + NotificationService | 实时监控 |
| `notify/sender.py` | `Services/NotificationService.swift` | 推送通知 |

---

## 常见问题

**Q: 真机运行报 "Untrusted Developer"？**
A: iPhone → 设置 → 通用 → VPN 与设备管理 → 点你的开发者证书 → 信任

**Q: Sina API 拉不到数据？**
A: 确认 Info.plist 已添加 ATS 例外（Allow Arbitrary Loads = YES）

**Q: LLM 调用报 401？**
A: 检查 API Key 是否正确；确认 Base URL 是否为 `https://token-plan-cn.xiaomimimo.com/anthropic`

**Q: 通知不弹？**
A: iPhone → 设置 → 通知 → FuturesBot → 允许通知

**Q: 后台不刷新？**
A: iOS 限制后台刷新最小间隔 ~15 分钟。App 打开时每 30 秒刷新。后台通知走 Bark（从 Mac 推送）。
