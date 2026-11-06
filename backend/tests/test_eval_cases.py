from collections import Counter

from app.models.ticket import TicketIntent, TicketPriority
from evals.intent_cases import CASES


def test_there_are_at_least_30_cases():
    assert len(CASES) >= 30


def test_case_ids_are_unique():
    ids = [c["id"] for c in CASES]
    assert len(ids) == len(set(ids))


def test_values_match_the_real_enums():
    intents = {i.value for i in TicketIntent}
    priorities = {p.value for p in TicketPriority}
    for c in CASES:
        assert set(c["intents"]) <= intents, c["id"]
        assert c["priority"] in priorities, c["id"]
        assert set(c["forbid"]) <= priorities, c["id"]
        assert c["text"].strip(), c["id"]


def test_every_tag_has_at_least_3_cases():
    counts = Counter(c["tag"] for c in CASES)
    assert all(n >= 3 for n in counts.values()), counts
