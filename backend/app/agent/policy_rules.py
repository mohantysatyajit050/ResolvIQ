"""Numbers from the store policies that the decision code uses.

The policy files in backend/policies/ state the same numbers in words.
tests/test_policy_files.py checks that the two agree, so they cannot drift apart.
"""

DAMAGE_REPORT_WINDOW_HOURS = 24
WRONG_ITEM_REPORT_WINDOW_HOURS = 48
LATE_DELIVERY_REFUND_AFTER_DAYS = 3
REFUND_INITIATION_HOURS = 12
REFUND_BANK_DAYS_MIN = 5
REFUND_BANK_DAYS_MAX = 7
