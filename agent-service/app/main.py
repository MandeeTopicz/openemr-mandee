"""
CareTopicz Agent Service - FastAPI application entrypoint.

Provides /health and /chat endpoints, CORS for OpenEMR.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load .env into os.environ so LangSmith (LANGCHAIN_*) can read it
_agent_root = Path(__file__).resolve().parent.parent
load_dotenv(_agent_root / ".env")

from app.api.routes import router
from app.config import settings
from app.observability.langsmith import is_tracing_enabled, setup_langsmith


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Configure LangSmith tracing with PHI redaction
    setup_langsmith(enable_phi_redaction=True)

    # Print config on startup (mask API key)
    key_status = "set" if settings.anthropic_api_key else "NOT SET"
    is_placeholder = (
        settings.anthropic_api_key == "your_api_key_here"
        if settings.anthropic_api_key
        else True
    )
    key_note = " (placeholder - replace with real key)" if is_placeholder and settings.anthropic_api_key else ""
    print("[CareTopicz] Config on startup:")
    print(f"  ANTHROPIC_API_KEY: {key_status}{key_note}")
    print(f"  ANTHROPIC_MODEL: {settings.anthropic_model}")
    print(f"  CORS_ORIGINS: {settings.cors_origins}")
    print(f"  LangSmith tracing: {'enabled' if is_tracing_enabled() else 'disabled (set LANGCHAIN_TRACING_V2=true to enable)'}")
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

# CORS - allow OpenEMR at localhost:8300
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, tags=["agent"])


@app.get("/")
async def root():
    """Root redirect/info."""
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "health": "/health",
        "chat": "/chat",
    }
