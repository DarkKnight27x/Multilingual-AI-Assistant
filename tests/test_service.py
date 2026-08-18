"""
Basic smoke tests. These do NOT require a live Groq key for the pure-logic
parts (frontmatter parsing, JSON splitting) but DO require one — and a
built vector index — for the full end-to-end `process_query` tests.

Run with: pytest tests/ -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from src.rag import _parse_frontmatter
from src.chain import _split_answer_and_json
from src.config import SUPPORTED_LANGUAGES, CATEGORIES


def test_frontmatter_parsing():
    raw = """---
service: Birth Certificate
state: Tamil Nadu
district: All
source_url: https://example.gov.in
---

## Body
Some content here.
"""
    meta, body = _parse_frontmatter(raw)
    assert meta["service"] == "Birth Certificate"
    assert meta["state"] == "Tamil Nadu"
    assert meta["source_url"] == "https://example.gov.in"
    assert "Some content here." in body


def test_frontmatter_missing_returns_whole_text():
    raw = "Just a plain markdown file with no frontmatter."
    meta, body = _parse_frontmatter(raw)
    assert meta == {}
    assert body == raw


def test_json_splitting_happy_path():
    raw_llm_output = (
        "Here is your answer about birth certificates...\n\n"
        "<<<JSON>>>\n"
        '{"service": "Birth Certificate", "category": "vital_records", '
        '"state": "Tamil Nadu", "district": "Chennai", '
        '"requirements": ["Hospital report"], "steps": ["1. Apply"], '
        '"fee": "Free", "processing_time": "7 days", "office": "Registrar", '
        '"source_url": "https://crsorgi.gov.in", "official_portals": []}\n'
        "<<<END_JSON>>>"
    )
    text, structured = _split_answer_and_json(raw_llm_output)
    assert "Here is your answer" in text
    assert structured.service == "Birth Certificate"
    assert structured.category == "vital_records"
    assert structured.requirements == ["Hospital report"]


def test_json_splitting_missing_json_block_does_not_crash():
    raw_llm_output = "Just a plain answer with no JSON block at all."
    text, structured = _split_answer_and_json(raw_llm_output)
    assert text == raw_llm_output
    assert structured.service is None
    assert structured.requirements == []


def test_config_sanity():
    assert "en" in SUPPORTED_LANGUAGES
    assert "ta" in SUPPORTED_LANGUAGES
    assert len(CATEGORIES) == 6
    assert "vital_records" in CATEGORIES


@pytest.mark.skip(reason="Requires GROQ_API_KEY and a built vector index — run manually")
def test_process_query_end_to_end():
    from src.service import process_query

    result = process_query(
        text="I need a birth certificate",
        language="en",
        session_id="pytest-1",
        state="Tamil Nadu",
        district="Chennai",
    )
    assert result["session_id"] == "pytest-1"
    assert result["language"] == "en"
    assert "response" in result
    assert "structured" in result
