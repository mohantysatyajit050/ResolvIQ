"""Tests for policy embedding and search. They use the fake embedder and the test database."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.agent.embeddings import EMBEDDING_DIM, FakeEmbedder
from app.agent.policy_search import search_policies
from app.models.policy import Policy
from app.services.policy_embedding import embed_policies
from app.services.policy_service import active_chunks, load_policies


class OtherFakeEmbedder(FakeEmbedder):
    model_name = "other-fake-embedder"


def write_policy(directory, slug, applies_to, sections, version=1):
    body = "".join(f"## {name}\n{text}\n\n" for name, text in sections)
    (directory / f"{slug}.md").write_text(
        "---\n"
        f"slug: {slug}\n"
        f"applies_to: {applies_to}\n"
        f"version: {version}\n"
        "---\n"
        f"# {slug} policy\n\n"
        f"{body}",
        encoding="utf-8",
    )


DAMAGED = [
    ("Reporting window", "Report broken or cracked items within 24 hours of delivery."),
    ("Evidence required", "Attach a clear photo of the damaged item."),
]
LATE = [
    ("Cancelling", "Cancel the order and get a refund when it is days past the expected date."),
    ("Waiting", "If the order is only a little late, wait while we track the parcel."),
]


@pytest.fixture()
def policies_dir(tmp_path):
    write_policy(tmp_path, "damaged-item", "damaged_item", DAMAGED)
    write_policy(tmp_path, "late-delivery", "late_delivery", LATE)
    return tmp_path


@pytest.fixture()
def searchable(db_session, policies_dir):
    """Both demo policies loaded and embedded with the fake embedder."""
    load_policies(db_session, policies_dir)
    embed_policies(db_session, FakeEmbedder())


def test_embed_fills_every_active_chunk(db_session, policies_dir):
    load_policies(db_session, policies_dir)

    assert embed_policies(db_session, FakeEmbedder()) == 4

    rows = active_chunks(db_session)
    assert all(r.embedding is not None for r in rows)
    assert all(len(r.embedding) == EMBEDDING_DIM for r in rows)
    assert all(r.embedding_model == "fake-embedder" for r in rows)


def test_embedding_twice_does_nothing_the_second_time(db_session, policies_dir):
    load_policies(db_session, policies_dir)
    embed_policies(db_session, FakeEmbedder())

    assert embed_policies(db_session, FakeEmbedder()) == 0


def test_inactive_chunks_are_not_embedded(db_session, policies_dir):
    load_policies(db_session, policies_dir)
    write_policy(policies_dir, "damaged-item", "damaged_item", DAMAGED, version=2)
    load_policies(db_session, policies_dir)

    # 2 damaged-item chunks of version 2 and 2 late-delivery chunks of version 1
    assert embed_policies(db_session, FakeEmbedder()) == 4

    old = db_session.scalars(
        select(Policy).where(Policy.slug == "damaged-item", Policy.version == 1)
    ).all()
    assert len(old) == 2
    assert all(r.embedding is None for r in old)


def test_a_different_model_means_everything_is_embedded_again(db_session, policies_dir):
    load_policies(db_session, policies_dir)
    embed_policies(db_session, FakeEmbedder())

    assert embed_policies(db_session, OtherFakeEmbedder()) == 4

    assert {r.embedding_model for r in active_chunks(db_session)} == {"other-fake-embedder"}


@pytest.mark.parametrize(
    "vector, model",
    [([0.1] * EMBEDDING_DIM, None), (None, "some-model")],
)
def test_database_refuses_a_vector_and_model_that_do_not_go_together(
    db_session, vector, model
):
    db_session.add(
        Policy(
            slug="x",
            title="t",
            section="s",
            chunk_index=0,
            version=1,
            applies_to="other",
            content="c",
            content_hash="h",
            embedding=vector,
            embedding_model=model,
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_search_finds_the_matching_chunk_first(db_session, searchable):
    hits = search_policies(
        db_session, FakeEmbedder(), "how many hours to report a cracked item"
    )

    assert (hits[0].slug, hits[0].section) == ("damaged-item", "Reporting window")
    assert hits[0].content == "Report broken or cracked items within 24 hours of delivery."
    assert hits[0].score >= hits[1].score >= hits[2].score


def test_intent_limits_the_search_to_that_policy(db_session, searchable):
    hits = search_policies(
        db_session,
        FakeEmbedder(),
        "how many hours to report a cracked item",
        intent="late_delivery",
    )

    assert {h.slug for h in hits} == {"late-delivery"}


@pytest.mark.parametrize("intent", [None, "other"])
def test_no_intent_or_other_searches_every_policy(db_session, searchable, intent):
    hits = search_policies(
        db_session,
        FakeEmbedder(),
        "refund when the order is days past the expected date",
        intent=intent,
        limit=4,
    )

    assert len(hits) == 4
    assert {h.slug for h in hits} == {"damaged-item", "late-delivery"}


def test_search_respects_the_limit(db_session, searchable):
    hits = search_policies(db_session, FakeEmbedder(), "cracked item", limit=1)

    assert len(hits) == 1


def test_a_limit_below_one_is_an_error(db_session, searchable):
    with pytest.raises(ValueError):
        search_policies(db_session, FakeEmbedder(), "cracked item", limit=0)


def test_search_ignores_chunks_made_by_another_model(db_session, searchable):
    assert search_policies(db_session, OtherFakeEmbedder(), "cracked item") == []


def test_search_ignores_chunks_without_embeddings(db_session, policies_dir):
    load_policies(db_session, policies_dir)  # loaded but never embedded

    assert search_policies(db_session, FakeEmbedder(), "cracked item") == []


def test_search_never_returns_old_versions(db_session, policies_dir):
    load_policies(db_session, policies_dir)
    embed_policies(db_session, FakeEmbedder())
    write_policy(
        policies_dir,
        "damaged-item",
        "damaged_item",
        [
            ("Reporting window", "Report cracked items within 48 hours of delivery."),
            ("Evidence required", "Attach a photo."),
        ],
        version=2,
    )
    load_policies(db_session, policies_dir)
    embed_policies(db_session, FakeEmbedder())

    hits = search_policies(
        db_session, FakeEmbedder(), "cracked items report hours", intent="damaged_item", limit=10
    )

    assert len(hits) == 2
    assert {h.version for h in hits} == {2}


def test_an_empty_query_returns_nothing(db_session, searchable):
    assert search_policies(db_session, FakeEmbedder(), "   ") == []


def test_an_unknown_intent_is_an_error(db_session, searchable):
    with pytest.raises(ValueError):
        search_policies(db_session, FakeEmbedder(), "cracked item", intent="refund_everything")
