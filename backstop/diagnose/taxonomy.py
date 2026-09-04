from backstop.models import Action, RootCause

REASON_MAP: dict[str, RootCause] = {
    # TRANSIENT_INFRA — retry works, cheapest wins in the system
    "gateway_technical_error": RootCause.TRANSIENT_INFRA,
    "server_error": RootCause.TRANSIENT_INFRA,
    "bank_not_available": RootCause.TRANSIENT_INFRA,
    "bank_technical_error": RootCause.TRANSIENT_INFRA,
    "bank_cutoff_in_progress": RootCause.TRANSIENT_INFRA,
    "request_timed_out": RootCause.TRANSIENT_INFRA,
    "psp_app_not_available": RootCause.TRANSIENT_INFRA,
    "psp_not_available": RootCause.TRANSIENT_INFRA,
    "upi_app_technical_error": RootCause.TRANSIENT_INFRA,
    "issuer_technical_error": RootCause.TRANSIENT_INFRA,
    "invalid_response_from_gateway": RootCause.TRANSIENT_INFRA,
    "payment_declined_due_to_high_traffic": RootCause.TRANSIENT_INFRA,
    "vpa_resolution_failed": RootCause.TRANSIENT_INFRA,

    # ISSUER_SOFT_DECLINE — recoverable, but time-shifted
    "insufficient_funds": RootCause.ISSUER_SOFT_DECLINE,
    "transaction_limit_exceeded": RootCause.ISSUER_SOFT_DECLINE,
    "transaction_daily_limit_exceeded": RootCause.ISSUER_SOFT_DECLINE,
    "transaction_daily_count_exceeded": RootCause.ISSUER_SOFT_DECLINE,
    "transaction_frequency_limit_exceeded": RootCause.ISSUER_SOFT_DECLINE,
    "credit_limit_exceeded": RootCause.ISSUER_SOFT_DECLINE,

    # AUTH_ABANDONED — nudge fast while intent is warm
    "authentication_failed": RootCause.AUTH_ABANDONED,
    "incorrect_otp": RootCause.AUTH_ABANDONED,
    "otp_expired": RootCause.AUTH_ABANDONED,
    "otp_attempts_exceeded": RootCause.AUTH_ABANDONED,
    "incorrect_cvv": RootCause.AUTH_ABANDONED,
    "incorrect_pin": RootCause.AUTH_ABANDONED,
    "payment_timed_out": RootCause.AUTH_ABANDONED,
    "payment_session_expired": RootCause.AUTH_ABANDONED,
    "payment_collect_request_expired": RootCause.AUTH_ABANDONED,

    # USER_ABORTED — one nudge, then stop. Chasing this is harassment.
    "payment_cancelled": RootCause.USER_ABORTED,

    # INSTRUMENT_TERMINAL — retrying is guaranteed to fail again
    "card_expired": RootCause.INSTRUMENT_TERMINAL,
    "card_number_invalid": RootCause.INSTRUMENT_TERMINAL,
    "incorrect_card_expiry_date": RootCause.INSTRUMENT_TERMINAL,
    "debit_instrument_blocked": RootCause.INSTRUMENT_TERMINAL,
    "debit_instrument_inactive": RootCause.INSTRUMENT_TERMINAL,
    "bank_account_invalid": RootCause.INSTRUMENT_TERMINAL,
    "invalid_vpa": RootCause.INSTRUMENT_TERMINAL,
    "transaction_on_vpa_restricted": RootCause.INSTRUMENT_TERMINAL,
    "card_declined": RootCause.INSTRUMENT_TERMINAL,

    # RAIL_INELIGIBLE — switch rail, don't retry
    "international_transaction_not_allowed": RootCause.RAIL_INELIGIBLE,
    "card_network_not_enabled": RootCause.RAIL_INELIGIBLE,
    "card_not_enrolled": RootCause.RAIL_INELIGIBLE,
    "user_not_registered_for_netbanking": RootCause.RAIL_INELIGIBLE,
    "upi_autopay_not_supported_on_psp": RootCause.RAIL_INELIGIBLE,
    "psp_app_not_supported": RootCause.RAIL_INELIGIBLE,
    "user_not_eligible": RootCause.RAIL_INELIGIBLE,

    # RISK_DECLINE — hard stop, human only
    "payment_risk_check_failed": RootCause.RISK_DECLINE,
    "compliance_violation": RootCause.RISK_DECLINE,
    "payment_amount_tampered": RootCause.RISK_DECLINE,

    # MERCHANT_CONFIG — this is the merchant's bug, not the customer's
    "input_validation_failed": RootCause.MERCHANT_CONFIG,
    "invalid_order_id": RootCause.MERCHANT_CONFIG,
    "order_amount_mismatch": RootCause.MERCHANT_CONFIG,
    "order_payment_method_mismatch": RootCause.MERCHANT_CONFIG,
    "order_already_paid": RootCause.MERCHANT_CONFIG,
    "payment_method_not_enabled": RootCause.MERCHANT_CONFIG,
    "bank_not_enabled": RootCause.MERCHANT_CONFIG,
    "live_mode_not_enabled": RootCause.MERCHANT_CONFIG,
    "invalid_amount": RootCause.MERCHANT_CONFIG,
    "invalid_currency": RootCause.MERCHANT_CONFIG,

    # MANDATE_FAILURE — RBI E-mandate Framework 2026 territory
    "mandate_creation_failed": RootCause.MANDATE_FAILURE,
    "mandate_creation_expired": RootCause.MANDATE_FAILURE,
    "mandate_creation_declined": RootCause.MANDATE_FAILURE,
    "mandate_creation_timeout": RootCause.MANDATE_FAILURE,
    "funds_blocked_by_mandate": RootCause.MANDATE_FAILURE,
    "reqauth_mandate_not_acknowledged": RootCause.MANDATE_FAILURE,
    "recurring_payment_not_enabled": RootCause.MANDATE_FAILURE,
}

# Retry can never fix these — the policy engine reads this set directly.
NEVER_RETRY = {
    RootCause.INSTRUMENT_TERMINAL,
    RootCause.RAIL_INELIGIBLE,
    RootCause.RISK_DECLINE,
    RootCause.MERCHANT_CONFIG,
}

# No automated action of any kind. Human review only.
HARD_STOP = {RootCause.RISK_DECLINE}

CAUSE_TO_CANDIDATE_ACTIONS: dict[RootCause, list[Action]] = {
    RootCause.TRANSIENT_INFRA: [Action.RETRY_SAME_RAIL, Action.SCHEDULE_FOLLOWUP],
    RootCause.ISSUER_SOFT_DECLINE: [Action.SCHEDULE_FOLLOWUP, Action.NUDGE_CHECKOUT, Action.RETRY_SAME_RAIL],
    RootCause.AUTH_ABANDONED: [Action.NUDGE_CHECKOUT, Action.SWITCH_RAIL_LINK],
    RootCause.USER_ABORTED: [Action.NUDGE_CHECKOUT, Action.NO_ACTION],
    RootCause.INSTRUMENT_TERMINAL: [Action.UPDATE_INSTRUMENT, Action.SWITCH_RAIL_LINK],
    RootCause.RAIL_INELIGIBLE: [Action.SWITCH_RAIL_LINK],
    RootCause.RISK_DECLINE: [Action.ESCALATE_HUMAN],
    RootCause.MERCHANT_CONFIG: [Action.ALERT_MERCHANT],
    RootCause.MANDATE_FAILURE: [Action.SCHEDULE_FOLLOWUP, Action.UPDATE_INSTRUMENT],
    RootCause.UNKNOWN: [Action.ESCALATE_HUMAN, Action.NO_ACTION],
}
