"""
Publisher 模組測試
測試所有渠道的 validate_config、mock 模式、multi-channel 並行發佈
"""

import asyncio
import unittest
from unittest.mock import patch, AsyncMock, MagicMock
import sys
import os

# 確保可以 import src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "digest-agent"))

from src.publishers.base_publisher import PublishResult, MultiPublishResult
from src.publishers.email_publisher import EmailPublisher
from src.publishers.telegram_publisher import TelegramPublisher
from src.publishers.line_publisher import LinePublisher
from src.publishers.discord_publisher import DiscordPublisher
from src.publishers.multi_channel_publisher import MultiChannelPublisher


# --- 測試用共用資料 ---

SAMPLE_ARTICLES = [
    {
        "title": "AI 突破：新模型超越人類表現",
        "summary": "最新研究顯示 AI 模型在多項基準測試中超越人類水準。",
        "url": "https://example.com/article-1",
        "source": "TechNews",
        "tags": ["AI", "LLM", "breakthrough"],
    },
    {
        "title": "量子計算新進展",
        "summary": "Google 宣布量子計算取得重大突破。",
        "url": "https://example.com/article-2",
        "source": "SciDaily",
        "tags": ["quantum", "google"],
    },
]


def run_async(coro):
    """Helper to run async tests"""
    return asyncio.get_event_loop().run_until_complete(coro)


# ============================================================
# EmailPublisher Tests
# ============================================================

class TestEmailPublisher(unittest.TestCase):

    def setUp(self):
        self.publisher = EmailPublisher(config={})

    def test_validate_config_valid(self):
        config = {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "from_address": "test@gmail.com",
            "to_address": "recipient@gmail.com",
        }
        self.assertTrue(self.publisher.validate_config(config))

    def test_validate_config_missing_server(self):
        config = {
            "smtp_port": 587,
            "from_address": "test@gmail.com",
            "to_address": "recipient@gmail.com",
        }
        self.assertFalse(self.publisher.validate_config(config))

    def test_validate_config_missing_to(self):
        config = {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "from_address": "test@gmail.com",
        }
        self.assertFalse(self.publisher.validate_config(config))

    def test_validate_config_empty_values(self):
        config = {
            "smtp_server": "",
            "smtp_port": 587,
            "from_address": "test@gmail.com",
            "to_address": "recipient@gmail.com",
        }
        self.assertFalse(self.publisher.validate_config(config))

    @patch.dict(os.environ, {
        "SMTP_SERVER": "smtp.test.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "test-user@test.com",
        "EMAIL_TO": "to@test.com",
    })
    def test_mock_mode_with_test_prefix(self):
        """SMTP_USER 以 test- 開頭時進入 mock 模式"""
        result = run_async(self.publisher.publish(SAMPLE_ARTICLES, {}))
        self.assertTrue(result.success)
        self.assertEqual(result.channel, "email")
        self.assertEqual(result.articles_sent, 2)

    @patch.dict(os.environ, {
        "SMTP_SERVER": "smtp.test.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "",
        "EMAIL_TO": "to@test.com",
    })
    def test_mock_mode_without_username(self):
        """SMTP_USER 未設定時進入 mock 模式"""
        result = run_async(self.publisher.publish(SAMPLE_ARTICLES, {}))
        self.assertTrue(result.success)
        self.assertEqual(result.articles_sent, 2)

    def test_empty_config_enters_mock_mode(self):
        """空配置 → 無 username → 進入 mock 模式"""
        result = run_async(self.publisher.publish(SAMPLE_ARTICLES, {}))
        self.assertTrue(result.success)

    def test_real_mode_invalid_config_returns_failure(self):
        """真實模式下缺少必要配置回傳失敗"""
        config = {"username": "real-user@gmail.com", "password": "pass"}
        result = run_async(self.publisher.publish(SAMPLE_ARTICLES, config))
        self.assertFalse(result.success)
        self.assertIn("Invalid", result.error)

    def test_format_html(self):
        html = self.publisher._format_html(SAMPLE_ARTICLES)
        self.assertIn("AI 突破", html)
        self.assertIn("Daily Digest", html)
        self.assertIn("TechNews", html)
        self.assertIn("example.com/article-1", html)

    def test_format_html_with_tags(self):
        html = self.publisher._format_html(SAMPLE_ARTICLES)
        self.assertIn("AI", html)
        self.assertIn("LLM", html)


# ============================================================
# TelegramPublisher Tests
# ============================================================

class TestTelegramPublisher(unittest.TestCase):

    def setUp(self):
        self.publisher = TelegramPublisher(config={})

    def test_validate_config_valid(self):
        config = {"bot_token": "123:ABC", "chat_id": "-100123"}
        self.assertTrue(self.publisher.validate_config(config))

    def test_validate_config_missing_token(self):
        config = {"chat_id": "-100123"}
        self.assertFalse(self.publisher.validate_config(config))

    def test_validate_config_missing_chat_id(self):
        config = {"bot_token": "123:ABC"}
        self.assertFalse(self.publisher.validate_config(config))

    def test_validate_config_empty_token(self):
        config = {"bot_token": "", "chat_id": "-100123"}
        self.assertFalse(self.publisher.validate_config(config))

    @patch.dict(os.environ, {
        "TELEGRAM_BOT_TOKEN": "test-fake-token",
        "TELEGRAM_CHAT_ID": "-100999",
    })
    def test_mock_mode(self):
        """BOT_TOKEN 以 test- 開頭時進入 mock 模式"""
        result = run_async(self.publisher.publish(SAMPLE_ARTICLES, {}))
        self.assertTrue(result.success)
        self.assertEqual(result.channel, "telegram")
        self.assertEqual(result.articles_sent, 2)

    def test_format_single_article(self):
        text = self.publisher._format_single_article(SAMPLE_ARTICLES[0])
        self.assertIn("AI 突破", text)
        self.assertIn("TechNews", text)
        self.assertIn("#AI", text)
        self.assertIn("閱讀原文", text)

    @patch("aiohttp.ClientSession")
    def test_real_mode_sends_per_article(self, mock_session_cls):
        """真實模式：每篇文章發送一則 Telegram 訊息"""
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_post = MagicMock(return_value=mock_resp)

        mock_session = AsyncMock()
        mock_session.post = mock_post
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_session_cls.return_value = mock_session

        config = {"bot_token": "real-token-123:ABC", "chat_id": "-100999"}
        result = run_async(self.publisher.publish(SAMPLE_ARTICLES, config))

        self.assertTrue(result.success)
        self.assertEqual(result.articles_sent, 2)
        self.assertEqual(mock_post.call_count, 2)


# ============================================================
# LinePublisher Tests
# ============================================================

class TestLinePublisher(unittest.TestCase):

    def setUp(self):
        self.publisher = LinePublisher(config={})

    def test_validate_config_push_valid(self):
        config = {"channel_access_token": "token123", "to": "Uabc123"}
        self.assertTrue(self.publisher.validate_config(config))

    def test_validate_config_push_missing_to(self):
        config = {"channel_access_token": "token123", "target_type": "push"}
        self.assertFalse(self.publisher.validate_config(config))

    def test_validate_config_broadcast_no_to(self):
        config = {"channel_access_token": "token123", "target_type": "broadcast"}
        self.assertTrue(self.publisher.validate_config(config))

    def test_validate_config_missing_token(self):
        config = {"to": "Uabc123"}
        self.assertFalse(self.publisher.validate_config(config))

    @patch.dict(os.environ, {
        "LINE_CHANNEL_TOKEN": "test-fake-token",
        "LINE_USER_ID": "Utest123",
    })
    def test_mock_mode(self):
        result = run_async(self.publisher.publish(SAMPLE_ARTICLES, {}))
        self.assertTrue(result.success)
        self.assertEqual(result.channel, "line")
        self.assertEqual(result.articles_sent, 2)

    def test_format_flex_message(self):
        messages = self.publisher._format_flex_message(SAMPLE_ARTICLES)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["type"], "flex")
        self.assertIn("Daily Digest", messages[0]["altText"])
        body = messages[0]["contents"]["body"]["contents"]
        # 2 articles + separators between them
        self.assertTrue(len(body) >= 2)


# ============================================================
# DiscordPublisher Tests
# ============================================================

class TestDiscordPublisher(unittest.TestCase):

    def setUp(self):
        self.publisher = DiscordPublisher(config={})

    def test_validate_config_valid(self):
        config = {"webhook_url": "https://discord.com/api/webhooks/123/abc"}
        self.assertTrue(self.publisher.validate_config(config))

    def test_validate_config_empty_url(self):
        config = {"webhook_url": ""}
        self.assertFalse(self.publisher.validate_config(config))

    def test_validate_config_missing_url(self):
        config = {}
        self.assertFalse(self.publisher.validate_config(config))

    @patch.dict(os.environ, {
        "DISCORD_WEBHOOK_URL": "test-webhook-url",
    })
    def test_mock_mode(self):
        result = run_async(self.publisher.publish(SAMPLE_ARTICLES, {}))
        self.assertTrue(result.success)
        self.assertEqual(result.channel, "discord")
        self.assertEqual(result.articles_sent, 2)

    def test_format_embeds(self):
        embeds = self.publisher._format_embeds(SAMPLE_ARTICLES)
        self.assertEqual(len(embeds), 2)
        self.assertEqual(embeds[0]["title"], "AI 突破：新模型超越人類表現")
        self.assertIn("quantum", embeds[1]["description"])
        self.assertEqual(embeds[0]["footer"]["text"], "Source: TechNews")

    def test_format_embeds_max_10(self):
        many_articles = SAMPLE_ARTICLES * 8  # 16 articles
        embeds = self.publisher._format_embeds(many_articles)
        self.assertEqual(len(embeds), 10)


# ============================================================
# MultiChannelPublisher Tests
# ============================================================

class TestMultiChannelPublisher(unittest.TestCase):

    def setUp(self):
        self.multi = MultiChannelPublisher()

    def test_register_and_list(self):
        pub = EmailPublisher(config={})
        self.multi.register_publisher("email", pub)
        self.assertIn("email", self.multi.list_channels())
        self.assertIs(self.multi.get_publisher("email"), pub)

    def test_unregister(self):
        pub = EmailPublisher(config={})
        self.multi.register_publisher("email", pub)
        self.multi.unregister_publisher("email")
        self.assertNotIn("email", self.multi.list_channels())

    def test_publish_unregistered_channel(self):
        result = run_async(
            self.multi.publish(SAMPLE_ARTICLES, ["nonexistent"])
        )
        self.assertEqual(result.total_failed, 1)
        self.assertEqual(result.total_success, 0)
        self.assertIn("not registered", result.results[0].error)

    @patch.dict(os.environ, {
        "SMTP_SERVER": "smtp.test.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "test-user",
        "EMAIL_TO": "to@test.com",
        "TELEGRAM_BOT_TOKEN": "test-bot-token",
        "TELEGRAM_CHAT_ID": "-100999",
    })
    def test_multi_channel_all_success_mock(self):
        """多渠道 mock 模式全部成功"""
        self.multi.register_publisher("email", EmailPublisher(config={}))
        self.multi.register_publisher("telegram", TelegramPublisher(config={}))

        result = run_async(
            self.multi.publish(SAMPLE_ARTICLES, ["email", "telegram"], use_retry=False)
        )
        self.assertEqual(result.total_success, 2)
        self.assertEqual(result.total_failed, 0)

    def test_single_channel_failure_does_not_block_others(self):
        """單一渠道失敗不影響其他渠道"""
        # Email: 真實模式但缺少 SMTP 配置 → 會失敗
        self.multi.register_publisher(
            "email",
            EmailPublisher(config={"username": "real@gmail.com", "password": "pass"}),
        )
        # Telegram: mock 模式 → 會成功
        self.multi.register_publisher(
            "telegram",
            TelegramPublisher(config={"bot_token": "test-token", "chat_id": "-100"}),
        )

        result = run_async(
            self.multi.publish(SAMPLE_ARTICLES, ["email", "telegram"], use_retry=False)
        )
        # email 因配置不完整失敗，telegram mock 成功
        self.assertEqual(result.total_failed, 1)
        self.assertEqual(result.total_success, 1)

        email_result = next(r for r in result.results if r.channel == "email")
        telegram_result = next(r for r in result.results if r.channel == "telegram")
        self.assertFalse(email_result.success)
        self.assertTrue(telegram_result.success)

    def test_invalid_config_channel_fails_gracefully(self):
        """配置驗證失敗的渠道不阻止其他渠道"""
        self.multi.register_publisher("discord", DiscordPublisher(config={}))
        self.multi.register_publisher(
            "telegram",
            TelegramPublisher(config={"bot_token": "test-tok", "chat_id": "-1"}),
        )

        result = run_async(
            self.multi.publish(
                SAMPLE_ARTICLES,
                ["discord", "telegram"],
                channel_configs={"discord": {}},  # 空 webhook_url → 驗證失敗
                use_retry=False,
            )
        )
        self.assertEqual(result.total_failed, 1)
        self.assertEqual(result.total_success, 1)


# ============================================================
# PublishResult / MultiPublishResult Tests
# ============================================================

class TestDataStructures(unittest.TestCase):

    def test_publish_result_defaults(self):
        r = PublishResult(channel="test", success=True)
        self.assertEqual(r.articles_sent, 0)
        self.assertIsNone(r.error)
        self.assertEqual(r.retry_count, 0)
        self.assertIsNotNone(r.timestamp)

    def test_multi_publish_result_add(self):
        m = MultiPublishResult()
        m.add_result(PublishResult(channel="a", success=True, articles_sent=3))
        m.add_result(PublishResult(channel="b", success=False, error="fail"))
        m.add_result(PublishResult(channel="c", success=True, articles_sent=3))

        self.assertEqual(m.total_success, 2)
        self.assertEqual(m.total_failed, 1)
        self.assertEqual(len(m.results), 3)


if __name__ == "__main__":
    unittest.main()
