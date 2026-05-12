#!/bin/bash
# 盘中自动监控脚本 - launchd 调用
# 全品种扫描 + 抓新闻 + 检查持仓 + 大白话推送

cd /Users/bianyawen/Desktop/期货

DATE=$(date +%Y-%m-%d)
LOG="daily/cron.log"

echo "[$(date '+%H:%M:%S')] === 盘中自动监控 ===" >> "$LOG"

# 1. 全品种扫描找机会（核心功能）
python3 -c "
import sys
sys.path.insert(0, 'tools')
from research.scanner import run_scan
run_scan()
" >> "$LOG" 2>&1

# 2. 抓新闻
python3 -c "
import sys
sys.path.insert(0, 'tools')
from news.fetch_news import fetch_mysteel_futures_news
from notify.sender import notify
items = fetch_mysteel_futures_news(keywords=['螺纹钢','螺纹','黑色','钢材','铁矿','铜','原油','豆粕','黄金'], limit=5)
if items:
    lines = []
    for item in items[:3]:
        lines.append(f'• {item.title}')
    notify('📰 最新新闻', '\n'.join(lines), level='info')
    print(f'抓到 {len(items)} 条新闻')
" >> "$LOG" 2>&1

# 3. 检查持仓的关键价位（大白话）
python3 -c "
import sys
sys.path.insert(0, 'tools')
from datetime import datetime
now = datetime.now()
hour = now.hour
if (9 <= hour < 12) or (13 <= hour < 15):
    from data.fetch_market import get_realtime_quote
    from notify.sender import notify

    # 检查 RB 持仓
    q = get_realtime_quote('rb')
    if q and q.get('price', 0) > 0:
        price = q['price']

        if price >= 3320:
            msg = f'''螺纹钢现价 {price}

🟢 好消息！价格涨到3320以上了。

操作建议：
1. 打开掘金雷达
2. 再买一些螺纹钢（加仓）
3. 把止损价改到 3300（保护利润）

注意：不要一次加太多，再买原来的一半就行。'''
            notify('🚀 螺纹钢涨了！可以加仓', msg, level='urgent')

        elif price <= 3250:
            msg = f'''螺纹钢现价 {price}

🔴 价格跌到3250了，接近止损位。

操作建议：
1. 打开掘金雷达
2. 把螺纹钢全部卖掉（平仓）
3. 等下次机会再做

原因：跌破3250说明趋势可能变了，先保住钱。'''
            notify('⚠️ 螺纹钢要止损了！', msg, level='urgent')

        elif price <= 3260:
            msg = f'''螺纹钢现价 {price}

⚠️ 价格接近止损位3260了。

操作建议：
1. 打开掘金雷达
2. 检查止损单还在不在
3. 如果止损单没了，重新设一个：止损价 3260

现在不要动，等它自己走。跌破3260就卖。'''
            notify('🔔 螺纹钢快到止损位了', msg, level='warn')

        else:
            print(f'RB现价: {price}，正常区间，不用管')
    else:
        print('无法获取实时价格')
else:
    print(f'非交易时间 {now.strftime(\"%H:%M\")}，跳过价格检查')
" >> "$LOG" 2>&1

echo "[$(date '+%H:%M:%S')] === 监控完成 ===" >> "$LOG"
