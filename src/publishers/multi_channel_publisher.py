"""
MultiChannelPublisher - 多渠道發佈協調器
負責將文章同時發佈到多個渠道，支援排程與錯誤隔離
"""

import asyncio
from typing import List, Dict, Optional
from datetime import datetime

from .base_publisher import BasePublisher, PublishResult, MultiPublishResult


class MultiChannelPublisher:
    """多渠道發佈協調器

    特性:
    - 並行發佈到多個渠道
    - 單一渠道失敗不影響其他渠道
    - 支援排程發佈（schedule_at）
    - 自動重試（透過 BasePublisher.publish_with_retry）
    """

    def __init__(self):
        self.publishers: Dict[str, BasePublisher] = {}

    def register_publisher(self, channel_id: str, publisher: BasePublisher):
        """註冊發佈渠道

        Args:
            channel_id: 渠道識別碼（如 "email", "telegram"）
            publisher: BasePublisher 實例
        """
        self.publishers[channel_id] = publisher

    def unregister_publisher(self, channel_id: str):
        """移除發佈渠道"""
        self.publishers.pop(channel_id, None)

    async def publish(
        self,
        articles: list,
        channels: List[str],
        channel_configs: Optional[Dict[str, Dict]] = None,
        schedule_at: Optional[datetime] = None,
        use_retry: bool = True,
    ) -> MultiPublishResult:
        """發佈文章到多個渠道

        Args:
            articles: 要發佈的文章列表
            channels: 目標渠道 ID 列表
            channel_configs: 各渠道的額外配置（選填）
            schedule_at: 排程發佈時間（選填，None 表示立即發佈）
            use_retry: 是否啟用重試機制

        Returns:
            MultiPublishResult 多渠道彙總結果
        """
        if schedule_at:
            delay = (schedule_at - datetime.now()).total_seconds()
            if delay > 0:
                await asyncio.sleep(delay)

        result = MultiPublishResult()
        configs = channel_configs or {}

        tasks = []
        for channel_id in channels:
            publisher = self.publishers.get(channel_id)
            if not publisher:
                result.add_result(PublishResult(
                    channel=channel_id,
                    success=False,
                    error=f"Publisher '{channel_id}' not registered",
                ))
                continue

            config = configs.get(channel_id, publisher.config)

            if use_retry:
                tasks.append(self._publish_channel(publisher, channel_id, articles, config))
            else:
                tasks.append(self._publish_channel_no_retry(publisher, channel_id, articles, config))

        if tasks:
            channel_results = await asyncio.gather(*tasks, return_exceptions=True)
            for ch_result in channel_results:
                if isinstance(ch_result, Exception):
                    result.add_result(PublishResult(
                        channel="unknown",
                        success=False,
                        error=str(ch_result),
                    ))
                else:
                    result.add_result(ch_result)

        return result

    async def _publish_channel(
        self, publisher: BasePublisher, channel_id: str, articles: list, config: Dict
    ) -> PublishResult:
        """發佈到單一渠道（帶重試）"""
        try:
            return await publisher.publish_with_retry(articles, config)
        except Exception as e:
            return PublishResult(
                channel=channel_id,
                success=False,
                error=str(e),
            )

    async def _publish_channel_no_retry(
        self, publisher: BasePublisher, channel_id: str, articles: list, config: Dict
    ) -> PublishResult:
        """發佈到單一渠道（不重試）"""
        try:
            return await publisher.publish(articles, config)
        except Exception as e:
            return PublishResult(
                channel=channel_id,
                success=False,
                error=str(e),
            )

    def list_channels(self) -> List[str]:
        """列出所有已註冊的渠道"""
        return list(self.publishers.keys())

    def get_publisher(self, channel_id: str) -> Optional[BasePublisher]:
        """取得指定渠道的 Publisher"""
        return self.publishers.get(channel_id)
