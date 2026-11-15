"""Checks on the real policy files in backend/policies/."""

import pytest

from app.agent.policy_rules import (
    DAMAGE_REPORT_WINDOW_HOURS,
    LATE_DELIVERY_REFUND_AFTER_DAYS,
    REFUND_BANK_DAYS_MAX,
    REFUND_BANK_DAYS_MIN,
    REFUND_INITIATION_HOURS,
    WRONG_ITEM_REPORT_WINDOW_HOURS,
)
from app.services.policy_service import (
    POLICY_DIR,
    active_chunks,
    load_policies,
    parse_policy_file,
)


@pytest.fixture(scope="module")
def policies():
    files = sorted(POLICY_DIR.glob("*.md"))
    assert files, "no policy files found"
    return {p.slug: p for p in map(parse_policy_file, files)}


def text_of(policies, slug):
    return "\n".join(chunk.content for chunk in policies[slug].chunks)


def test_the_four_complaint_types_each_have_a_policy(policies):
    assert {p.applies_to for p in policies.values()} == {
        "late_delivery",
        "damaged_item",
        "wrong_item",
        "refund_status",
    }


def test_each_policy_has_several_sections(policies):
    for policy in policies.values():
        assert len(policy.chunks) >= 3, policy.slug


def test_numbers_in_the_text_match_the_rules_in_code(policies):
    assert f"{DAMAGE_REPORT_WINDOW_HOURS} hours" in text_of(policies, "damaged-item")
    assert f"{WRONG_ITEM_REPORT_WINDOW_HOURS} hours" in text_of(policies, "wrong-item")
    assert f"{LATE_DELIVERY_REFUND_AFTER_DAYS} or more days" in text_of(
        policies, "late-delivery"
    )
    refund = text_of(policies, "refund-timing")
    assert f"{REFUND_INITIATION_HOURS} hours" in refund
    assert f"{REFUND_BANK_DAYS_MIN} to {REFUND_BANK_DAYS_MAX} business days" in refund


def test_real_files_load_into_the_database(db_session):
    summary = load_policies(db_session)

    assert set(summary.added) == {
        "late-delivery",
        "damaged-item",
        "wrong-item",
        "refund-timing",
    }
    assert len(active_chunks(db_session, "damaged_item")) >= 3
