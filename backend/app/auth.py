import hashlib
import hmac
import os
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.db import pool

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

AUTH_SECRET = os.getenv("AUTH_SECRET", "")
if len(AUTH_SECRET) < 32:
    raise RuntimeError("AUTH_SECRET is missing or shorter than 32 characters. Check .env file.")

TOKEN_HOURS = 12
ALGORITHM = "HS256"

# scrypt settings: about 16 MB of memory per hash, which makes brute force expensive
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 1


def hash_password(password: str) -> str:
    """Returns 'scrypt$n$r$p$salt$hash' so the settings travel with the hash."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt, digest = stored.split("$")
    except ValueError:
        return False
    if algo != "scrypt":
        return False
    check = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p))
    return hmac.compare_digest(check.hex(), digest)


# Checked when the email is unknown, so both failure cases take the same time
_DUMMY_HASH = hash_password(secrets.token_hex(16))


def create_token(agent: dict) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(agent["id"]),
        "iat": now,
        "exp": now + timedelta(hours=TOKEN_HOURS),
    }
    return jwt.encode(payload, AUTH_SECRET, algorithm=ALGORITHM)


bearer = HTTPBearer(auto_error=False)


def unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=401, detail=detail, headers={"WWW-Authenticate": "Bearer"})


def current_agent(creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> dict:
    """Requires 'Authorization: Bearer <token>' and returns the signed-in agent."""
    if creds is None:
        raise unauthorized("Not signed in")
    try:
        payload = jwt.decode(
            creds.credentials, AUTH_SECRET, algorithms=[ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
        agent_id = int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError):
        raise unauthorized("Session expired or invalid. Sign in again.") from None

    # Look the agent up so a deleted account stops working right away
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT id, email, name FROM agents WHERE id = %s", (agent_id,)
        ).fetchone()
    if row is None:
        raise unauthorized("Session expired or invalid. Sign in again.")
    return {"id": row[0], "email": row[1], "name": row[2]}


# Use as a parameter type to get the signed-in agent in an endpoint
CurrentAgent = Annotated[dict, Depends(current_agent)]

router = APIRouter(prefix="/auth")


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(body: LoginRequest):
    email = body.email.strip().lower()
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT id, email, name, password_hash FROM agents WHERE email = %s", (email,)
        ).fetchone()

    if row is None:
        verify_password(body.password, _DUMMY_HASH)
        raise unauthorized("Wrong email or password")
    if not verify_password(body.password, row[3]):
        raise unauthorized("Wrong email or password")

    agent = {"id": row[0], "email": row[1], "name": row[2]}
    return {"token": create_token(agent), "name": agent["name"], "email": agent["email"]}


@router.get("/me")
def me(agent: CurrentAgent):
    return {"name": agent["name"], "email": agent["email"]}
