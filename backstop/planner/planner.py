import json
import logging
import os
import re
from typing import Any

from backstop.models import Action, Case, PaymentEvent
from backstop.planner.prompt import SYSTEM_PROMPT
from backstop.planner.redact import redact

logger = logging.getLogger(__name__)


def strip_fences(text: str) -> str:
    """Strip markdown code fences if model accidentally emitted them."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


def safest(permitted: frozenset[Action]) -> Action:
    """
    Monotonic fallback ladder toward inaction.
    Under uncertainty or model errors, a recovery engine always degrades toward less action.
    """
    for candidate in (Action.NO_ACTION, Action.SCHEDULE_FOLLOWUP, Action.ESCALATE_HUMAN):
        if candidate in permitted:
            return candidate
    return next(iter(permitted)) if permitted else Action.NO_ACTION


def call_gemini(system_instruction: str, user_content: str) -> str:
    """Call Google Gemini API."""
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        raise ValueError("GEMINI_API_KEY is not set")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=gemini_key)
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=0.1,
        response_mime_type="application/json",
    )
    response = client.models.generate_content(
        model=model_name,
        contents=user_content,
        config=config,
    )
    return response.text


def heuristic_plan(case: Case, permitted: frozenset[Action]) -> tuple[Action, dict[str, Any]]:
    """Deterministic fallback planner when Gemini API is offline or unconfigured."""
    if not permitted or Action.NO_ACTION in permitted and len(permitted) == 1:
        return Action.NO_ACTION, {"reason": "policy restricted to no action", "delay_hours": 0, "message_tone": "neutral"}

    # Intelligent deterministic priority based on root cause
    priority_order = [
        Action.RETRY_SAME_RAIL,
        Action.NUDGE_CHECKOUT,
        Action.SWITCH_RAIL_LINK,
        Action.UPDATE_INSTRUMENT,
        Action.SCHEDULE_FOLLOWUP,
        Action.ALERT_MERCHANT,
        Action.ESCALATE_HUMAN,
        Action.NO_ACTION,
    ]
    for act in priority_order:
        if act in permitted:
            return act, {
                "action": act.value,
                "reason": f"deterministic policy match for {case.root_cause.value}",
                "delay_hours": 0 if act == Action.RETRY_SAME_RAIL else 2,
                "message_tone": "neutral",
                "mode": "deterministic_heuristic",
            }

    return safest(permitted), {"reason": "heuristic default", "delay_hours": 0, "message_tone": "neutral"}


def plan(case: Case, event: PaymentEvent, permitted: frozenset[Action]) -> tuple[Action, dict[str, Any]]:
    """
    Plan the next recovery action.
    1. Redacts PII from case & event.
    2. Calls Google Gemini API with schema validation.
    3. Retries once if invalid.
    4. Falls back monotonically to safest(permitted).
    """
    if not permitted:
        return Action.NO_ACTION, {"reason": "empty permitted set", "delay_hours": 0, "message_tone": "neutral"}

    if len(permitted) == 1 and Action.NO_ACTION in permitted:
        return Action.NO_ACTION, {"reason": "only no_action permitted by policy", "delay_hours": 0, "message_tone": "neutral"}

    payload = redact(case, event, permitted)
    payload_str = json.dumps(payload, indent=2)

    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        return heuristic_plan(case, permitted)

    for attempt in range(2):
        try:
            raw_response = call_gemini(SYSTEM_PROMPT, payload_str)
            clean_json = strip_fences(raw_response)
            data = json.loads(clean_json)

            action_str = data.get("action")
            action = Action(action_str)

            if action not in permitted:
                raise ValueError(f"Model proposed action '{action_str}' which is NOT in permitted set: {[a.value for a in permitted]}")

            return action, data

        except Exception as e:
            logger.warning(f"Planner attempt #{attempt + 1} failed: {e}")
            if attempt == 1:
                # Fall back to safest permitted action on exhaustion
                safe_choice = safest(permitted)
                return safe_choice, {
                    "action": safe_choice.value,
                    "reason": f"Fallback to safest action after planner error: {e!s}",
                    "delay_hours": 0,
                    "message_tone": "neutral",
                    "fallback": True,
                }

    safe_choice = safest(permitted)
    return safe_choice, {"action": safe_choice.value, "reason": "Planner safety fallback", "delay_hours": 0, "message_tone": "neutral"}
