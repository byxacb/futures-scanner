# 自动化运行说明

> 2026-05-11 配置完成。本机已注册定时任务，每个交易日自动产出简报。

## 已配置的定时任务

| 任务 | 时间 | 命令 | 输出 |
|------|------|------|------|
| `com.bianyawen.futures.morning` | 周一-五 08:30 | `morning.py --symbols rb,m,au,IF,sc` | `daily/YYYY-MM-DD.md` 的盘前段 |
| `com.bianyawen.futures.evening` | 周一-五 15:15 | `evening.py --symbols rb,m,au,IF,sc` | 同上的盘后段 |

均为 macOS `launchd` 用户级任务，重启后自动恢复。

## 查看运行状态

```bash
launchctl list | grep futures
# 输出 PID/exit_code/label，exit_code=0 表示上次跑成功

# 看最近一次输出
tail -50 /Users/bianyawen/Desktop/期货/daily/cron.out
tail -50 /Users/bianyawen/Desktop/期货/daily/cron.err  # 错误流

# 看最新简报
ls -lt /Users/bianyawen/Desktop/期货/daily/*.md | head -3
```

## 手动跑一次

不等定时器：
```bash
cd /Users/bianyawen/Desktop/期货
python3 -m tools.briefing.morning --symbols rb,m,au,IF,sc
python3 -m tools.briefing.evening --symbols rb,m,au,IF,sc
```

## 暂停 / 重启 / 卸载

```bash
# 暂停
launchctl unload ~/Library/LaunchAgents/com.bianyawen.futures.morning.plist

# 重启
launchctl load ~/Library/LaunchAgents/com.bianyawen.futures.morning.plist

# 永久卸载
rm ~/Library/LaunchAgents/com.bianyawen.futures.morning.plist
rm ~/Library/LaunchAgents/com.bianyawen.futures.evening.plist
```

## 修改时间或品种池

编辑：`~/Library/LaunchAgents/com.bianyawen.futures.morning.plist`
改：
- 时间：`StartCalendarInterval` 里的 `Hour` / `Minute`
- 品种：`--symbols rb,m,au,IF,sc` 这个参数

改完后：
```bash
launchctl unload ~/Library/LaunchAgents/com.bianyawen.futures.morning.plist
launchctl load ~/Library/LaunchAgents/com.bianyawen.futures.morning.plist
```

## 哪些没有自动化（仍需用户操作）

| 项目 | 为什么不自动 |
|------|------|
| **实际下单** | 安全硬规则——必须用户本人在比赛软件操作 |
| **API Key 配置** | 安全——绝不让 Key 在自动流程中暴露 |
| **比赛账户登录** | 主办方反作弊——账号密码绝不上 Claude |
| **复盘心得文字** | 复盘需要个人反思，机器写的没意义 |
| **盘中临时调仓** | 突发行情需要用户判断 |

## 自动化能延伸做的事（按需开启）

1. **盘中实时监控**：开机后手动启动 `python3 -m tools.monitor.live_watch`，桌面通知止损/突破触发
2. **夜盘简报**（20:30）：再加一个 plist，仅金属/能化/股指夜盘品种
3. **周复盘**（周日 20:00）：见 todo——`briefing/weekly.py` 待写
4. **新闻情绪自动打分**：需要你先把 LLM API Key 填到 `tools/.env`
