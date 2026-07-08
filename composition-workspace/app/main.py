"""Composition Workspace & Coordination Console - FastAPI entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.routers import coordination, dashboard, documents, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Composition Workspace & Coordination Console",
    description=(
        "A writing/document editor with version history and comments, "
        "paired with a coordination console for task assignment and "
        "project-wide status tracking."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(users.router)
app.include_router(documents.router)
app.include_router(coordination.router)
app.include_router(dashboard.router)

app.mount("/", StaticFiles(directory="static", html=True), name="static")
