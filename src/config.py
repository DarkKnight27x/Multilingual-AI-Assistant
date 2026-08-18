"""
Central configuration for Team B's RAG + LLM backend.

Everything that other modules need to agree on (languages, categories,
model names, paths) lives here so there is exactly one source of truth.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_BASE_DIR = BASE_DIR / "data" / "knowledge_base"
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", str(BASE_DIR / "chroma_db"))

# ---------------------------------------------------------------------------
# LLM / embeddings
# ---------------------------------------------------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.15"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")

# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# ---------------------------------------------------------------------------
# Languages (Team A does detection/speech; we just have to respect the code)
# ---------------------------------------------------------------------------
SUPPORTED_LANGUAGES = ["en", "hi", "ta", "mr", "ml", "gu"]

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "mr": "Marathi",
    "ml": "Malayalam",
    "gu": "Gujarati",
}

# Injected straight into the system prompt so the LLM knows exactly which
# language to answer in, in its own script.
LANGUAGE_INSTRUCTIONS = {
    "en": "Respond fully in English.",
    "hi": "उत्तर पूरी तरह हिंदी में दें (Devanagari script).",
    "ta": "பதிலை முழுவதுமாக தமிழில் மட்டும் கொடுங்கள் (Tamil script).",
    "mr": "उत्तर पूर्णपणे मराठीत द्या (Devanagari script).",
    "ml": "മറുപടി പൂർണ്ണമായും മലയാളത്തിൽ നൽകുക (Malayalam script).",
    "gu": "જવાબ સંપૂર્ણપણે ગુજરાતીમાં આપો (Gujarati script).",
}

DEFAULT_LANGUAGE = "en"

# ---------------------------------------------------------------------------
# Service categories (tag every knowledge chunk with one of these)
# ---------------------------------------------------------------------------
CATEGORIES = {
    "vital_records": "Vital records (birth, death, marriage certificates)",
    "property_inheritance": "Property & inheritance (legal heir, mutation, succession certificate)",
    "income_caste_domicile": "Income, caste & domicile certificates",
    "business_trade": "Business & trade (Udyam, trade license, GST registration)",
    "welfare_schemes": "Welfare schemes & pensions (ration card, pension, disability certificate)",
    "grievances": "Grievances & complaints (RTI, grievance redressal, consumer complaints)",
}

# Week 1 priority — used to order retrieval / fallback messaging, not to hard block.
PRIORITY_CATEGORIES = ["vital_records", "property_inheritance", "income_caste_domicile"]
STRETCH_CATEGORIES = ["business_trade", "welfare_schemes", "grievances"]

# ---------------------------------------------------------------------------
# Retrieval defaults
# ---------------------------------------------------------------------------
DEFAULT_TOP_K = 5

# Fields every chunk's metadata MUST carry (Step 2 contract)
REQUIRED_CHUNK_METADATA = ["category", "service", "state", "source_url"]
