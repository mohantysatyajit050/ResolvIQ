"""Tests for the policy seed script. They use the fake embedder and the test database."""

from sqlalchemy import func, select

from app.agent.embeddings import FakeEmbedder
from app.models.policy import Policy
from scripts.seed_policies import run


def test_run_loads_and_embeds_the_real_policy_files(db_session, capsys):
    assert run(db_session, FakeEmbedder()) == 0

    out = capsys.readouterr().out
    for slug in ("damaged-item", "late-delivery", "refund-timing", "wrong-item"):
        assert slug in out
    total = db_session.scalar(select(func.count()).select_from(Policy))
    embedded = db_session.scalar(
        select(func.count()).select_from(Policy).where(Policy.embedding.is_not(None))
    )
    assert total > 0
    assert embedded == total


def test_running_twice_adds_and_embeds_nothing_the_second_time(db_session, capsys):
    run(db_session, FakeEmbedder())
    capsys.readouterr()

    assert run(db_session, FakeEmbedder()) == 0

    out = capsys.readouterr().out
    assert "Added or updated: none" in out
    assert "Embedded chunks: 0" in out


def test_run_reports_a_problem_and_returns_1(db_session, tmp_path, capsys):
    # an empty folder has no policy files, so the load must fail cleanly
    assert run(db_session, FakeEmbedder(), tmp_path) == 1

    assert "Policy load failed" in capsys.readouterr().out
