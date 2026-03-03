"""
LinePublisher - 透過 LINE Messaging API 發送摘要
支援 Mock 模式：CHANNEL_TOKEN 以 "test-" 開頭時只記錄 log
"""

import os
import logging
from typing import Dict

import aiohttp

from .base_publisher import BasePublisher, PublishResult

logger = logging.getLogger(__name__)


class LinePublisher(BasePublisher):
    """透過 LINE Messaging API 發送摘要"""

    LINE_API_BASE = "https://api.line.me/v2/bot/message"

    async def publish(self, articles: list, config: Dict) -> PublishResult:
        """透過 LINE Messaging API 發送 Flex Message（支援 Mock 模式）"""
        cfg = self._resolve_config(config)

        channel_token = cfg.get(
            "channel_access_token",
            os.environ.get("LINE_CHANNEL_TOKEN", ""),
        )
        target_type = cfg.get("target_type", "push")
        to_id = cfg.get("to", os.environ.get("LINE_USER_ID", ""))

        resolved = {"channel_access_token": channel_token, "target_type": target_type, "to": to_id}
        if not self.validate_config(resolved):
            return PublishResult(
                channel="line", success=False,
                error="Invalid LINE configuration: missing channel_access_token or to (for push)",
            )

        # Mock 模式
        if not channel_token or channel_token.startswith("test-"):
            logger.info(
                "[MOCK] LINE: Would send %d articles via %s to %s",
                len(articles), target_type, to_id or "broadcast",
            )
            return PublishResult(channel="line", success=True, articles_sent=len(articles))

        try:
            messages = self._format_flex_message(articles)

            if target_type == "broadcast":
                api_url = f"{self.LINE_API_BASE}/broadcast"
                payload = {"messages": messages}
            else:
                api_url = f"{self.LINE_API_BASE}/push"
                payload = {"to": to_id, "messages": messages}

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {channel_token}",
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        logger.info("[LINE] Sent %d articles via %s", len(articles), target_type)
                        return PublishResult(
                            channel="line", success=True, articles_sent=len(articles),
                        )
                    else:
                        body = await resp.text()
                        logger.error("[LINE] API error %d: %s", resp.status, body)
                        return PublishResult(
                            channel="line", success=False,
                            error=f"LINE API returned {resp.status}: {body}",
                        )

        except Exception as e:
            logger.error("[LINE] Failed: %s", e)
            return PublishResult(channel="line", success=False, error=str(e))

    def validate_config(self, config: Dict) -> bool:
        """驗證 LINE 配置"""
        if not config.get("channel_access_token"):
            return False
        target_type = config.get("target_type", "push")
        if target_type == "push" and not config.get("to"):
            return False
        return True

    def _format_flex_message(self, articles: list) -> list:
        """格式化文章為 LINE Flex Message（卡片樣式）"""
        body_contents = []
        for article in articles[:10]:
            title = article.get("title", "Untitled")
            summary = article.get("summary", "No summary")
            url = article.get("url", "")
            source = article.get("source", "")
            tags = article.get("tags", [])

            contents = [
                {
                    "type": "text",
                    "text": title,
                    "weight": "bold",
                    "size": "sm",
                    "wrap": True,
                    "color": "#1a73e8",
                },
            ]

            if source:
                contents.append({
                    "type": "text",
                    "text": f"📍 {source}",
                    "size": "xxs",
                    "color": "#999999",
                })

            short_summary = summary[:100] + "..." if len(summary) > 100 else summary
            contents.append({
                "type": "text",
                "text": short_summary,
                "size": "xs",
                "color": "#666666",
                "wrap": True,
            })

            if tags:
                contents.append({
                    "type": "text",
                    "text": "🏷️ " + " ".join(f"#{t}" for t in tags[:5]),
                    "size": "xxs",
                    "color": "#1a73e8",
                })

            box = {
                "type": "box",
                "layout": "vertical",
                "margin": "lg",
                "spacing": "sm",
                "contents": contents,
            }
            if url:
                box["action"] = {"type": "uri", "uri": url, "label": "Read"}

            body_contents.append(box)

            # 分隔線
            body_contents.append({
                "type": "separator",
                "margin": "lg",
                "color": "#eeeeee",
            })

        # 移除最後一條分隔線
        if body_contents and body_contents[-1].get("type") == "separator":
            body_contents.pop()

        flex_message = {
            "type": "flex",
            "altText": f"📰 Daily Digest ({len(articles)} articles)",
            "contents": {
                "type": "bubble",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "backgroundColor": "#1a73e8",
                    "paddingAll": "16px",
                    "contents": [
                        {
                            "type": "text",
                            "text": "📰 Daily Digest",
                            "weight": "bold",
                            "size": "lg",
                            "color": "#ffffff",
                        },
                        {
                            "type": "text",
                            "text": f"{len(articles)} articles",
                            "size": "xs",
                            "color": "#ffffffcc",
                        },
                    ],
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": body_contents,
                },
            },
        }

        return [flex_message]
