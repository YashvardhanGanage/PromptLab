from fastapi import APIRouter
from app.llm_client import llm_client

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("")
def get_health():
    model_status = llm_client.check_connection_sync()
    return {
        "status": "ok",
        "service": "PromptLab API",
        "version": "1.0.0",
        "llm": model_status
    }
