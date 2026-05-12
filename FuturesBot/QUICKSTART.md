# 🚀 3 分钟启动指南

## Step 1：装 Xcode（只需一次）

App Store → 搜 **"Xcode"** → 安装（约 12GB，30 分钟）

## Step 2：打开项目

```bash
open /Users/bianyawen/Desktop/期货/FuturesBot/FuturesBot.xcodeproj
```

或者：Xcode → File → Open → 选 `FuturesBot.xcodeproj`

## Step 3：选你的 iPhone → 点 ▶️

1. Xcode 顶部设备栏 → 选你的 iPhone（需要 USB 连接）
2. 点 ▶️ 运行
3. 首次运行：iPhone → 设置 → 通用 → VPN 与设备管理 → 信任你的开发者证书

## Step 4：允许通知

App 首次启动会弹出"允许通知"→ 点 **允许**

---

## ✅ 预配置的内容（你不需要填任何东西）

| 配置 | 值 |
|------|-----|
| LLM API | 小米 MiMo via token-plan（已内置） |
| Bark 推送 | 已内置你的 Bark URL |
| 盯盘品种 | rb/m/au/IF/sc（5 个主力） |
| 定时通知 | 08:30 盘前 + 15:15 盘后 |
| 信号监控 | 每 30 秒自动拉行情，每 5 分钟重算信号 |
| 强信号推送 | 出现强信号自动推 Bark + 本地通知 |

---

## 📱 App 使用流程

### 每天早上 08:30
1. iPhone 收到通知："📊 盘前简报已生成"
2. 打开 FuturesBot → 看「简报」tab
3. 看「交易」tab → 今日决策卡告诉你买什么卖什么
4. 去掘金雷达下单

### 盘中（09:00-15:00）
1. 收到 🔥 通知 → 打开 FuturesBot → 看信号详情
2. 去掘金雷达操作 → 截图发给 Claude agent
3. 收到 ⚠️ 止损通知 → 去掘金雷达挂止损

### 每天下午 15:15
1. 收到通知："📉 盘后复盘"
2. 打开 FuturesBot → 看「简报」tab 的更新
3. 在掘金雷达截图持仓发给 Claude agent

---

## 🔥 自动化功能

### 信号自动推送
- 每 30 秒拉行情（App 打开时）
- 检测到新强信号 → **立即推 Bark + 本地通知**
- 信号减弱 → 推通知提醒风险

### 定时简报
- 08:30 自动推送"盘前简报已生成"
- 15:15 自推送"盘后复盘"

### AI 助手
- 点「AI 助手」tab → 直接问期货问题
- 预置策略 prompt（master_playbook + 20 条铁律）
- 支持"今天 rb 怎么做"等自然语言

---

## ⚠️ 注意事项

1. **App 打开时**每 30 秒刷新行情；**后台**不会自动刷新（iOS 限制）
2. **实时止损通知**需要 App 在前台或通过 Bark 从 Mac 推送
3. **不要删除 FuturesBot.xcodeproj** — 这是 Xcode 项目文件
4. **如果编译报错**：检查 Xcode 版本 ≥ 15，iOS 部署目标 ≥ 16.0
