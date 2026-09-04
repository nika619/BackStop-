"""
Tests for backstop.diagnose.classifier — covering exact-map, source heuristics,
and free-text heuristic fallback branches (no live Gemini call needed).
"""
import pytest
from datetime import datetime, timezone
from backstop.models import PaymentEvent, RootCause
from backstop.diagnose.classifier import classify, llm_classify_free_text


def make_event(error_reason=None, error_source=None, error_description=None):
    return PaymentEvent(
        event_id="evt_cls_01",
        payment_id="pay_cls_01",
        customer_ref="cust_cls_01",
        amount_paise=99900,
        failed_at=datetime.now(timezone.utc),
        error_reason=error_reason,
        error_source=error_source,
        error_description=error_description,
    )


# --- Exact REASON_MAP coverage ---

def test_classify_insufficient_funds_maps_to_issuer_soft_decline():
    event = make_event(error_reason="insufficient_funds")
    cause, confidence, evidence = classify(event)
    assert cause == RootCause.ISSUER_SOFT_DECLINE
    assert confidence == 1.0
    assert any("exact_map" in e for e in evidence)


def test_classify_card_expired_maps_to_instrument_terminal():
    event = make_event(error_reason="card_expired")
    cause, confidence, _ = classify(event)
    assert cause == RootCause.INSTRUMENT_TERMINAL
    assert confidence == 1.0


def test_classify_payment_risk_check_maps_to_risk_decline():
    event = make_event(error_reason="payment_risk_check_failed")
    cause, confidence, _ = classify(event)
    assert cause == RootCause.RISK_DECLINE
    assert confidence == 1.0


def test_classify_gateway_error_maps_to_transient_infra():
    event = make_event(error_reason="gateway_technical_error")
    cause, confidence, _ = classify(event)
    assert cause == RootCause.TRANSIENT_INFRA
    assert confidence == 1.0


def test_classify_auth_failed_maps_to_auth_abandoned():
    event = make_event(error_reason="authentication_failed")
    cause, confidence, _ = classify(event)
    assert cause == RootCause.AUTH_ABANDONED
    assert confidence == 1.0


def test_classify_invalid_vpa_maps_to_instrument_terminal():
    event = make_event(error_reason="invalid_vpa")
    cause, confidence, _ = classify(event)
    assert cause == RootCause.INSTRUMENT_TERMINAL
    assert confidence == 1.0


# --- Source-based deterministic fallback ---

def test_classify_business_source_maps_to_merchant_config():
    event = make_event(error_reason="unmapped_reason_xyz", error_source="business")
    cause, confidence, evidence = classify(event)
    assert cause == RootCause.MERCHANT_CONFIG
    assert 0.5 <= confidence <= 0.7
    assert any("source" in e for e in evidence)


def test_classify_gateway_source_maps_to_transient_infra():
    event = make_event(error_reason="unmapped_reason_xyz", error_source="gateway")
    cause, confidence, _ = classify(event)
    assert cause == RootCause.TRANSIENT_INFRA


def test_classify_razorpay_source_maps_to_transient_infra():
    event = make_event(error_reason="unmapped_reason_xyz", error_source="razorpay")
    cause, confidence, _ = classify(event)
    assert cause == RootCause.TRANSIENT_INFRA


# --- Free-text heuristic fallback (no Gemini key needed) ---

def test_free_text_timeout_keyword_maps_to_transient_infra(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    cause, confidence, _ = llm_classify_free_text("server timeout on payment gateway")
    assert cause == RootCause.TRANSIENT_INFRA
    assert confidence >= 0.7


def test_free_text_balance_keyword_maps_to_issuer_soft_decline(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    cause, confidence, _ = llm_classify_free_text("insufficient balance in account")
    assert cause == RootCause.ISSUER_SOFT_DECLINE


def test_free_text_otp_keyword_maps_to_auth_abandoned(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    cause, confidence, _ = llm_classify_free_text("customer did not enter otp")
    assert cause == RootCause.AUTH_ABANDONED


def test_free_text_expired_keyword_maps_to_instrument_terminal(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    cause, confidence, _ = llm_classify_free_text("expired card used")
    assert cause == RootCause.INSTRUMENT_TERMINAL


def test_free_text_fraud_keyword_maps_to_risk_decline(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    cause, confidence, _ = llm_classify_free_text("suspicious fraud risk detected")
    assert cause == RootCause.RISK_DECLINE
    assert confidence >= 0.8


def test_free_text_empty_description_returns_unknown(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    cause, _, _ = llm_classify_free_text(None)
    assert cause == RootCause.UNKNOWN


def test_free_text_unrecognised_returns_unknown(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    cause, confidence, _ = llm_classify_free_text("some completely unrecognised payment failure")
    assert cause == RootCause.UNKNOWN
    assert confidence <= 0.5
