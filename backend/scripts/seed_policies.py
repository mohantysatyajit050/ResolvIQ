"""Load the policy files in backend/policies/ into the database and embed them.

Run from the backend folder:
    uv run python -m scripts.seed_policies

Safe to run again: unchanged policies are skipped, a policy edited without a
version bump is refused with a clear message, and only chunks without an
embedding from the current model are embedded.
The first run downloads the embedding model (about 70 MB).
"""

import sys
from pathlib import Path

from sqlalchemy.orm import Session

from app.agent.embeddings import Embedder, EmbeddingError, get_embedder
from app.db.session import SessionLocal
from app.services.policy_embedding import embed_policies
from app.services.policy_service import (
    POLICY_DIR,
    PolicyFileError,
    PolicyVersionError,
    load_policies,
)


def run(db: Session, embedder: Embedder, directory: Path = POLICY_DIR) -> int:
    """Load and embed the policies, print what happened. Returns the exit code."""
    try:
        summary = load_policies(db, directory)
        embedded = embed_policies(db, embedder)
    except (PolicyFileError, PolicyVersionError, EmbeddingError) as error:
        print(f"Policy load failed: {error}")
        return 1
    print(f"Added or updated: {', '.join(summary.added) or 'none'}")
    print(f"Already up to date: {', '.join(summary.unchanged) or 'none'}")
    print(f"Embedded chunks: {embedded}")
    return 0


def main() -> int:
    try:
        embedder = get_embedder()
    except EmbeddingError as error:
        print(f"Policy load failed: {error}")
        return 1
    with SessionLocal() as db:
        return run(db, embedder)


if __name__ == "__main__":
    sys.exit(main())
