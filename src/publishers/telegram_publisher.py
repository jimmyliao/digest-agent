"""
TelegramPublisher - 透過 Telegram Bot API 發送摘要
支援 Mock 模式：BOT_TOKEN 以 "test-" 開頭時只記錄 log
"""

import os
import logging
from typing import Dict, List

import aiohttp

from .base_publisher import BasePublisher, PublishResult, STAR_FOOTER_TEXT

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
            full_message = self._format_message(articles)
            # Telegram 訊息上限約 4096 字符，若過長需拆分
            chunks = self._split_message(full_message, 4000)

            sent_chunks = 0
            api_url = f"{self.TELEGRAM_API_BASE.format(token=bot_token)}/sendMessage"

            async with aiohttp.ClientSession() as session:
                for chunk in chunks:
                    payload = {
                        "chat_id": chat_id,
                        "text": chunk,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": cfg.get("disable_preview", False),
                    }
                    async with session.post(api_url, json=payload) as resp:
                        if resp.status == 200:
                            sent_chunks += 1
                        else:
                            body = await resp.text()
                            logger.error("[Telegram] API error: %s", body)
                            return PublishResult(channel="telegram", success=False, error=f"API Error: {body}")

            logger.info("[Telegram] Sent %d chunks for %d articles to chat %s", sent_chunks, len(articles), chat_id)
            return PublishResult(channel="telegram", success=True, articles_sent=len(articles))

        except Exception as e:
            logger.error("[Telegram] Failed: %s", e)
            return PublishResult(channel="telegram", success=False, error=str(e))

    def validate_config(self, config: Dict) -> bool:
        """驗證 Telegram 配置"""
        return bool(config.get("bot_token")) and bool(config.get("chat_id"))

    def _format_message(self, articles: list) -> str:
        """格式化多篇文章為單一 Telegram HTML 訊息"""
        date_str = datetime.now().strftime("%Y/%m/%d")
        header = f"<b>📰 AI 新聞摘要 ({date_str})</b>\n本日共計 {len(articles)} 篇文章\n"
        
        parts = [header]
        for i, article in enumerate(articles, 1):
            parts.append(f"\n{i}. " + self._format_single_article(article))
        
        parts.append(f"\n\n<i>{STAR_FOOTER_TEXT}</i>")
        return "\n".join(parts)

    def _format_single_article(self, article: dict) -> str:
        """格式化單篇文章為 Telegram HTML 訊息片段"""
        title = article.get("title", "Untitled")
        summary = article.get("summary", "")
        url = article.get("url", "")
        source = article.get("source", "")
        tags = article.get("tags", [])

        title_html = f"<b>{title}</b>"
        if url:
            title_html = f'<a href="{url}">{title_html}</a>'
            
        parts = [title_html]
        if source:
            parts[0] += f"  <i>({source})</i>"

        if summary:
            # 摘要在合併模式下不宜過長
            short = summary[:300] + "..." if len(summary) > 300 else summary
            parts.append(f"{short}")

        if tags:
            tags_str = " ".join(f"#{t}" for t in tags)
            parts.append(f"🏷️ {tags_str}")

        return "\n".join(parts)

    def _split_message(self, text: str, limit: int) -> List[str]:
        """按長度拆分訊息，儘量在換行處拆分"""
        if len(text) <= limit:
            return [text]
        
        chunks = []
        while text:
            if len(text) <= limit:
                chunks.append(text)
                break
            
            # 尋找最近的換行符號
            split_at = text.rfind('\n', 0, limit)
            if split_at == -1:
                split_at = limit
            
            chunks.append(text[:split_at])
            text = text[split_at:].lstrip()
        return chunks
