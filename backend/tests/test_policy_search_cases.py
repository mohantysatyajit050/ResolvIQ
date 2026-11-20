"""Checks on the policy search cases themselves (the search is not run here)."""

from app.models.ticket import TicketIntent
from app.services.policy_service import POLICY_DIR, parse_policy_file
from evals.policy_search_cases import ALL_CASES


def real_chunks():
    """Every chunk in the real policy files: 'slug/Section' -> the intent it applies to."""
    found = {}
    for path in sorted(POLICY_DIR.glob("*.md")):
        policy = parse_policy_file(path)
        for chunk in policy.chunks:
            found[f"{policy.slug}/{chunk.section}"] = policy.applies_to
    return found


def test_case_ids_are_unique():
    ids = [case.id for case in ALL_CASES]

    assert len(ids) == len(set(ids))


def test_every_intent_is_a_real_ticket_intent():
    valid = {intent.value for intent in TicketIntent}

    assert all(case.intent in valid for case in ALL_CASES)


def test_every_expected_chunk_exists_and_matches_the_intent():
    chunks = real_chunks()

    for case in ALL_CASES:
        assert case.expected in chunks, f"{case.id}: no such chunk {case.expected}"
        assert chunks[case.expected] == case.intent, f"{case.id}: intent does not match the policy"


def test_every_case_has_a_question_and_a_tag():
    assert all(case.query.strip() and case.tag for case in ALL_CASES)


def test_cases_cover_english_and_hinglish():
    tags = {case.tag for case in ALL_CASES}

    assert {"english", "hinglish"} <= tags
