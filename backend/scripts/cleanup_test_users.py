"""
Remove demo/test users from the TokenMaxx SQLite database.

These accounts are NOT seeded by the app — they are usually created by manual
signup during development or one-off API tests (e.g. testuser@example.com).

Usage (from backend/):
    python scripts/cleanup_test_users.py
    python scripts/cleanup_test_users.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running as: python scripts/cleanup_test_users.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session

from database import Conversation, Message, ModelRun, SessionLocal, User

# Known integration-test / demo emails created during development
KNOWN_TEST_EMAILS = frozenset(
    {
        "admintest@example.com",
        "brandnew@example.com",
        "newfix@example.com",
        "testuser@example.com",
        "admin@example.com",
    }
)


def _emails_to_remove(db: Session, include_example_domain: bool) -> list[User]:
    """Return user rows that match test/demo criteria."""
    users = db.query(User).all()
    targets: list[User] = []
    for user in users:
        email = user.email.strip().lower()
        if email in KNOWN_TEST_EMAILS:
            targets.append(user)
        elif include_example_domain and email.endswith("@example.com"):
            targets.append(user)
    return targets


def delete_users_and_data(db: Session, users: list[User], *, dry_run: bool) -> int:
    """Delete users plus their conversations, messages, and model_runs."""
    if not users:
        return 0

    user_ids = [u.id for u in users]
    conv_ids = [
        row.id
        for row in db.query(Conversation.id)
        .filter(Conversation.user_id.in_(user_ids))
        .all()
    ]

    if dry_run:
        for user in users:
            print(f"[dry-run] would delete user id={user.id} email={user.email}")
        return len(users)

    if conv_ids:
        db.query(ModelRun).filter(ModelRun.conversation_id.in_(conv_ids)).delete(
            synchronize_session=False
        )
        db.query(Message).filter(Message.conversation_id.in_(conv_ids)).delete(
            synchronize_session=False
        )
        db.query(Conversation).filter(Conversation.id.in_(conv_ids)).delete(
            synchronize_session=False
        )

    db.query(ModelRun).filter(ModelRun.user_id.in_(user_ids)).delete(
        synchronize_session=False
    )
    deleted = (
        db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
    )
    db.commit()
    return deleted


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete demo/test users from SQLite")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be deleted without changing the database",
    )
    parser.add_argument(
        "--all-example-com",
        action="store_true",
        help="Also delete any user with an @example.com email",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        targets = _emails_to_remove(db, include_example_domain=args.all_example_com)
        count = delete_users_and_data(db, targets, dry_run=args.dry_run)
        if count == 0:
            print("No test users found.")
        elif args.dry_run:
            print(f"Dry run complete — {count} user(s) would be removed.")
        else:
            print(f"Removed {count} test user(s).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
