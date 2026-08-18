"""
LLM generation layer.

Wraps the Groq-backed chat model, builds the final prompt (system prompt +
context + structured-output instructions), calls the model at low
temperature, and parses out the natural-language answer plus the
structured JSON block for Team C.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, asdict
from typing import Optional

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from src.config import GROQ_API_KEY, LLM_MODEL, LLM_TEMPERATURE
from src.prompts import build_system_prompt, build_structured_instructions

logger = logging.getLogger(__name__)

_llm = None


def get_llm() -> ChatGroq:
    global _llm
    if _llm is None:
        _llm = ChatGroq(
            api_key=GROQ_API_KEY,
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
        )
    return _llm


@dataclass
class StructuredAnswer:
    service: Optional[str] = None
    category: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    requirements: list = None
    steps: list = None
    fee: str = "Not specified in verified sources"
    processing_time: str = "Not specified in verified sources"
    office: str = "Not specified in verified sources"
    source_url: Optional[str] = None
    official_portals: list = None

    def __post_init__(self):
        self.requirements = self.requirements or []
        self.steps = self.steps or []
        self.official_portals = self.official_portals or []

    def to_dict(self) -> dict:
        return asdict(self)


_JSON_BLOCK_RE = re.compile(r"<<<JSON>>>(.*?)<<<END_JSON>>>", re.DOTALL)


def _split_answer_and_json(raw_text: str) -> tuple[str, StructuredAnswer]:
    """Separate the natural-language answer from the trailing JSON block."""
    match = _JSON_BLOCK_RE.search(raw_text)

    if not match:
        # Model didn't follow the format — return full text as the answer
        # and an empty structured object rather than crashing.
        logger.warning("No structured JSON block found in LLM output")
        return raw_text.strip(), StructuredAnswer()

    natural_language = raw_text[: match.start()].strip()
    json_str = match.group(1).strip()

    try:
        parsed = json.loads(json_str)
        structured = StructuredAnswer(
            service=parsed.get("service"),
            category=parsed.get("category"),
            state=parsed.get("state"),
            district=parsed.get("district"),
            requirements=parsed.get("requirements") or [],
            steps=parsed.get("steps") or [],
            fee=parsed.get("fee") or "Not specified in verified sources",
            processing_time=parsed.get("processing_time") or "Not specified in verified sources",
            office=parsed.get("office") or "Not specified in verified sources",
            source_url=parsed.get("source_url"),
            official_portals=parsed.get("official_portals") or [],
        )
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse structured JSON: %s", e)
        structured = StructuredAnswer()

    return natural_language, structured


def generate_answer(
    query: str,
    language: str,
    context: str,
    state: Optional[str],
    district: Optional[str],
) -> tuple[str, StructuredAnswer]:
    """
    Single LLM call that returns both the natural-language answer (in the
    citizen's language) and a structured JSON object for Team C, using the
    <<<JSON>>> marker convention so we can split them reliably.
    """
    system_prompt = build_system_prompt(
        language=language, context=context, state=state, district=district
    )
    system_prompt += "\n" + build_structured_instructions()

    llm = get_llm()
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=query),
    ]

    response = llm.invoke(messages)
    raw_text = response.content

    return _split_answer_and_json(raw_text)
