import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup → yield → shutdown."""
    print(f"🚀 TriageNet API starting up — Environment: {settings.APP_ENV}")
    print(f"   DB URL:     {settings.DATABASE_URL[:40]}...")
    print(f"   Azure OAI:  {settings.AZURE_OPENAI_ENDPOINT}")
    # Future: start background monitoring worker here
    yield
    print("🛑 TriageNet API shutting down gracefully.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="TriageNet API",
        description="Multi-Agent Emergency Department Orchestration System",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],          # Tighten in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers (mounted after creation so imports resolve) ───────────────────
    from app.api.v1 import patients, hitl, websockets   # noqa: E402 – intentional

    app.include_router(patients.router, prefix="/api/v1", tags=["patients"])
    app.include_router(hitl.router,     prefix="/api/v1", tags=["hitl"])
    app.include_router(websockets.router, prefix="",      tags=["websockets"])

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["system"])
    async def health_check():
        return {
            "status": "healthy",
            "service": "TriageNet API",
            "version": "1.0.0",
            "environment": settings.APP_ENV,
        }

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,          # Turn off in production
        log_level="info",
    )