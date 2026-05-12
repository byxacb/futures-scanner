"""通知模块 - 把简报/告警推送到手机

支持的通道（可同时启用多个）：
- Server酱（微信公众号推送）—— sct.ftqq.com，国内首选
- Bark（iOS 原生推送）—— 开源，bark.day.app
- 邮件（SMTP）—— Gmail / QQ / 163 / 网易 通用

配置全部在 tools/.env，绝不硬编码。

接口：
- notify(title, content, level="info"): 主入口，自动调所有已启用通道
- level: info / warn / urgent（决定 Bark 通知声音和振动）

调用方：
- briefing/morning.py: 每日盘前简报推送
- briefing/evening.py: 每日盘后复盘推送
- monitor/live_watch.py: 实时止损/突破告警
"""

from __future__ import annotations

import json
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


def _load_env():
    """加载 tools/.env（.env 始终覆盖 shell）"""
    env_file = Path(__file__).parent.parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()


_load_env()


# ============================================================
# Server酱（推荐）
# ============================================================
def send_serverchan(title: str, content: str) -> bool:
    """通过 Server酱 推送到微信公众号。
    免费版每日 5 条；付费 ¥0.6/天无限。
    注册：sct.ftqq.com，微信扫码登录后拿 SendKey。
    """
    key = os.getenv("SERVERCHAN_SENDKEY")
    if not key:
        return False
    url = f"https://sctapi.ftqq.com/{key}.send"
    try:
        with httpx.Client(timeout=10) as c:
            r = c.post(url, data={"title": title[:64], "desp": content[:32000]})
            ok = r.json().get("code") == 0
            if not ok:
                logger.warning("Server酱 推送失败: %s", r.text[:200])
            return ok
    except Exception as e:
        logger.error("Server酱 异常: %s", e)
        return False


# ============================================================
# Bark（iOS 原生推送）
# ============================================================
def send_bark(title: str, content: str, level: str = "info") -> bool:
    """通过 Bark 推送到 iPhone（开源 iOS app）。
    安装：App Store 搜 Bark → 进 app 复制 URL。
    URL 形如 https://api.day.app/abc123xyz/
    """
    bark_url = os.getenv("BARK_URL", "").rstrip("/")
    if not bark_url:
        return False

    # level 决定声音
    sound_map = {"info": "minuet", "warn": "alarm", "urgent": "anticipate"}

    # Bark GET 方式更可靠：URL/标题/内容
    from urllib.parse import quote
    title_enc = quote(title, safe="")
    content_enc = quote(content[:500], safe="")
    sound = sound_map.get(level, "minuet")

    url = f"{bark_url}/{title_enc}/{content_enc}?sound={sound}&group=期货比赛&isArchive=1"
    if level == "urgent":
        url += "&level=timeSensitive"

    try:
        with httpx.Client(timeout=10, follow_redirects=True) as c:
            r = c.get(url)
            ok = r.json().get("code") == 200
            if not ok:
                logger.warning("Bark 推送失败: %s", r.text[:200])
            return ok
    except Exception as e:
        logger.error("Bark 异常: %s", e)
        return False


# ============================================================
# 邮件（SMTP）
# ============================================================
def send_email(title: str, content: str) -> bool:
    """通过 SMTP 发邮件。
    支持 Gmail（需应用专用密码）/ QQ邮箱 / 163邮箱 / Outlook 等
    """
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "465"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    to = os.getenv("SMTP_TO", user)
    sender_name = os.getenv("SMTP_SENDER_NAME", "期货机器人")

    if not all([host, user, password, to]):
        return False

    msg = MIMEText(content, "plain", "utf-8")
    msg["Subject"] = title
    msg["From"] = formataddr((sender_name, user))
    msg["To"] = to

    try:
        if port == 465:
            srv = smtplib.SMTP_SSL(host, port, timeout=15)
        else:
            srv = smtplib.SMTP(host, port, timeout=15)
            srv.starttls()
        srv.login(user, password)
        srv.sendmail(user, [to], msg.as_string())
        srv.quit()
        return True
    except Exception as e:
        logger.error("邮件发送失败: %s", e)
        return False


# ============================================================
# 主入口
# ============================================================
def notify(title: str, content: str, level: str = "info") -> dict:
    """同时通过所有已配置通道推送。

    Args:
        title: 简短标题（<64 字）
        content: 内容（支持 markdown，Server酱 会自动渲染）
        level: info / warn / urgent

    Returns:
        {channel: success}
    """
    results = {}
    if os.getenv("SERVERCHAN_SENDKEY"):
        results["serverchan"] = send_serverchan(title, content)
    if os.getenv("BARK_URL"):
        results["bark"] = send_bark(title, content, level)
    if os.getenv("SMTP_HOST"):
        results["email"] = send_email(title, content)

    if not results:
        logger.warning("没有任何通知通道配置——简报只能本地查看")

    for ch, ok in results.items():
        print(f"  📲 {ch}: {'✅' if ok else '❌'}")
    return results


if __name__ == "__main__":
    # 自测
    import sys
    title = sys.argv[1] if len(sys.argv) > 1 else "测试推送"
    content = sys.argv[2] if len(sys.argv) > 2 else "如果你能看到这条消息，说明通知通道工作正常 🎉"
    print(f"正在推送：{title}")
    results = notify(title, content)
    print(f"结果：{results}")
