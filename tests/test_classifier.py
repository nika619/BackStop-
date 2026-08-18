from datetime import datetime, timezone

from backstop.diagnose.classifier import classify
from backstop.models import PaymentEvent, RootCause


def test_classifier_exact_matches_standard_reasons():
    event = PaymentEvent(
        event_id="evt_cls_01",
        payment_id="pay_cls_01",
        customer_ref="cust_cls",
        amount_paise=99900,
        error_reason="insufficient_funds",
        failed_at=datetime.now(timezone.utc),
    )
    cause, confidence, evidence = classify(event)
    assert cause == RootCause.ISSUER_SOFT_DECLINE
    assert confidence == 1.0
    assert "exact_map" in evidence[0]


def test_classifier_identifies_merchant_defect():
    event = PaymentEvent(
        event_id="evt_cls_02",
        payment_id="pay_cls_02",
        customer_ref="cust_cls",
        amount_paise=99900,
        error_reason="input_validation_failed",
        failed_at=datetime.now(timezone.utc),
    )
    cause, confidence, evidence = classify(event)
    assert cause == RootCause.MERCHANT_CONFIG
    assert confidence == 1.0


def test_classifier_heuristic_fallback_on_unmapped_source():
    event = PaymentEvent(
        event_id="evt_cls_03",
        payment_id="pay_cls_03",
        customer_ref="cust_cls",
        amount_paise=99900,
        error_reason="some_custom_random_code",
        error_source="business",
        failed_at=datetime.now(timezone.utc),
    )
    cause, confidence, evidence = classify(event)
    assert cause == RootCause.MERCHANT_CONFIG
    assert confidence == 0.6
