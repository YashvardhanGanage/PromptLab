import os
import pytest

# Ensure mock LLM mode is active for all automated test runs
os.environ["MOCK_LLM"] = "true"

from app.config import settings
settings.MOCK_LLM = True

from app.llm_client import llm_client
llm_client.force_mock = True

@pytest.fixture(autouse=True)
def enable_mock_llm():
    settings.MOCK_LLM = True
    llm_client.force_mock = True
    yield
