import os
import logging
from backstop.models import RootCause, PaymentEvent
from backstop.diagnose.taxonomy import REASON_MAP

logger = logging.getLogger(__name__)


def llm_classify_free_text(description: str | None) -> tuple[RootCause, float, list[str]]:
    """
    LLM fallback reserved for unmapped free-text error descriptions (~2% of cases).
    Uses Google Gemini API when configured, or deterministic fallback.
    """
    if not description:
        return RootCause.UNKNOWN, 0.0, ["unmapped: empty description"]

    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        desc_lower = description.lower()
        if any(w in desc_lower for w in ["timeout", "server", "gateway", "network", "bank down"]):
            return RootCause.TRANSIENT_INFRA, 0.7, ["heuristics: free-text infra pattern"]
        if any(w in desc_lower for w in ["balance", "funds", "limit"]):
            return RootCause.ISSUER_SOFT_DECLINE, 0.7, ["heuristics: free-text balance pattern"]
        if any(w in desc_lower for w in ["otp", "pin", "cvv", "abandon"]):
            return RootCause.AUTH_ABANDONED, 0.7, ["heuristics: free-text auth pattern"]
        if any(w in desc_lower for w in ["expired", "invalid card", "blocked"]):
            return RootCause.INSTRUMENT_TERMINAL, 0.7, ["heuristics: free-text terminal pattern"]
        if any(w in desc_lower for w in ["fraud", "risk", "suspicious", "tamper"]):
            return RootCause.RISK_DECLINE, 0.85, ["heuristics: free-text risk pattern"]
        return RootCause.UNKNOWN, 0.3, ["heuristics: unclassified free-text"]

    try:
        from google import genai
        client = genai.Client(api_key=gemini_key)
        prompt = (
            f"Classify this payment failure description into one of: "
            f"transient_infra, issuer_soft_decline, auth_abandoned, user_aborted, "
            f"instrument_terminal, rail_ineligible, risk_decline, merchant_config, mandate_failure, unknown.\n"
            f"Description: {description}\n"
            f"Respond with only the exact enum string."
        )
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        response = client.models.generate_content(model=model_name, contents=prompt)
        text = response.text.strip().lower()
        for cause in RootCause:
            if cause.value == text or cause.value in text:
                return cause, 0.85, [f"gemini_llm: {text}"]
        return RootCause.UNKNOWN, 0.4, ["gemini_llm: unmapped response"]
    except Exception as e:
        logger.warning(f"Gemini classification fallback error: {e}")
        return RootCause.UNKNOWN, 0.2, [f"gemini_llm_error: {str(e)}"]


def classify(event: PaymentEvent) -> tuple[RootCause, float, list[str]]:
    """
    Tiered classification:
    1. Exact match against Razorpay REASON_MAP (O(1), deterministic, 1.0 confidence)
    2. Source / step heuristics fallback (deterministic, 0.5 - 0.6 confidence)
    3. Gemini LLM fallback on unmapped free-text description
    """
    reason = (event.error_reason or "").strip().lower()
    if reason in REASON_MAP:
        return REASON_MAP[reason], 1.0, [f"exact_map: {reason}"]

    # Source-based deterministic fallback before invoking any model
    if event.error_source == "business":
        return RootCause.MERCHANT_CONFIG, 0.6, ["source: business"]
    if event.error_source in {"gateway", "razorpay"}:
        return RootCause.TRANSIENT_INFRA, 0.5, [f"source: {event.error_source}"]

    # Free text fallback
    return llm_classify_free_text(event.error_description)
