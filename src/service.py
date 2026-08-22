"""
Orchestration layer: this is what api.py calls for every /converse request.

Flow:
    query -> extract intent + location -> merge with session/request ->
    retrieve (location-first) -> LLM generate -> natural language + structured
"""

from __future__ import annotations
from src.portal_map import get_official_portals
import logging
from typing import Optional

from src.conversation import (
    ChatMessage,
    get_or_create_session,
    extract_intent_and_location,
    update_session_from_request,
    ask_for_missing,
    needs_state,
)
from src.rag import retrieve, format_context
from src.chain import generate_answer, get_llm, StructuredAnswer
from src.prompts import get_fallback
from src.config import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)


def _cheap_llm_call(prompt: str) -> str:
    """Small helper so conversation.extract_intent_and_location can make a
    raw text-in/text-out call without importing ChatGroq message types."""
    from langchain_core.messages import HumanMessage

    llm = get_llm()
    resp = llm.invoke([HumanMessage(content=prompt)])
    return resp.content


def _add_assistant_message(session, response: str) -> None:
    session.history.append(
        ChatMessage(role="assistant", content=response)
    )


def process_query(
    text: str,
    language: str,
    session_id: str,
    state: Optional[str] = None,
    district: Optional[str] = None,
) -> dict:
    """
    Main entry point used by POST /converse.
    Never raises for normal failure modes — always returns a usable response.
    """
    language = language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE

    session = get_or_create_session(session_id, language)

    session.history.append(
        ChatMessage(role="user", content=text)
    )

    try:
        extracted = extract_intent_and_location(text, _cheap_llm_call)
    except Exception as e:
        logger.error("Intent extraction failed: %s", e)
        extracted = {"intent": None, "category": None, "state": None, "district": None}

    update_session_from_request(session, state, district, extracted)

    effective_state = session.state
    effective_district = session.district
    effective_category = session.category

    # --- Step 1: official portal router ---
    official_portals = get_official_portals(
        category=effective_category,
        state=effective_state,
    )

    # --------------------------------------------------
    # Strict ask-for-state
    # --------------------------------------------------
    if not effective_state and needs_state(effective_category):
        response = ask_for_missing(language)

        _add_assistant_message(session, response)

        return {
            "response": response,
            "language": language,
            "session_id": session_id,
            "structured": {
                "service": extracted.get("intent"),
                "category": effective_category,
                "state": None,
                "district": effective_district,
                "requirements": [],
                "steps": [],
                "fee": "Not specified in verified sources",
                "processing_time": "Not specified in verified sources",
                "office": "Not specified in verified sources",
                "source_url": official_portals[0] if official_portals else None,
                "official_portals": official_portals,
            },
        }

    try:
        chunks = retrieve(
            query=text,
            state=effective_state,
            district=effective_district,
            category=effective_category,
        )
        context = format_context(chunks)
    except Exception as e:
        logger.error("Retrieval failed: %s", e)
        chunks, context = [], ""

    if not context:
        fallback = get_fallback(language)

        _add_assistant_message(session, fallback)

        return {
            "response": fallback,
            "language": language,
            "session_id": session_id,
            "structured": {
                "service": None,
                "category": effective_category,
                "state": effective_state,
                "district": effective_district,
                "requirements": [],
                "steps": [],
                "fee": "Not specified in verified sources",
                "processing_time": "Not specified in verified sources",
                "office": "Not specified in verified sources",
                "source_url": official_portals[0] if official_portals else None,
                "official_portals": official_portals,
            },
        }

    try:
        natural_language, structured = generate_answer(
            query=text,
            language=language,
            context=context,
            state=effective_state,
            district=effective_district,
        )
    except Exception as e:
        logger.error("LLM generation failed: %s", e)

        fallback = get_fallback(language)

        _add_assistant_message(session, fallback)

        return {
            "response": fallback,
            "language": language,
            "session_id": session_id,
            "structured": {
                "service": None,
                "category": effective_category,
                "state": effective_state,
                "district": effective_district,
                "requirements": [],
                "steps": [],
                "fee": "Not specified in verified sources",
                "processing_time": "Not specified in verified sources",
                "office": "Not specified in verified sources",
                "source_url": official_portals[0] if official_portals else None,
                "official_portals": official_portals,
            },
        }

    if not natural_language:
        natural_language = get_fallback(language)

    _add_assistant_message(session, natural_language)

    # Merge router portals into structured output
    structured_dict = structured.to_dict()
    existing = structured_dict.get("official_portals") or []
    merged = list(dict.fromkeys(existing + official_portals))
    structured_dict["official_portals"] = merged

    if not structured_dict.get("source_url") and merged:
        structured_dict["source_url"] = merged[0]

    # Keep category/state if model left them empty
    if not structured_dict.get("category"):
        structured_dict["category"] = effective_category
    if not structured_dict.get("state"):
        structured_dict["state"] = effective_state
    if not structured_dict.get("district"):
        structured_dict["district"] = effective_district

    return {
        "response": natural_language,
        "language": language,
        "session_id": session_id,
        "structured": structured_dict,
    }