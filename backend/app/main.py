from contextlib import asynccontextmanager

import psycopg
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai_routes import router as ai_router
from app.auth import current_agent
from app.auth import router as auth_router
from app.claims import router as claims_router
from app.db import pool
from app.households import router as households_router
from app.ingest import router as ingest_router
from app.photos import device_router as photo_upload_router
from app.photos import router as photos_router
from app.queue import router as queue_router
from app.stats import router as stats_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool.open()
    yield
    pool.close()


app = FastAPI(title="HackUTD Backend", lifespan=lifespan)

# dev server calls API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173,     "
        "https://anchor4.us",
        "https://www.anchor4.us"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Boxes sign their messages with HMAC, so ingest does not use agent login
app.include_router(ingest_router)
app.include_router(photo_upload_router)
app.include_router(auth_router)

# Everything an agent uses needs a signed-in agent
agent_only = [Depends(current_agent)]
app.include_router(households_router, dependencies=agent_only)
app.include_router(queue_router, dependencies=agent_only)
app.include_router(ai_router, dependencies=agent_only)
app.include_router(claims_router, dependencies=agent_only)
app.include_router(photos_router, dependencies=agent_only)
app.include_router(stats_router, dependencies=agent_only)

@app.get("/health")
def health():
    try:
        with pool.connection() as conn:
            conn.execute("SELECT 1")
        return {"status": "ok", "database": "connected"}
    except psycopg.Error:
        return {"status": "degraded", "database": "unreachable"}