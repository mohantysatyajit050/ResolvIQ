"""Load the policy files in backend/policies/ into the database.

Run from the backend folder:
    uv run python -m scripts.seed_policies

Safe to run again: unchanged policies are skipped, and a policy edited
without a version bump is refused with a clear message.
"""

import sys
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.policy_service import (
    POLICY_DIR,
    PolicyFileError,
    PolicyVersionError,
    load_policies,
)


def run(db: Session, directory: Path = POLICY_DIR) -> int:
    """Load the policies and print what happened. Returns the exit code."""
    try:
        summary = load_policies(db, directory)
    except (PolicyFileError, PolicyVersionError) as error:
        print(f"Policy load failed: {error}")
        return 1
    print(f"Added or updated: {', '.join(summary.added) or 'none'}")
    print(f"Already up to date: {', '.join(summary.unchanged) or 'none'}")
    return 0


def main() -> int:
    with SessionLocal() as db:
        return run(db)


if __name__ == "__main__":
    sys.exit(main())
