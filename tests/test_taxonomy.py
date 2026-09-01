import pytest
from backstop.models import RootCause, Action
from backstop.diagnose.taxonomy import REASON_MAP, NEVER_RETRY, HARD_STOP, CAUSE_TO_CANDIDATE_ACTIONS


def test_every_reason_maps_to_valid_root_cause():
    for reason, root_cause in REASON_MAP.items():
        assert isinstance(root_cause, RootCause)
        assert root_cause != RootCause.UNKNOWN


def test_never_retry_contains_terminal_and_risk_causes():
    assert RootCause.INSTRUMENT_TERMINAL in NEVER_RETRY
    assert RootCause.RAIL_INELIGIBLE in NEVER_RETRY
    assert RootCause.RISK_DECLINE in NEVER_RETRY
    assert RootCause.MERCHANT_CONFIG in NEVER_RETRY


def test_hard_stop_contains_risk_decline():
    assert RootCause.RISK_DECLINE in HARD_STOP
    assert RootCause.TRANSIENT_INFRA not in HARD_STOP


def test_every_root_cause_has_candidate_actions():
    for root_cause in RootCause:
        assert root_cause in CAUSE_TO_CANDIDATE_ACTIONS
        actions = CAUSE_TO_CANDIDATE_ACTIONS[root_cause]
        assert len(actions) > 0
        for action in actions:
            assert isinstance(action, Action)
