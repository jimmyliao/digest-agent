"""Tests for health check endpoints."""


class TestHealthSimple:
    """GET /health — docker-compose healthcheck endpoint."""

    def test_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_status_ok(self, client):
        data = client.get("/health").json()
        assert data["status"] == "ok"

    def test_db_field_present(self, client):
        data = client.get("/health").json()
        assert "db" in data

    def test_version_field(self, client):
        data = client.get("/health").json()
        assert "version" in data
        assert data["version"] == "0.1.0"


class TestHealthDetailed:
    """GET /api/health — detailed health check for API consumers."""

    def test_returns_200(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_success_true(self, client):
        data = client.get("/api/health").json()
        assert data["success"] is True

    def test_data_structure(self, client):
        body = client.get("/api/health").json()
        assert "data" in body
        assert body["data"]["status"] == "healthy"
        assert "version" in body["data"]

    def test_components_database(self, client):
        body = client.get("/api/health").json()
        components = body["data"]["components"]
        assert "database" in components
        assert components["database"]["status"] == "ok"
        assert "response_time_ms" in components["database"]
