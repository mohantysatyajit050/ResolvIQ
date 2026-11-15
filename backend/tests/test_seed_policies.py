"""Tests for the policy seed script. They use the test database, not the dev one."""

from scripts.seed_policies import run


def test_run_loads_the_real_policy_files(db_session, capsys):
    assert run(db_session) == 0

    out = capsys.readouterr().out
    for slug in ("damaged-item", "late-delivery", "refund-timing", "wrong-item"):
        assert slug in out


def test_running_twice_adds_nothing_the_second_time(db_session, capsys):
    run(db_session)
    capsys.readouterr()

    assert run(db_session) == 0

    assert "Added or updated: none" in capsys.readouterr().out


def test_run_reports_a_problem_and_returns_1(db_session, tmp_path, capsys):
    # an empty folder has no policy files, so the load must fail cleanly
    assert run(db_session, tmp_path) == 1

    assert "Policy load failed" in capsys.readouterr().out
