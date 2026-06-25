from unittest.mock import MagicMock
import pytest
from blinsky.pipeline import BlinskyPipeline

def test_pipeline_run_turn():
    pipeline = BlinskyPipeline()
    # Mock Ollama process method
    pipeline.ollama.process = MagicMock(return_value=("This is a mock response", None))
    
    # Run pipeline turn with text override
    response = pipeline.run_turn(override_text="Hello", use_agent=False)
    
    assert response == "This is a mock response"
    pipeline.ollama.process.assert_called_once_with("Hello")
