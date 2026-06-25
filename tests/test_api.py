from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import pytest
from api.app import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@patch("api.app.BlinskyPipeline")
def test_chat(mock_pipeline_class):
    mock_pipeline = MagicMock()
    mock_pipeline.ollama.process.return_value = ("Hello from mock", None)
    mock_pipeline._handle_skill_command.return_value = None
    mock_pipeline_class.return_value = mock_pipeline

    response = client.post(
        "/chat",
        json={"message": "hi"},
        headers={"X-Tavily-Key": "mock-tavily-key", "X-Ollama-URL": "http://localhost:11434"}
    )
    assert response.status_code == 200
    assert response.json()["reply"] == "Hello from mock"


@patch("api.app.SkillManager")
def test_skills_endpoints(mock_skill_manager_class):
    mock_manager = MagicMock()
    mock_manager.list_skills.return_value = [{"name": "s1", "content": "c1"}]
    mock_skill_manager_class.return_value = mock_manager

    # GET /skills
    response = client.get("/skills")
    assert response.status_code == 200
    assert len(response.json()["skills"]) == 1

    # POST /skills
    response = client.post("/skills", json={"name": "s2", "content": "c2"})
    assert response.status_code == 200
    assert response.json()["ok"] is True


@patch("langchain_ollama.OllamaLLM.invoke")
@patch("blinsky.tools.search.web_search")
def test_validate_keys(mock_web_search, mock_ollama_invoke):
    mock_web_search.return_value = "Search result"
    mock_ollama_invoke.return_value = "Ollama response"

    # Valid keys
    response = client.post(
        "/validate-keys",
        headers={"X-Tavily-Key": "mock-tavily-key", "X-Ollama-URL": "http://localhost:11434"}
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True

    # Missing headers
    response = client.post("/validate-keys")
    assert response.status_code == 400
