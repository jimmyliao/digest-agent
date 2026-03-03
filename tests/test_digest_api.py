"""Tests for digest API endpoints (fetch, status)."""

import json
from unittest.mock import AsyncMock, patch

from src.fetcher.rss_fetcher import FetchResult, RawArticle
from src.models.database import TaskRecordDB


class TestTriggerFetch:
    """POST /api/digest/fetch"""

    def test_fetch_default_sources(self, client, db_session):
        resp = client.post("/api/digest/fetch", json={"force_refresh": False})
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["status"] == "queued"
        assert "task_id" in body["data"]
        assert body["data"]["source_count"] == 3  # 3 default sources

    def test_fetch_creates_task_record(self, client, db_session):
        resp = client.post("/api/digest/fetch", json={})
        task_id = resp.json()["data"]["task_id"]

        task = db_session.query(TaskRecordDB).filter(TaskRecordDB.task_id == task_id).first()
        assert task is not None
        assert task.task_type == "fetch"
        assert task.status == "queued"

    def test_fetch_specific_sources(self, client, db_session):
        resp = client.post(
            "/api/digest/fetch",
            json={"source_ids": ["google-official"]},
        )
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["source_count"] == 1

    def test_fetch_invalid_source(self, client, db_session):
        resp = client.post(
            "/api/digest/fetch",
            json={"source_ids": ["nonexistent-source"]},
        )
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "INVALID_SOURCES"
        assert "nonexistent-source" in body["error"]["details"]

    def test_fetch_mixed_valid_invalid_sources(self, client, db_session):
        resp = client.post(
            "/api/digest/fetch",
            json={"source_ids": ["google-official", "bad-source"]},
        )
        body = resp.json()
        assert body["success"] is False
        assert "bad-source" in body["error"]["details"]

    def test_fetch_force_refresh_flag(self, client, db_session):
        resp = client.post(
            "/api/digest/fetch",
            json={"force_refresh": True},
        )
        body = resp.json()
        assert body["success"] is True

    def test_fetch_task_id_format(self, client, db_session):
        resp = client.post("/api/digest/fetch", json={})
        task_id = resp.json()["data"]["task_id"]
        assert task_id.startswith("fetch-")

    def test_fetch_started_at_present(self, client, db_session):
        resp = client.post("/api/digest/fetch", json={})
        data = resp.json()["data"]
        assert "started_at" in data
        assert data["started_at"] is not None


class TestTaskStatus:
    """GET /api/digest/status/{task_id}"""

    def test_get_existing_task(self, client, sample_task):
        resp = client.get("/api/digest/status/test-task-001")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["task_id"] == "test-task-001"
        assert body["data"]["task_type"] == "fetch"

    def test_task_progress_fields(self, client, sample_task):
        body = client.get("/api/digest/status/test-task-001").json()
        progress = body["data"]["progress"]
        assert progress["completed"] == 3
        assert progress["total"] == 3
        assert progress["percentage"] == 100

    def test_completed_task_has_result(self, client, sample_task):
        body = client.get("/api/digest/status/test-task-001").json()
        assert body["data"]["status"] == "completed"
        assert "result" in body["data"]
        assert body["data"]["result"]["articles_fetched"] == 10

    def test_task_timestamps(self, client, sample_task):
        body = client.get("/api/digest/status/test-task-001").json()
        data = body["data"]
        assert data["started_at"] is not None
        assert data["completed_at"] is not None

    def test_task_not_found(self, client):
        resp = client.get("/api/digest/status/nonexistent-task")
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "TASK_NOT_FOUND"

    def test_task_not_found_includes_id(self, client):
        body = client.get("/api/digest/status/bad-id-123").json()
        assert "bad-id-123" in body["error"]["details"]

    def test_fetch_then_check_status(self, client, db_session):
        """Integration: trigger fetch, then check its task status exists."""
        fetch_resp = client.post("/api/digest/fetch", json={})
        task_id = fetch_resp.json()["data"]["task_id"]

        status_resp = client.get(f"/api/digest/status/{task_id}")
        body = status_resp.json()
        assert body["success"] is True
        assert body["data"]["task_id"] == task_id
        assert body["data"]["task_type"] == "fetch"


class TestPublishValidation:
    """POST /api/digest/publish — validation tests."""

    def test_publish_invalid_channel(self, client, db_session):
        resp = client.post(
            "/api/digest/publish",
            json={"article_ids": ["a1"], "channels": ["fax"]},
        )
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "INVALID_CHANNELS"

    def test_publish_valid_channels(self, client, db_session):
        resp = client.post(
            "/api/digest/publish",
            json={"article_ids": ["a1"], "channels": ["email", "telegram"]},
        )
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["status"] == "queued"
        assert set(body["data"]["channels"]) == {"email", "telegram"}
