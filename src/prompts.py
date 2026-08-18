"""
Prompt templates.

The single most important job of this file is to make hallucination
structurally unlikely: the model is only ever allowed to state facts that
appear in the retrieved context, and it must say so explicitly when it
doesn't know something.
"""

from src.config import CATEGORIES, LANGUAGE_INSTRUCTIONS, LANGUAGE_NAMES

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_CATEGORY_LIST = "\n".join(f"- {key}: {desc}" for key, desc in CATEGORIES.items())

SYSTEM_PROMPT_TEMPLATE = """You are "Nyaya Sahayak", a government-services assistant for Indian citizens,
used through both a phone helpline and a mobile app.

You help ONLY with these six categories of government services:
{category_list}

Anything outside these six categories (e.g. general chit-chat, unrelated topics,
medical/legal advice unrelated to these services) must be politely declined,
and the user should be redirected to ask about one of the six categories.

=== HARD RULES (never break these) ===
1. NEVER invent fees, office names, form numbers, eligibility criteria, or
   processing timelines. Only state what appears in the CONTEXT below.
2. If the CONTEXT does not contain the answer, say so honestly and point the
   citizen to the official portal(s) listed in the context (or, if none are
   present, say you don't have verified information and recommend visiting
   the nearest Common Service Centre / e-District portal).
3. If the citizen's state or district is missing AND the answer could vary
   by state, ASK for it before giving procedural specifics. You may still
   give general/central-government information if it is state-independent.
4. For welfare schemes specifically: always point the citizen to
   https://www.myscheme.gov.in for eligibility screening. Never invent a
   scheme name or benefit that is not in the CONTEXT.
5. Never fabricate a source_url. Only use source_url values present in the
   CONTEXT you were given.
6. Structure your natural-language answer as: brief explanation → numbered
   steps → documents required → where to apply → official link(s).
7. Keep the tone simple, respectful, and usable for someone with low
   digital literacy (this may be read aloud over a phone call).

=== LANGUAGE ===
{language_instruction}
Respond ONLY in {language_name}. Do not mix in English unless a term (like a
proper noun / portal name) has no natural translation.

=== CONTEXT (verified knowledge retrieved for this query) ===
{context}

=== CITIZEN LOCATION ===
State: {state}
District: {district}
"""


def build_system_prompt(language: str, context: str, state: str | None, district: str | None) -> str:
    """Assemble the full system prompt for a single turn."""
    lang_instruction = LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["en"])
    lang_name = LANGUAGE_NAMES.get(language, "English")

    return SYSTEM_PROMPT_TEMPLATE.format(
        category_list=_CATEGORY_LIST,
        language_instruction=lang_instruction,
        language_name=lang_name,
        context=context if context.strip() else "(no relevant verified information found)",
        state=state or "(not provided)",
        district=district or "(not provided)",
    )


# ---------------------------------------------------------------------------
# Structured-output extraction prompt (used after the natural language
# answer, or in the same call — see chain.py)
# ---------------------------------------------------------------------------

STRUCTURED_OUTPUT_INSTRUCTIONS = """
After your natural-language answer, also produce a STRICT JSON object
(and nothing else after it) matching exactly this shape:

{{
  "service": "<short service name or null if unclear>",
  "category": "<one of: {category_keys} or null>",
  "state": "<state or null>",
  "district": "<district or null>",
  "requirements": ["<document 1>", "<document 2>", "..."],
  "steps": ["1. ...", "2. ...", "..."],
  "fee": "<fee text from context, or 'Not specified in verified sources'>",
  "processing_time": "<from context, or 'Not specified in verified sources'>",
  "office": "<from context, or 'Not specified in verified sources'>",
  "source_url": "<primary source url from context, or null>",
  "official_portals": ["<url1>", "<url2>"]
}}

Only use information present in the CONTEXT. If a field is unknown, use
null (for strings) or an empty list (for arrays) — never invent a value.
Wrap the JSON between the markers <<<JSON>>> and <<<END_JSON>>> exactly.
"""


def build_structured_instructions() -> str:
    from src.config import CATEGORIES as _CATS

    return STRUCTURED_OUTPUT_INSTRUCTIONS.format(category_keys=", ".join(_CATS.keys()))


# ---------------------------------------------------------------------------
# Intent / location extraction prompt (used by conversation.py)
# ---------------------------------------------------------------------------

INTENT_EXTRACTION_PROMPT = """Given the citizen's message below, extract:
- intent: a short snake_case label for what service they want (e.g. "birth_certificate",
  "legal_heir_certificate", "income_certificate", "ration_card", "rti_filing"). Use null if unclear.
- category: one of {category_keys}, or null.
- state: an Indian state name if mentioned in the message itself, else null.
- district: a district name if mentioned in the message itself, else null.

Message: "{message}"

Respond with STRICT JSON only, no prose, no markdown fences:
{{"intent": "...", "category": "...", "state": null, "district": null}}
"""


def build_intent_prompt(message: str) -> str:
    from src.config import CATEGORIES as _CATS

    return INTENT_EXTRACTION_PROMPT.format(
        category_keys=", ".join(_CATS.keys()), message=message
    )


# ---------------------------------------------------------------------------
# Fallback strings (no LLM call needed for these)
# ---------------------------------------------------------------------------

FALLBACK_NO_CONTEXT = {
    "en": "I don't have verified information on this yet. Please check your state's e-District portal or visit the nearest Common Service Centre (CSC).",
    "hi": "मेरे पास इसकी सत्यापित जानकारी अभी उपलब्ध नहीं है। कृपया अपने राज्य के ई-डिस्ट्रिक्ट पोर्टल की जाँच करें या नज़दीकी कॉमन सर्विस सेंटर (CSC) पर जाएँ।",
    "ta": "இதற்கான சரிபார்க்கப்பட்ட தகவல் என்னிடம் இல்லை. உங்கள் மாநிலத்தின் இ-டிஸ்ட்ரிக்ட் போர்ட்டலைப் பார்க்கவும் அல்லது அருகிலுள்ள பொது சேவை மையத்தை (CSC) அணுகவும்.",
    "mr": "याबद्दल माझ्याकडे सत्यापित माहिती अद्याप नाही. कृपया तुमच्या राज्याचे ई-डिस्ट्रिक्ट पोर्टल तपासा किंवा जवळच्या कॉमन सर्व्हिस सेंटर (CSC) ला भेट द्या.",
    "ml": "ഇതിനെക്കുറിച്ച് സ്ഥിരീകരിച്ച വിവരം എന്റെ പക്കൽ ഇല്ല. ദയവായി നിങ്ങളുടെ സംസ്ഥാനത്തിന്റെ ഇ-ഡിസ്ട്രിക്ട് പോർട്ടൽ പരിശോധിക്കുക അല്ലെങ്കിൽ അടുത്തുള്ള കോമൺ സർവീസ് സെന്റർ (CSC) സന്ദർശിക്കുക.",
    "gu": "આ વિશે મારી પાસે ચકાસાયેલ માહિતી હજુ ઉપલબ્ધ નથી. કૃપા કરીને તમારા રાજ્યના ઈ-ડિસ્ટ્રિક્ટ પોર્ટલ તપાસો અથવા નજીકના કોમન સર્વિસ સેન્ટર (CSC) ની મુલાકાત લો.",
}


def get_fallback(language: str) -> str:
    return FALLBACK_NO_CONTEXT.get(language, FALLBACK_NO_CONTEXT["en"])
