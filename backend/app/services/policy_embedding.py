"""Fill in the embeddings of policy chunks.

A chunk needs an embedding when it is active and either has none or was made by
a different model than the one in use. Run this after loading policies.
"""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.agent.embeddings import Embedder
from app.models.policy import Policy

BATCH_SIZE = 32


def chunk_embedding_text(policy: Policy) -> str:
    """The text that gets embedded.

    The title and section heading are included because a section such as
    'Reporting window' means little without the policy it belongs to.
    """
    return f"{policy.title}: {policy.section}\n{policy.content}"


def embed_policies(db: Session, embedder: Embedder) -> int:
    """Embed every active chunk that has no embedding from this model. Returns how many."""
    pending = db.scalars(
        select(Policy)
        .where(
            Policy.is_active.is_(True),
            or_(
                Policy.embedding.is_(None),
                Policy.embedding_model != embedder.model_name,
            ),
        )
        .order_by(Policy.slug, Policy.chunk_index)
    ).all()

    try:
        for start in range(0, len(pending), BATCH_SIZE):
            batch = pending[start : start + BATCH_SIZE]
            vectors = embedder.embed_documents([chunk_embedding_text(p) for p in batch])
            for policy, vector in zip(batch, vectors, strict=True):
                policy.embedding = vector
                policy.embedding_model = embedder.model_name
        db.commit()
    except Exception:
        db.rollback()
        raise
    return len(pending)
