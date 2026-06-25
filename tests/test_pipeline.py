from unittest.mock import MagicMock, patch
import pytest
from blinsky.pipeline import BlinskyPipeline

@patch("blinsky.pipeline.Memory")
@patch("langchain_ollama.OllamaLLM")
def test_pipeline_run_turn(mock_llm, mock_memory):
    pipeline = BlinskyPipeline(bypass_memory=True)
    # Mock Ollama process method
    pipeline.ollama.process = MagicMock(return_value=("This is a mock response", None))
    
    # Run pipeline turn with text override
    response = pipeline.run_turn(override_text="Hello", use_agent=False)
    
    assert response == "This is a mock response"
    pipeline.ollama.process.assert_called_once_with("Hello")
