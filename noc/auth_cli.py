from __future__ import annotations

import argparse
import asyncio
import getpass
import time
import uuid

import aiosqlite

from noc.auth import password_hash
from noc.auth_models import UserCreate
from noc.db import Database


async def bootstrap_global_admin() -> None:
    db = Database()
    await db.open()
    try:
        existing = await db.query("SELECT id FROM users LIMIT 1")
        active_globals = await db.query("SELECT id FROM users WHERE role='global_admin' AND is_active=1 LIMIT 1")
        if active_globals:
            print("A Global Admin is already configured; bootstrap skipped.")
            return
        if existing:
            raise SystemExit("Users exist but no active Global Admin is available; use the account recovery procedure.")
        username = input("Global Admin username: ").strip()
        password = getpass.getpass("Password (at least 8 characters): ")
        confirmation = getpass.getpass("Confirm password: ")
        if password != confirmation:
            raise SystemExit("Passwords do not match.")
        user = UserCreate(username=username, password=password, role="global_admin")
        now = time.time()
        try:
            await db.execute(
                "INSERT INTO users(id,username,password_hash,role,is_active,created_at,updated_at) VALUES(?,?,?,'global_admin',1,?,?)",
                (str(uuid.uuid4()), user.username, password_hash(user.password), now, now),
            )
        except aiosqlite.IntegrityError:
            raise SystemExit("Could not create the Global Admin account.") from None
        print(f"Global Admin '{user.username}' created. Open http://127.0.0.1:6969/login to sign in.")
    finally:
        await db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="NOC Monitor account administration")
    parser.add_argument("command", choices=["bootstrap"], help="create the first Global Admin account")
    args = parser.parse_args()
    if args.command == "bootstrap":
        asyncio.run(bootstrap_global_admin())


if __name__ == "__main__":
    main()
