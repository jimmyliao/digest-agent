"""
BasePublisher - 發佈渠道抽象基底類別
定義所有 Publisher 共用的介面與資料結構
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PublishResult:
    """單一渠道發佈結果"""
    channel: str
    success: bool
    articles_sent: int = 0
    error: Optional[str] = None
    retry_count: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class MultiPublishResult:
    """多渠道發佈彙總結果"""
    results: List[PublishResult] = field(default_factory=list)
    total_success: int = 0
    total_failed: int = 0

    def add_result(self, result: PublishResult):
        self.results.append(result)
        if result.success:
            self.total_success += 1
        else:
            self.total_failed += 1


class BasePublisher(ABC):
    """發佈渠道抽象基底類別"""

    MAX_RETRIES = 3

    def __init__(self, config: Dict):
        self.config = config

    @abstractmethod
    async def publish(self, articles: list, config: Dict) -> PublishResult:
        """發佈文章到此渠道"""
        pass

    @abstractmethod
    def validate_config(self, config: Dict) -> bool:
        """驗證渠道配置是否完整"""
        pass

    def _resolve_config(self, config: Dict) -> Dict:
        """合併傳入 config 與 self.config，傳入優先"""
        merged = {**self.config, **config}
        return merged

    async def publish_with_retry(self, articles: list, config: Dict) -> PublishResult:
        """帶重試邏輯的發佈（exponential backoff）"""
        import asyncio

        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                result = await self.publish(articles, config)
                result.retry_count = attempt
                if result.success:
                    return result
                last_error = result.error
            except Exception as e:
                last_error = str(e)

            if attempt < self.MAX_RETRIES - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(
                    "[%s] Attempt %d failed: %s. Retrying in %ds...",
                    self.__class__.__name__, attempt + 1, last_error, wait_time,
                )
                await asyncio.sleep(wait_time)

        return PublishResult(
            channel=self.__class__.__name__,
            success=False,
            articles_sent=0,
            error=f"Failed after {self.MAX_RETRIES} retries: {last_error}",
            retry_count=self.MAX_RETRIES,
        )
