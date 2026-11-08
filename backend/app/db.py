import os
from pathlib import Path

from dotenv import load_dotenv
from psycopg_pool import ConnectionPool

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

DATABASE_URL = os.getenv("TIGERDATA_URL")
if not DATABASE_URL:
    raise RuntimeError("TIGERDATA_URL is missing. Check .env file.")

pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=5, open=False)