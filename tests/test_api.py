from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import pytest
from api.app import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@patch("api.app._get_pipeline")
def test_chat(mock_get_pipeline):
    mock_pipeline = MagicMock()
    mock_pipeline.ollama.process.return_value = ("Hello from mock", None)
    mock_pipeline._handle_skill_command.return_value = None
    mock_get_pipeline.return_value = mock_pipeline

    response = client.post("/chat", json={"message": "hi"})
    assert response.status_code == 200
    assert response.json()["reply"] == "Hello from mock"

@patch("api.app._get_pipeline")
def test_skills_endpoints(mock_get_pipeline):
    mock_pipeline = MagicMock()
    mock_pipeline.skills.list_skills.return_value = [{"name": "s1", "content": "c1"}]
    mock_get_pipeline.return_value = mock_pipeline

    # GET /skills
    response = client.get("/skills")
    assert response.status_code == 200
    assert len(response.json()["skills"]) == 1

    # POST /skills
    response = client.post("/skills", json={"name": "s2", "content": "c2"})
    assert response.status_code == 200
    assert response.json()["ok"] is True
