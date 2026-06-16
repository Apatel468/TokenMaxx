"""
Tests for the public liveness endpoint (GET /health).
"""


def test_health_returns_ok(client):
    # Confirms the API process is up and returns the expected service metadata.
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("ok", "degraded")
    assert body["service"] == "TokenMaxx"
    assert "tagline" in body
    assert "version" in body
    assert body["database"]["status"] == "ok"
    assert "groq_configured" in body
