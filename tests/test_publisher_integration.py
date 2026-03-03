"""
Publisher ↔ Orchestration 整合測試
驗證 orchestrator → MultiChannelPublisher → 各渠道 publisher pipeline 正確運作
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import patch

# Ensure backend src is importable (project root must come first)
_project_root = os.path.join(os.path.dirname(__file__), "..")
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
# Remove digest-agent/ from path if present to avoid src conflicts
_da_path = os.path.join(_project_root, "digest-agent")
if _da_path in sys.path:
    sys.path.remove(_da_path)

from src.orchestrator import DigestOrchestrator, build_multi_publisher
from src.publishers.base_publisher import PublishResult as ChannelPublishResult
from src.publishers.multi_channel_publisher import MultiChannelPublisher
from src.publishers.email_publisher import EmailPublisher
from src.publishers.telegram_publisher import TelegramPublisher
from src.publishers.discord_publisher import DiscordPublisher
from src.publishers.line_publisher import LinePublisher


SAMPLE_ARTICLES = [
    {
        "title": "GPT-5 發布：AI 能力再創新高",
        "summary": "OpenAI 宣布最新模型 GPT-5，在多項基準測試中大幅超越前代。",
        "url": "https://example.com/gpt5",
        "source": "TechCrunch",
        "tags": ["AI", "GPT", "OpenAI"],
    },
    {
        "title": "台灣半導體產業展望",
        "summary": "2026年全球半導體需求持續成長，台灣廠商受惠。",
        "url": "https://example.com/semiconductor",
        "source": "工商時報",
        "tags": ["semiconductor", "taiwan", "TSMC"],
    },
    {
        "title": "Kubernetes 2.0 Released",
        "summary": "Major release brings simplified networking and improved security.",
        "url": "https://example.com/k8s",
        "source": "CNCF Blog",
        "tags": ["kubernetes", "cloud-native", "devops"],
    },
]

# Mock environment for all publishers to use mock mode
MOCK_ENV = {
    "SMTP_SERVER": "smtp.mock.test",
    "SMTP_PORT": "587",
    "SMTP_USER": "test-mock@test.com",
    "SMTP_PASSWORD": "",
    "EMAIL_TO": "to@test.com",
    "TELEGRAM_BOT_TOKEN": "test-mock-token",
    "TELEGRAM_CHAT_ID": "-100999",
    "LINE_CHANNEL_TOKEN": "test-mock-line-token",
    "LINE_USER_ID": "Utest123",
    "DISCORD_WEBHOOK_URL": "test-mock-webhook",
}


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestBuildMultiPublisher(unittest.TestCase):
    """Test that build_multi_publisher() creates and registers all channels."""

    @patch.dict(os.environ, MOCK_ENV)
    def test_all_channels_registered(self):
        multi = build_multi_publisher()
        channels = multi.list_channels()
        self.assertIn("email", channels)
        self.assertIn("telegram", channels)
        self.assertIn("line", channels)
        self.assertIn("discord", channels)
        self.assertEqual(len(channels), 4)

    @patch.dict(os.environ, MOCK_ENV)
    def test_publishers_are_correct_types(self):
        multi = build_multi_publisher()
        self.assertIsInstance(multi.get_publisher("email"), EmailPublisher)
        self.assertIsInstance(multi.get_publisher("telegram"), TelegramPublisher)
        self.assertIsInstance(multi.get_publisher("line"), LinePublisher)
        self.assertIsInstance(multi.get_publisher("discord"), DiscordPublisher)


class TestOrchestratorPublishPipeline(unittest.TestCase):
    """Test DigestOrchestrator.run_publish_pipeline() with mock mode."""

    @patch.dict(os.environ, MOCK_ENV)
    def test_publish_all_channels_mock(self):
        """全渠道 mock 模式發佈成功"""
        orchestrator = DigestOrchestrator()
        result = run_async(
            orchestrator.run_publish_pipeline(
                articles=SAMPLE_ARTICLES,
                channels=["email", "telegram", "line", "discord"],
            )
        )
        self.assertTrue(result.success)
        self.assertEqual(result.published_count, 4)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(result.channels, ["email", "telegram", "line", "discord"])

    @patch.dict(os.environ, MOCK_ENV)
    def test_publish_subset_channels(self):
        """只發佈到部分渠道"""
        orchestrator = DigestOrchestrator()
        result = run_async(
            orchestrator.run_publish_pipeline(
                articles=SAMPLE_ARTICLES,
                channels=["email", "telegram"],
            )
        )
        self.assertTrue(result.success)
        self.assertEqual(result.published_count, 2)

    @patch.dict(os.environ, MOCK_ENV)
    def test_publish_empty_articles(self):
        """空文章列表 → 直接成功返回"""
        orchestrator = DigestOrchestrator()
        result = run_async(
            orchestrator.run_publish_pipeline(articles=[], channels=["email"])
        )
        self.assertTrue(result.success)
        self.assertEqual(result.published_count, 0)

    @patch.dict(os.environ, MOCK_ENV)
    def test_publish_none_articles(self):
        """None 文章 → 直接成功返回"""
        orchestrator = DigestOrchestrator()
        result = run_async(
            orchestrator.run_publish_pipeline(articles=None, channels=["email"])
        )
        self.assertTrue(result.success)

    @patch.dict(os.environ, MOCK_ENV)
    def test_publish_default_all_channels(self):
        """不指定 channels → 使用所有已註冊渠道"""
        orchestrator = DigestOrchestrator()
        result = run_async(
            orchestrator.run_publish_pipeline(articles=SAMPLE_ARTICLES)
        )
        self.assertTrue(result.success)
        self.assertEqual(result.published_count, 4)


class TestSingleChannelFailureIsolation(unittest.TestCase):
    """Test that a single channel failure does not block others."""

    @patch.dict(os.environ, MOCK_ENV)
    def test_one_channel_fails_others_succeed(self):
        """一個渠道失敗，其他渠道仍然成功"""
        orchestrator = DigestOrchestrator()

        # Replace email publisher with one that has real-mode config (will fail)
        orchestrator.multi_publisher.register_publisher(
            "email",
            EmailPublisher(config={
                "username": "real-user@gmail.com",
                "password": "bad-password",
                # Missing smtp_server → validation fails → PublishResult(success=False)
            }),
        )

        result = run_async(
            orchestrator.run_publish_pipeline(
                articles=SAMPLE_ARTICLES,
                channels=["email", "telegram", "line", "discord"],
            )
        )

        # Email fails, other 3 succeed
        self.assertFalse(result.success)  # Overall has failures
        self.assertEqual(result.published_count, 3)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("Email", result.errors[0])

    @patch.dict(os.environ, MOCK_ENV)
    def test_unregistered_channel_fails_gracefully(self):
        """未註冊的渠道失敗不影響其他渠道"""
        orchestrator = DigestOrchestrator()
        result = run_async(
            orchestrator.run_publish_pipeline(
                articles=SAMPLE_ARTICLES,
                channels=["email", "telegram", "slack"],  # slack 未註冊
            )
        )
        # slack fails, email + telegram succeed
        self.assertEqual(result.published_count, 2)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("slack", result.errors[0])


class TestChannelResults(unittest.TestCase):
    """Test that channel_results provide per-channel detail."""

    @patch.dict(os.environ, MOCK_ENV)
    def test_channel_results_populated(self):
        orchestrator = DigestOrchestrator()
        result = run_async(
            orchestrator.run_publish_pipeline(
                articles=SAMPLE_ARTICLES,
                channels=["email", "telegram"],
            )
        )
        self.assertIsNotNone(result.channel_results)
        self.assertEqual(len(result.channel_results.results), 2)
        for cr in result.channel_results.results:
            self.assertTrue(cr.success)
            self.assertEqual(cr.articles_sent, 3)

    @patch.dict(os.environ, MOCK_ENV)
    def test_channel_results_per_channel_article_count(self):
        """驗證每個渠道的 articles_sent 數量正確"""
        orchestrator = DigestOrchestrator()
        single_article = [SAMPLE_ARTICLES[0]]
        result = run_async(
            orchestrator.run_publish_pipeline(
                articles=single_article,
                channels=["discord"],
            )
        )
        self.assertEqual(result.channel_results.results[0].articles_sent, 1)


class TestFullPipeline(unittest.TestCase):
    """Test the full pipeline orchestration (fetch → summarize → publish)."""

    @patch.dict(os.environ, MOCK_ENV)
    def test_full_pipeline_runs_all_stages(self):
        """完整 pipeline 執行所有階段（fetch/summarize 仍為 stub）"""
        orchestrator = DigestOrchestrator()
        result = run_async(orchestrator.run_full_pipeline())

        self.assertTrue(result.success)
        self.assertIsNotNone(result.fetch)
        self.assertIsNotNone(result.summarize)
        self.assertIsNotNone(result.publish)
        # publish has no articles (fetch is still stub) so it succeeds with 0
        self.assertTrue(result.publish.success)


if __name__ == "__main__":
    unittest.main()
