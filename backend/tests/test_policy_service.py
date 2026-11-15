"""Tests for the policy loader. They use the real test database."""

import pytest
from sqlalchemy import select

from app.models.policy import Policy
from app.services.policy_service import (
    PolicyFileError,
    PolicyVersionError,
    active_chunks,
    load_policies,
    parse_policy_text,
)


def policy_text(version=1, rule="Return within 7 days.", applies_to="damaged_item", slug="demo"):
    return (
        "---\n"
        f"slug: {slug}\n"
        f"applies_to: {applies_to}\n"
        f"version: {version}\n"
        "---\n"
        "# Demo policy\n"
        "\n"
        "## First section\n"
        f"{rule}\n"
        "\n"
        "## Second section\n"
        "Attach a photo.\n"
    )


def write_policy(directory, name, text):
    (directory / name).write_text(text, encoding="utf-8")


def test_parse_reads_header_title_and_sections():
    parsed = parse_policy_text(policy_text())

    assert parsed.slug == "demo"
    assert parsed.applies_to == "damaged_item"
    assert parsed.version == 1
    assert parsed.title == "Demo policy"
    assert [c.section for c in parsed.chunks] == ["First section", "Second section"]
    assert parsed.chunks[0].content == "Return within 7 days."


def test_parse_handles_windows_line_endings():
    unix = parse_policy_text(policy_text())
    windows = parse_policy_text(policy_text().replace("\n", "\r\n"))

    assert windows == unix


def test_parse_rejects_missing_header():
    with pytest.raises(PolicyFileError):
        parse_policy_text("# Title\n\n## Section\nText\n")


def test_parse_rejects_unknown_intent():
    with pytest.raises(PolicyFileError):
        parse_policy_text(policy_text(applies_to="refund_everything"))


@pytest.mark.parametrize("bad_version", ["abc", 0])
def test_parse_rejects_bad_version(bad_version):
    with pytest.raises(PolicyFileError):
        parse_policy_text(policy_text(version=bad_version))


def test_parse_rejects_file_without_sections():
    with pytest.raises(PolicyFileError):
        parse_policy_text("---\nslug: demo\napplies_to: other\nversion: 1\n---\n# Title\n")


def test_first_load_adds_chunks_in_order(db_session, tmp_path):
    write_policy(tmp_path, "demo.md", policy_text())

    summary = load_policies(db_session, tmp_path)

    assert summary.added == ("demo",)
    assert summary.unchanged == ()
    rows = active_chunks(db_session)
    assert [(r.chunk_index, r.section) for r in rows] == [
        (0, "First section"),
        (1, "Second section"),
    ]
    assert all(r.version == 1 and r.is_active for r in rows)
    assert all(len(r.content_hash) == 64 for r in rows)


def test_loading_twice_changes_nothing(db_session, tmp_path):
    write_policy(tmp_path, "demo.md", policy_text())
    load_policies(db_session, tmp_path)

    summary = load_policies(db_session, tmp_path)

    assert summary.added == ()
    assert summary.unchanged == ("demo",)
    assert len(db_session.scalars(select(Policy)).all()) == 2


def test_edit_without_version_bump_is_an_error_and_changes_nothing(db_session, tmp_path):
    write_policy(tmp_path, "demo.md", policy_text())
    load_policies(db_session, tmp_path)
    write_policy(tmp_path, "demo.md", policy_text(rule="Return within 30 days."))

    with pytest.raises(PolicyVersionError):
        load_policies(db_session, tmp_path)

    assert active_chunks(db_session)[0].content == "Return within 7 days."
    assert len(db_session.scalars(select(Policy)).all()) == 2


def test_version_bump_retires_old_rows(db_session, tmp_path):
    write_policy(tmp_path, "demo.md", policy_text())
    load_policies(db_session, tmp_path)
    write_policy(tmp_path, "demo.md", policy_text(version=2, rule="Return within 30 days."))

    summary = load_policies(db_session, tmp_path)

    assert summary.added == ("demo",)
    everything = db_session.scalars(select(Policy)).all()
    assert len(everything) == 4
    active = active_chunks(db_session)
    assert [r.version for r in active] == [2, 2]
    assert active[0].content == "Return within 30 days."
    old = [r for r in everything if r.version == 1]
    assert len(old) == 2
    assert not any(r.is_active for r in old)


def test_older_version_than_stored_is_an_error(db_session, tmp_path):
    write_policy(tmp_path, "demo.md", policy_text(version=2))
    load_policies(db_session, tmp_path)
    write_policy(tmp_path, "demo.md", policy_text(version=1))

    with pytest.raises(PolicyVersionError):
        load_policies(db_session, tmp_path)


def test_one_bad_file_means_nothing_is_loaded(db_session, tmp_path):
    write_policy(tmp_path, "a.md", policy_text())
    write_policy(tmp_path, "b.md", "no header here")

    with pytest.raises(PolicyFileError):
        load_policies(db_session, tmp_path)

    assert db_session.scalars(select(Policy)).all() == []


def test_two_files_with_the_same_slug_is_an_error(db_session, tmp_path):
    write_policy(tmp_path, "a.md", policy_text())
    write_policy(tmp_path, "b.md", policy_text())

    with pytest.raises(PolicyFileError):
        load_policies(db_session, tmp_path)


def test_empty_directory_is_an_error(db_session, tmp_path):
    with pytest.raises(PolicyFileError):
        load_policies(db_session, tmp_path)


def test_active_chunks_can_filter_by_intent(db_session, tmp_path):
    write_policy(tmp_path, "a.md", policy_text(slug="a", applies_to="damaged_item"))
    write_policy(tmp_path, "b.md", policy_text(slug="b", applies_to="wrong_item"))
    load_policies(db_session, tmp_path)

    assert {r.slug for r in active_chunks(db_session, "wrong_item")} == {"b"}
