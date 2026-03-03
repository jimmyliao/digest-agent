"""Tests for articles API endpoints."""

import json
import uuid
from datetime import datetime, timezone

from src.models.database import ArticleDB


class TestListArticles:
    """GET /api/articles/"""

    def test_empty_db_returns_empty_list(self, client):
        resp = client.get("/api/articles/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["items"] == []
        assert body["data"]["total"] == 0

    def test_returns_articles(self, client, sample_articles):
        resp = client.get("/api/articles/")
        body = resp.json()
        assert body["success"] is True
        assert len(body["data"]["items"]) == 10
        assert body["data"]["total"] == 10

    def test_pagination_limit(self, client, sample_articles):
        resp = client.get("/api/articles/?limit=3")
        body = resp.json()
        assert len(body["data"]["items"]) == 3
        assert body["data"]["has_more"] is True
        assert body["data"]["limit"] == 3

    def test_pagination_skip(self, client, sample_articles):
        resp = client.get("/api/articles/?skip=8&limit=5")
        body = resp.json()
        assert len(body["data"]["items"]) == 2  # only 2 remaining
        assert body["data"]["skip"] == 8
        assert body["data"]["has_more"] is False

    def test_filter_by_source(self, client, sample_articles):
        resp = client.get("/api/articles/?source=google-ai")
        body = resp.json()
        items = body["data"]["items"]
        assert len(items) > 0
        assert all(a["source"] == "google-ai" for a in items)

    def test_filter_by_status(self, client, sample_articles):
        resp = client.get("/api/articles/?status=published")
        body = resp.json()
        items = body["data"]["items"]
        assert len(items) > 0
        assert all(a["publish_status"] == "published" for a in items)

    def test_filter_by_status_pending(self, client, sample_articles):
        resp = client.get("/api/articles/?status=pending")
        body = resp.json()
        items = body["data"]["items"]
        assert all(a["publish_status"] == "pending" for a in items)

    def test_search_by_title(self, client, sample_articles):
        resp = client.get("/api/articles/?search=Article 0")
        body = resp.json()
        items = body["data"]["items"]
        assert len(items) >= 1
        assert any("Article 0" in a["title"] for a in items)

    def test_search_no_match(self, client, sample_articles):
        resp = client.get("/api/articles/?search=zzz_nonexistent_zzz")
        body = resp.json()
        assert body["data"]["total"] == 0
        assert body["data"]["items"] == []

    def test_sort_by_title_asc(self, client, sample_articles):
        resp = client.get("/api/articles/?sort_by=title&order=asc")
        body = resp.json()
        titles = [a["title"] for a in body["data"]["items"]]
        assert titles == sorted(titles)

    def test_combined_filters(self, client, sample_articles):
        resp = client.get("/api/articles/?source=google-ai&status=pending&limit=5")
        body = resp.json()
        items = body["data"]["items"]
        for a in items:
            assert a["source"] == "google-ai"
            assert a["publish_status"] == "pending"

    def test_article_fields_present(self, client, sample_articles):
        resp = client.get("/api/articles/?limit=1")
        item = resp.json()["data"]["items"][0]
        required_fields = [
            "id", "title", "source", "source_url", "published_at",
            "tags", "publish_status", "publish_channels",
        ]
        for field in required_fields:
            assert field in item, f"Missing field: {field}"

    def test_tags_returned_as_list(self, client, sample_articles):
        resp = client.get("/api/articles/?limit=1")
        item = resp.json()["data"]["items"][0]
        assert isinstance(item["tags"], list)


class TestGetArticle:
    """GET /api/articles/{article_id}"""

    def test_get_existing_article(self, client, sample_articles):
        article_id = sample_articles[0].id
        resp = client.get(f"/api/articles/{article_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["id"] == article_id
        assert body["data"]["title"] == sample_articles[0].title

    def test_get_article_has_detail_fields(self, client, sample_articles):
        article_id = sample_articles[0].id
        body = client.get(f"/api/articles/{article_id}").json()
        data = body["data"]
        assert "language" in data
        assert "content_hash" in data
        assert "metadata" in data

    def test_article_not_found(self, client):
        resp = client.get("/api/articles/nonexistent-uuid")
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "ARTICLE_NOT_FOUND"

    def test_article_not_found_includes_id(self, client):
        fake_id = "fake-id-12345"
        body = client.get(f"/api/articles/{fake_id}").json()
        assert fake_id in body["error"]["details"]
