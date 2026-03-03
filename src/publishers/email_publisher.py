"""
EmailPublisher - 透過 SMTP 發送 Email 摘要
支援 Mock 模式：SMTP_USER 未設定時只記錄 log
"""

import os
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import Dict

from .base_publisher import BasePublisher, PublishResult, REPO_URL, STAR_FOOTER_TEXT

logger = logging.getLogger(__name__)


class EmailPublisher(BasePublisher):
    """透過 SMTP 發送 Email 摘要"""

    async def publish(self, articles: list, config: Dict) -> PublishResult:
        """透過 SMTP 發送 Email（支援 Mock 模式）"""
        cfg = self._resolve_config(config)

        smtp_server = cfg.get("smtp_server", os.environ.get("SMTP_SERVER", ""))
        smtp_port = int(cfg.get("smtp_port", os.environ.get("SMTP_PORT", "587")))
        username = cfg.get("username", os.environ.get("SMTP_USER", ""))
        password = cfg.get("password", os.environ.get("SMTP_PASSWORD", ""))
        from_addr = cfg.get("from_address", os.environ.get("SMTP_USER", ""))
        from_name = cfg.get("from_name", os.environ.get("SMTP_FROM_NAME", "Digest Agent"))
        to_addr = cfg.get("to_address", os.environ.get("EMAIL_TO", ""))

        # Mock 模式：SMTP_USER 未設定或以 test- 開頭
        if not username or username.startswith("test-"):
            logger.info(
                "[MOCK] Email: Would send %d articles to %s (from %s via %s:%s)",
                len(articles), to_addr or "(no recipient)", from_addr or "(no sender)",
                smtp_server or "(no server)", smtp_port,
            )
            return PublishResult(channel="email", success=True, articles_sent=len(articles))

        resolved = {
            "smtp_server": smtp_server, "smtp_port": smtp_port,
            "from_address": from_addr, "to_address": to_addr,
        }
        if not self.validate_config(resolved):
            return PublishResult(
                channel="email", success=False,
                error="Invalid email configuration: missing smtp_server, smtp_port, from_address, or to_address",
            )

        try:
            html_body = self._format_html(articles)
            msg = MIMEMultipart("alternative")
            date_str = datetime.now().strftime("%Y/%m/%d")
            msg["Subject"] = f"[Digest] {len(articles)} 篇 AI 新聞摘要 - {date_str}"
            msg["From"] = f"{from_name} <{from_addr}>"

            to_addresses = [to_addr] if isinstance(to_addr, str) else to_addr
            msg["To"] = ", ".join(to_addresses)

            msg.attach(MIMEText(html_body, "html", "utf-8"))

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(username, password)
                server.sendmail(from_addr, to_addresses, msg.as_string())

            logger.info("[Email] Sent %d articles to %s", len(articles), to_addr)
            return PublishResult(channel="email", success=True, articles_sent=len(articles))

        except Exception as e:
            logger.error("[Email] Failed: %s", e)
            return PublishResult(channel="email", success=False, error=str(e))

    def validate_config(self, config: Dict) -> bool:
        """驗證 Email 配置"""
        required = ["smtp_server", "smtp_port", "from_address", "to_address"]
        return all(config.get(key) for key in required)

    def _format_html(self, articles: list) -> str:
        """格式化文章為 HTML email"""
        date_str = datetime.now().strftime("%Y年%m月%d日")
        article_count = len(articles)

        articles_html = ""
        for article in articles:
            title = article.get("title", "Untitled")
            summary = article.get("summary", "No summary available")
            url = article.get("url", "#")
            source = article.get("source", "Unknown")
            tags = article.get("tags", [])
            tags_html = " ".join(
                f'<span style="background:#e8f4f8;color:#1a73e8;padding:2px 8px;'
                f'border-radius:12px;font-size:11px;margin-right:4px;">{t}</span>'
                for t in tags
            ) if tags else ""

            articles_html += f"""
            <div style="margin-bottom:24px;padding:16px;border-left:4px solid #1a73e8;
                        background:#fafafa;border-radius:0 8px 8px 0;">
                <h2 style="margin:0 0 8px 0;font-size:16px;">
                    <a href="{url}" style="color:#1a73e8;text-decoration:none;">{title}</a>
                </h2>
                <p style="color:#666;font-size:12px;margin:0 0 8px 0;">Source: {source}</p>
                {f'<p style="margin:0 0 8px 0;">{tags_html}</p>' if tags_html else ''}
                <p style="color:#333;font-size:14px;line-height:1.6;margin:0;">{summary}</p>
            </div>
            """

        return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
             max-width:600px;margin:0 auto;padding:20px;color:#333;">
    <div style="background:linear-gradient(135deg,#1a73e8,#34a853);padding:24px;
                border-radius:12px;color:white;margin-bottom:24px;">
        <h1 style="margin:0;font-size:24px;">Daily Digest</h1>
        <p style="margin:8px 0 0 0;opacity:0.9;">{date_str} | {article_count} 篇文章</p>
    </div>
    {articles_html}
    <div style="text-align:center;padding:16px;color:#999;font-size:12px;border-top:1px solid #eee;">
        Powered by <a href="{REPO_URL}" style="color:#1a73e8;">Digest Agent</a> - JimmyLiao
        &nbsp;·&nbsp; ⭐ <a href="{REPO_URL}" style="color:#1a73e8;">Star on GitHub</a>
    </div>
</body>
</html>"""
