"""
DiscordPublisher - 透過 Discord Webhook 發送摘要
支援 Mock 模式：WEBHOOK_URL 未設定或以 "test-" 開頭時只記錄 log
"""

import os
import logging
from typing import Dict
from datetime import datetime

import aiohttp

from .base_publisher import BasePublisher, PublishResult

logger = logging.getLogger(__name__)


class DiscordPublisher(BasePublisher):
    """透過 Discord Webhook 發送摘要"""

    async def publish(self, articles: list, config: Dict) -> PublishResult:
        """透過 Discord Webhook 發送 embed 訊息（支援 Mock 模式）"""
        cfg = self._resolve_config(config)

        webhook_url = cfg.get("webhook_url", os.environ.get("DISCORD_WEBHOOK_URL", ""))
        username = cfg.get("username", "Digest Bot")
        avatar_url = cfg.get("avatar_url", "")

        resolved = {"webhook_url": webhook_url}
        if not self.validate_config(resolved):
            return PublishResult(
                channel="discord", success=False,
                error="Invalid Discord configuration: missing or invalid webhook_url",
            )

        # Mock 模式
        if webhook_url.startswith("test-") or "example.com" in webhook_url:
            logger.info(
                "[MOCK] Discord: Would send %d articles via webhook", len(articles),
            )
            return PublishResult(channel="discord", success=True, articles_sent=len(articles))

        try:
            embeds = self._format_embeds(articles)
            payload = {
                "username": username,
                "content": f"**📰 Daily Digest** - {len(articles)} articles",
                "embeds": embeds[:10],
            }
            if avatar_url:
                payload["avatar_url"] = avatar_url

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as resp:
                    if resp.status in (200, 204):
                        logger.info("[Discord] Sent %d articles via webhook", len(articles))
                        return PublishResult(
                            channel="discord", success=True, articles_sent=len(articles),
                        )
                    else:
                        body = await resp.text()
                        logger.error("[Discord] Webhook error %d: %s", resp.status, body)
                        return PublishResult(
                            channel="discord", success=False,
                            error=f"Discord webhook returned {resp.status}: {body}",
                        )

        except Exception as e:
            logger.error("[Discord] Failed: %s", e)
            return PublishResult(channel="discord", success=False, error=str(e))

    def validate_config(self, config: Dict) -> bool:
        """驗證 Discord 配置"""
        webhook_url = config.get("webhook_url", "")
        return bool(webhook_url)

    def _format_embeds(self, articles: list) -> list:
        """格式化文章為 Discord Embeds"""
        embeds = []
        for article in articles[:10]:
            title = article.get("title", "Untitled")
            summary = article.get("summary", "No summary available")
            url = article.get("url", "")
            source = article.get("source", "Unknown")
            tags = article.get("tags", [])

            description = summary[:4000]
            if tags:
                tags_str = " | ".join(f"`{t}`" for t in tags)
                description += f"\n\n🏷️ {tags_str}"

            embed = {
                "title": title[:256],
                "description": description[:4096],
                "color": 1738215,  # #1a73e8 as decimal
                "footer": {"text": f"Source: {source}"},
                "timestamp": datetime.now().isoformat(),
            }

            if url:
                embed["url"] = url

            embeds.append(embed)

        return embeds
