from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import pool
from app.ingest import router as ingest_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool.open()
    yield
    pool.close()


app = FastAPI(title="HackUTD Backend", lifespan=lifespan)

# dev server calls API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router)

@app.get("/health")
def health():
    try:
        with pool.connection() as conn:
            conn.execute("SELECT 1")
        return {"status": "ok", "database": "connected"}
    except psycopg.Error:
        return {"status": "degraded", "database": "unreachable"}