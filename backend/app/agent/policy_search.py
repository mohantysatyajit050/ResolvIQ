"""Policy search tool: the policy_retrieval node of the agent. No LLM.

Finds the policy chunks closest in meaning to a complaint.

Rules:
- only active chunks, and only chunks embedded by the same model as the query
- the router's intent narrows the search to that policy; 'other' or no intent
  searches every policy
- results come from the policies table, so the agent can only quote stored text
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.embeddings import Embedder
from app.models.policy import Policy
from app.models.ticket import TicketIntent

MAX_QUERY_CHARS = 2000
DEFAULT_LIMIT = 3


@dataclass(frozen=True)
class PolicyHit:
    policy_id: uuid.UUID
    slug: str
    title: str
    section: str
    chunk_index: int
    version: int
    applies_to: str
    content: str
    score: float  # cosine similarity: closer to 1 means closer in meaning


def search_policies(
    db: Session,
    embedder: Embedder,
    query: str,
    intent: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[PolicyHit]:
    """Return the chunks closest in meaning to the query, best first."""
    if intent is not None and intent not in {i.value for i in TicketIntent}:
        raise ValueError(f"unknown intent {intent!r}")
    if limit < 1:
        raise ValueError("limit must be at least 1")

    query = query.strip()[:MAX_QUERY_CHARS]
    if not query:
        return []

    distance = Policy.embedding.cosine_distance(embedder.embed_query(query))
    stmt = select(Policy, distance.label("distance")).where(
        Policy.is_active.is_(True),
        Policy.embedding.is_not(None),
        Policy.embedding_model == embedder.model_name,
    )
    if intent is not None and intent != "other":
        stmt = stmt.where(Policy.applies_to == intent)

    rows = db.execute(
        stmt.order_by(distance, Policy.slug, Policy.chunk_index).limit(limit)
    ).all()
    return [
        PolicyHit(
            policy_id=policy.id,
            slug=policy.slug,
            title=policy.title,
            section=policy.section,
            chunk_index=policy.chunk_index,
            version=policy.version,
            applies_to=policy.applies_to,
            content=policy.content,
            score=1.0 - float(dist),
        )
        for policy, dist in rows
    ]
