"""
Lightweight conversation / session engine.

We deliberately keep this simple for the 1-week MVP: an in-memory dict of
session_id -> SessionState. No DB, no Redis. Swap the store implementation
later if sessions need to survive a restart or scale across workers.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from src.config import CATEGORIES
from src.prompts import build_intent_prompt

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    session_id: str
    language: str = "en"
    state: Optional[str] = None
    district: Optional[str] = None
    intent: Optional[str] = None
    category: Optional[str] = None
    missing: list = field(default_factory=list)
    turns: int = 0


# In-memory session store. key: session_id
_SESSIONS: dict[str, SessionState] = {}


def get_or_create_session(session_id: str, language: str) -> SessionState:
    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = SessionState(session_id=session_id, language=language)
    session = _SESSIONS[session_id]
    session.language = language  # language can change turn to turn per Team A
    return session


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def extract_intent_and_location(message: str, llm_call) -> dict:
    """
    Ask the LLM to pull out intent/category/state/district from raw text.
    `llm_call` is injected (a callable str -> str) so this stays testable
    without importing chain.py's network-touching client directly.
    """
    prompt = build_intent_prompt(message)
    raw = llm_call(prompt)

    match = _JSON_RE.search(raw)
    if not match:
        logger.warning("Intent extraction returned no JSON: %s", raw)
        return {"intent": None, "category": None, "state": None, "district": None}

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        logger.warning("Intent extraction JSON parse failed: %s", raw)
        return {"intent": None, "category": None, "state": None, "district": None}


def update_session_from_request(
    session: SessionState,
    request_state: Optional[str],
    request_district: Optional[str],
    extracted: dict,
) -> None:
    """
    Merge location/intent info from (in priority order):
      1. explicit fields on the /converse request (Team C sends these from
         device GPS / user profile — most trustworthy)
      2. values extracted from the free-text message itself
      3. whatever was already known from earlier turns in this session
    """
    session.state = request_state or extracted.get("state") or session.state
    session.district = request_district or extracted.get("district") or session.district

    if extracted.get("intent"):
        session.intent = extracted["intent"]
    if extracted.get("category") in CATEGORIES:
        session.category = extracted["category"]

    session.turns += 1


def compute_missing_fields(session: SessionState) -> list[str]:
    """
    Decide what we still need before we can give a state-specific answer.
    We only *require* the state (district is nice-to-have, not blocking) —
    keeps the phone-call flow short.
    """
    missing = []
    if not session.state:
        missing.append("state")
    session.missing = missing
    return missing


ASK_FOR_STATE = {
    "en": "Which state are you in? This helps me give you the correct procedure.",
    "hi": "आप किस राज्य में हैं? इससे मुझे सही प्रक्रिया बताने में मदद मिलेगी।",
    "ta": "நீங்கள் எந்த மாநிலத்தில் இருக்கிறீர்கள்? இது சரியான செயல்முறையை தெரிவிக்க உதவும்.",
    "mr": "तुम्ही कोणत्या राज्यात आहात? यामुळे मला योग्य प्रक्रिया सांगण्यास मदत होईल.",
    "ml": "നിങ്ങൾ ഏത് സംസ്ഥാനത്താണ്? ഇത് ശരിയായ നടപടിക്രമം അറിയിക്കാൻ എന്നെ സഹായിക്കും.",
    "gu": "તમે કયા રાજ્યમાં છો? આનાથી મને સાચી પ્રક્રિયા જણાવવામાં મદદ મળશે.",
}


def ask_for_missing(language: str) -> str:
    return ASK_FOR_STATE.get(language, ASK_FOR_STATE["en"])
# Categories that usually need state before giving full local procedure
STATE_DEPENDENT_CATEGORIES = {
    "vital_records",
    "property_inheritance",
    "income_caste_domicile",
    "welfare_schemes",
}

# Categories that can often answer without state (central processes)
STATE_OPTIONAL_CATEGORIES = {
    "business_trade",  # Udyam / GST are central
    "grievances",      # RTI Online / CPGRAMS are central
}


def needs_state(category: Optional[str]) -> bool:
    """
    Return True if we should ask for state before giving a full answer.
    """
    if not category:
        return True  # unknown category → safer to ask
    if category in STATE_OPTIONAL_CATEGORIES:
        return False
    if category in STATE_DEPENDENT_CATEGORIES:
        return True
    return True