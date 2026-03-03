"""
Digest Agent - Publishers Module (Backend)
多渠道發佈系統：支援 Email, Telegram, LINE, Discord
"""

from .base_publisher import BasePublisher, PublishResult, MultiPublishResult
from .email_publisher import EmailPublisher
from .telegram_publisher import TelegramPublisher
from .line_publisher import LinePublisher
from .discord_publisher import DiscordPublisher
from .multi_channel_publisher import MultiChannelPublisher

__all__ = [
    "BasePublisher",
    "PublishResult",
    "MultiPublishResult",
    "EmailPublisher",
    "TelegramPublisher",
    "LinePublisher",
    "DiscordPublisher",
    "MultiChannelPublisher",
]
