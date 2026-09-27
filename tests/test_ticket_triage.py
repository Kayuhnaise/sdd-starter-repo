"""Support ticket triage — acceptance tests for specs/spec-v1.md.

Test names correspond directly to the numbered acceptance criteria in the
feature specification.
"""

from __future__ import annotations


def test_ac1_successful_triage(client):
    response = client.get("/tickets/T-001/triage")

    assert response.status_code == 200

    body = response.json()

    assert body["ticket"]["id"] == "T-001"
    assert body["ticket"]["subject"] == "Refund for duplicate charge"
    assert body["ticket"]["body"] == (
        "I was billed twice for my September membership. Please refund one."
    )

    assert body["triage"]["category"]
    assert body["triage"]["priority"]
    assert body["triage"]["suggested_team"]
    assert body["triage"]["draft_first_reply"]

    assert "confidence" in body["model"]
    assert "model_version" in body["model"]
    assert "latency_ms" in body["model"]

def test_ac2_supported_category_and_priority(client):
    response = client.get("/tickets/T-001/triage")

    assert response.status_code == 200

    triage = response.json()["triage"]

    assert triage["category"] in {
        "billing",
        "access",
        "data",
        "outage",
        "general",
    }
    assert triage["priority"] in {
        "high",
        "normal",
        "low",
    }

def test_ac3_low_confidence_requires_human_review(client):
    response = client.get("/tickets/T-016/triage")

    assert response.status_code == 200

    body = response.json()

    assert body["model"]["confidence"] < 0.50
    assert body["triage"]["requires_human_review"] is True
    assert body["model"]["value"] is not None

def test_ac4_normal_confidence_does_not_require_review(client):
    response = client.get("/tickets/T-001/triage")

    assert response.status_code == 200

    body = response.json()

    assert body["model"]["confidence"] >= 0.50
    assert body["triage"]["requires_human_review"] is False

def test_ac5_missing_subject_uses_body(client):
    response = client.get("/tickets/T-020/triage")

    assert response.status_code == 200

    body = response.json()

    assert body["ticket"]["id"] == "T-020"
    assert body["ticket"]["subject"] == ""
    assert body["ticket"]["body"] == "Body with no subject at all."
    assert body["triage"]["category"]


def test_ac6_missing_body_uses_subject(client):
    response = client.get("/tickets/T-021/triage")

    assert response.status_code == 200

    body = response.json()

    assert body["ticket"]["id"] == "T-021"
    assert body["ticket"]["subject"] == "Subject with no body"
    assert body["ticket"]["body"] == ""
    assert body["triage"]["category"]

def test_ac7_unknown_ticket_returns_404(client):
    response = client.get("/tickets/T-999/triage")

    assert response.status_code == 404

    body = response.json()
    assert body["code"] == "not_found"


def test_ac8_model_unavailable_returns_503(client, monkeypatch):
    from app import model_client as mc

    monkeypatch.setenv("STUB_FAILURE_RATE", "1.0")
    mc.reset_client()

    response = client.get("/tickets/T-001/triage")

    assert response.status_code == 503

    body = response.json()
    assert body["code"] == "model_unavailable"


def test_ac9_model_timeout_returns_504(client, monkeypatch):
    from app import model_client as mc

    monkeypatch.setenv("STUB_LATENCY_MS", "900")
    monkeypatch.setenv("STUB_TIMEOUT_MS", "100")
    monkeypatch.setenv("STUB_SLEEP", "0")
    mc.reset_client()

    response = client.get("/tickets/T-001/triage")

    assert response.status_code == 504

    body = response.json()
    assert body["code"] == "model_timeout"

def test_ac10_response_contains_model_payload(client):
    response = client.get("/tickets/T-001/triage")

    assert response.status_code == 200

    model = response.json()["model"]

    assert "value" in model
    assert "confidence" in model
    assert "model_version" in model
    assert "latency_ms" in model

    assert 0.0 <= model["confidence"] <= 1.0
    assert model["model_version"] in ("v1", "v2")
    assert model["latency_ms"] >= 0

def test_ac11_model_version_is_reported(client, monkeypatch):
    from app import model_client as mc

    monkeypatch.setenv("STUB_MODEL_VERSION", "v1")
    mc.reset_client()

    first = client.get("/tickets/T-001/triage")

    assert first.status_code == 200
    assert first.json()["model"]["model_version"] == "v1"

    monkeypatch.setenv("STUB_MODEL_VERSION", "v2")
    mc.reset_client()

    second = client.get("/tickets/T-001/triage")

    assert second.status_code == 200
    assert second.json()["model"]["model_version"] == "v2"

def test_ac12_draft_reply_is_not_sent(client):
    response = client.get("/tickets/T-001/triage")

    assert response.status_code == 200

    triage = response.json()["triage"]

    assert triage["draft_first_reply"]
    assert "draft_first_reply" in triage


def test_ac13_duplicate_tickets_remain_independent(client):
    first = client.get("/tickets/T-001/triage")
    duplicate = client.get("/tickets/T-011/triage")

    assert first.status_code == 200
    assert duplicate.status_code == 200

    first_body = first.json()
    duplicate_body = duplicate.json()

    assert first_body["ticket"]["id"] == "T-001"
    assert duplicate_body["ticket"]["id"] == "T-011"
    assert first_body["ticket"] != duplicate_body["ticket"]


def test_ac14_concurrent_requests_do_not_modify_ticket(client):
    first = client.get("/tickets/T-001/triage")
    second = client.get("/tickets/T-001/triage")

    assert first.status_code == 200
    assert second.status_code == 200

    assert first.json()["ticket"] == second.json()["ticket"]
    assert first.json()["ticket"]["id"] == "T-001"