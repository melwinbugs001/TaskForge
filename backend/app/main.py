from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, goals, push, team_tasks, teams
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="TaskForge",
    description="A controlled, observable platform for multi-step AI agent workflows.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(goals.router, prefix="/api/v1")
app.include_router(teams.router, prefix="/api/v1")
app.include_router(team_tasks.router, prefix="/api/v1")
app.include_router(push.router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/health", tags=["health"])
def api_health_check() -> dict[str, str]:
    return {"status": "ok"}
