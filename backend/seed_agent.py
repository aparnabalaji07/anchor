"""Creates the demo agent, or resets its password if it already exists.

Run from the backend folder:  python seed_agent.py
"""

import os

from app.auth import hash_password
from app.db import pool

EMAIL = "jake@statefarm.org"
NAME = "Jake"


def main():
    password = os.getenv("DEMO_AGENT_PASSWORD", "")
    if len(password) < 8:
        raise SystemExit("Set DEMO_AGENT_PASSWORD in .env (at least 8 characters).")

    pool.open()
    try:
        with pool.connection() as conn:
            created = conn.execute(
                """INSERT INTO agents (email, name, password_hash) VALUES (%s, %s, %s)
                   ON CONFLICT (email) DO UPDATE
                   SET name = EXCLUDED.name, password_hash = EXCLUDED.password_hash
                   RETURNING (xmax = 0)""",
                (EMAIL, NAME, hash_password(password)),
            ).fetchone()[0]
    finally:
        pool.close()

    print(f"{'Created' if created else 'Updated'} demo agent {EMAIL}")


if __name__ == "__main__":
    main()
