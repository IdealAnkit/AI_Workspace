"""Create the initial administrator without ever creating a duplicate admin."""

import argparse
import asyncio
import getpass
import sys
from pathlib import Path

# Allow `python scripts/seed_admin.py` from the backend directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config.settings import get_settings  # noqa: E402
from app.database.engine import AsyncSessionLocal  # noqa: E402
from app.services.auth_service import AuthService  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create the first AI Workspace admin user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--full-name", required=True)
    return parser.parse_args()


async def seed_admin() -> int:
    args = parse_args()
    password = getpass.getpass("Admin password (minimum 12 characters): ")
    password_length = len(password.encode("utf-8"))
    if password_length < 12 or password_length > 72:
        print("Admin password must contain 12-72 UTF-8 bytes.", file=sys.stderr)
        return 2

    async with AsyncSessionLocal() as session:
        try:
            admin = await AuthService(session, get_settings()).create_admin(
                email=args.email.strip().lower(),
                username=args.username.strip().lower(),
                full_name=args.full_name.strip(),
                password=password,
            )
            if admin is None:
                print("An administrator already exists; no user was created.")
                return 0
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    print(f"Created administrator: {admin.email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(seed_admin()))
