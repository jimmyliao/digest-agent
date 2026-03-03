"""
TelegramPublisher - 透過 Telegram Bot API 發送摘要
支援 Mock 模式：BOT_TOKEN 以 "test-" 開頭時只記錄 log
"""

import os
import logging
from typing import Dict

import aiohttp

from .base_publisher import BasePublisher, PublishResult

logger = logging.getLogger(__name__)


class TelegramPublisher(BasePublisher):
    """透過 Telegram Bot API 發送摘要"""

    TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}"

    async def publish(self, articles: list, config: Dict) -> PublishResult:
        """透過 Telegram Bot 發送訊息（支援 Mock 模式）"""
        cfg = self._resolve_config(config)

        bot_token = cfg.get("bot_token", os.environ.get("TELEGRAM_BOT_TOKEN", ""))
        chat_id = cfg.get("chat_id", os.environ.get("TELEGRAM_CHAT_ID", ""))

        resolved = {"bot_token": bot_token, "chat_id": chat_id}
        if not self.validate_config(resolved):
            return PublishResult(
                channel="telegram", success=False,
                error="Invalid Telegram configuration: missing bot_token or chat_id",
            )

        # Mock 模式
        if not bot_token or bot_token.startswith("test-"):
            message = self._format_message(articles)
            logger.info("[MOCK] Telegram: Would send to chat %s:\n%s", chat_id, message[:200])
            return PublishResult(channel="telegram", success=True, articles_sent=len(articles))

        try:
            sent = 0
            api_url = f"{self.TELEGRAM_API_BASE.format(token=bot_token)}/sendMessage"

            async with aiohttp.ClientSession() as session:
                for article in articles:
                    text = self._format_single_article(article)
                    payload = {
                        "chat_id": chat_id,
                        "text": text,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": cfg.get("disable_preview", False),
                    }

                    async with session.post(api_url, json=payload) as resp:
                        if resp.status == 200:
                            sent += 1
                        else:
                            body = await resp.text()
                            logger.warning("[Telegram] API error for article: %s", body)

            logger.info("[Telegram] Sent %d/%d articles to chat %s", sent, len(articles), chat_id)
            return PublishResult(channel="telegram", success=True, articles_sent=sent)

        except Exception as e:
            logger.error("[Telegram] Failed: %s", e)
            return PublishResult(channel="telegram", success=False, error=str(e))

    def validate_config(self, config: Dict) -> bool:
        """驗證 Telegram 配置"""
        return bool(config.get("bot_token")) and bool(config.get("chat_id"))

    def _format_message(self, articles: list) -> str:
        """格式化多篇文章為單一 Telegram 訊息（用於 mock log）"""
        parts = [f"<b>📰 Daily Digest</b> ({len(articles)} articles)\n"]
        for i, article in enumerate(articles, 1):
            parts.append(self._format_single_article(article))
        return "\n---\n".join(parts)

    def _format_single_article(self, article: dict) -> str:
        """格式化單篇文章為 Telegram HTML 訊息"""
        title = article.get("title", "Untitled")
        summary = article.get("summary", "")
        url = article.get("url", "")
        source = article.get("source", "")
        tags = article.get("tags", [])

        parts = [f"<b>{title}</b>"]
        if source:
            parts[0] += f"  <i>({source})</i>"

        if summary:
            short = summary[:500] + "..." if len(summary) > 500 else summary
            parts.append(f"\n{short}")

        if tags:
            tags_str = " ".join(f"#{t}" for t in tags)
            parts.append(f"\n🏷️ {tags_str}")

        if url:
            parts.append(f'\n🔗 <a href="{url}">閱讀原文</a>')

        return "\n".join(parts)
