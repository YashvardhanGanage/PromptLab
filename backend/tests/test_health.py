import pytest
from app.main import read_root
from app.api.health import get_health

def test_root():
    data = read_root()
    assert data["name"] == "PromptLab API"
    assert "/docs" in data["docs_url"]

def test_health():
    data = get_health()
    assert data["status"] == "ok"
    assert "llm" in data
    assert "status" in data["llm"]
