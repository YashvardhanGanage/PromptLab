from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.dataset_service import ensure_starter_dataset
from app.api.health import router as health_router
from app.api.experiments import router as experiments_router
from app.api.prompts import router as prompts_router
from app.api.datasets import router as datasets_router
from app.api.evaluations import router as evaluations_router
from app.api.agent_runs import router as agent_runs_router
from app.api.dashboard import router as dashboard_router
from app.api.export import router as export_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize SQLite tables and starter benchmark dataset
    init_db()
    ensure_starter_dataset()
    yield

app = FastAPI(
    title="PromptLab API",
    description="Agentic AI Prompt Testing, Evaluation & Optimization Platform",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for local development and Vercel/custom frontend deployments
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers with /api prefix
app.include_router(health_router, prefix="/api")
app.include_router(experiments_router, prefix="/api")
app.include_router(prompts_router, prefix="/api")
app.include_router(datasets_router, prefix="/api")
app.include_router(evaluations_router, prefix="/api")
app.include_router(agent_runs_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(export_router, prefix="/api")

@app.get("/")
def read_root():
    return {
        "name": "PromptLab API",
        "description": "Evidence-based prompt evaluation and agentic optimization engine",
        "docs_url": "/docs",
        "version": "1.0.0"
    }
