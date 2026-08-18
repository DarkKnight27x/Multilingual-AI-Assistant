"""
Sample queries covering different categories, languages, and the
missing-location flow. Run after build_index.py:

    python scripts/test_query.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.service import process_query  # noqa: E402

TEST_CASES = [
    # (text, language, session_id, state, district)
    ("I need a birth certificate", "en", "test-1", "Tamil Nadu", "Chennai"),
    ("How to get income certificate", "hi", "test-2", "Maharashtra", "Pune"),
    ("legal heir certificate apply pannuvathu eppadi", "ta", "test-3", None, None),
    ("How do I file an RTI application?", "en", "test-4", None, None),
    ("ration card apply cheyyendathu engane", "ml", "test-5", "Kerala", None),
    ("Udyam registration process for small business", "en", "test-6", "Gujarat", None),
]

if __name__ == "__main__":
    for text, lang, sid, state, district in TEST_CASES:
        print("=" * 80)
        print(f"QUERY: {text} | lang={lang} | state={state} | district={district}")
        result = process_query(text, lang, sid, state, district)
        print(json.dumps(result, indent=2, ensure_ascii=False))
