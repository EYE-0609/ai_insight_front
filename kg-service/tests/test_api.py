from fastapi.testclient import TestClient

from app import app
from tests.test_graph_extractor import sample_insight_payload


client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_build_graph_api_returns_graph_payload():
    response = client.post("/api/graph/build", json={"insight_payload": sample_insight_payload()})

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_profile"]["industry"] == "新能源"
    assert payload["company_edges"]
    assert payload["profile_edges"]
    assert payload["evidence_chunks"]


def test_build_and_persist_skips_without_neo4j_uri(monkeypatch):
    monkeypatch.delenv("NEO4J_URI", raising=False)

    response = client.post("/api/graph/build-and-persist", json={"insight_payload": sample_insight_payload()})

    assert response.status_code == 200
    payload = response.json()
    assert payload["persistence_meta"]["status"] == "skipped"
    assert payload["persistence_meta"]["reason"] == "missing_neo4j_uri"

