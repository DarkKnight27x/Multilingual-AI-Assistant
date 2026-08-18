# Team B — RAG + LLM Backend (PS-21, Smart India Hackathon 2026)

Shared AI brain for Team A (phone/Bhashini helpline) and Team C (mobile app).
Takes a citizen's messy question + location and returns a grounded,
location-correct, non-hallucinated answer about government services.

## Quick start

```bash
cd packages/ai
cp .env.example .env        # fill in GROQ_API_KEY
pip install -r requirements.txt

python scripts/build_index.py           # build the vector store
python scripts/test_query.py            # sanity-check sample queries

uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload
```

## Try it

```bash
curl -X POST http://localhost:8000/converse \
  -H "Content-Type: application/json" \
  -d '{
    "text": "I need a birth certificate",
    "language": "en",
    "session_id": "call-1"
  }'

curl -X POST http://localhost:8000/converse \
  -H "Content-Type: application/json" \
  -d '{
    "text": "How to get income certificate",
    "language": "hi",
    "session_id": "app-9",
    "state": "Maharashtra",
    "district": "Pune"
  }'
```

## Architecture

```
query → extract intent + location → missing info? → ask
                                   ↓ no
                                retrieve (location-first) → LLM → answer
```

- **Location-first retrieval is the #1 rule.** We filter by state/district
  BEFORE semantic search, never after. A Kerala procedure returned to a
  Tamil Nadu citizen is worse than no answer. See `src/rag.py::retrieve()`.
- **Anti-hallucination is structural, not just a prompt suggestion.** The
  LLM is only shown retrieved context and instructed to say "I don't know"
  + point to official portals when context is empty. See `src/prompts.py`.
- **One endpoint serves both consuming teams.** `POST /converse` returns a
  `response` string (what Team A reads/speaks) and a `structured` object
  (what Team C renders in the app UI).

## Adding knowledge

Add a markdown file under `data/knowledge_base/<category>/`, with a small
front-matter block:

```markdown
---
service: Birth Certificate
state: Tamil Nadu      # or "All" if state-independent
district: All
source_url: https://tnesevai.tn.gov.in
---

## What it is
...
```

Then rebuild the index: `python scripts/build_index.py`.

**Content rules (non-negotiable):**
- Only stable, publicly verifiable information.
- Always include an official portal link.
- Never write a specific fee/timeline unless you've verified it — write
  "varies by state, check portal" instead of guessing.

## Folder structure

```
packages/ai/
├── data/knowledge_base/<category>/*.md   # verified content, tagged by state
├── scripts/
│   ├── build_index.py                    # rebuild vector store
│   └── test_query.py                     # sample queries across langs/cats
└── src/
    ├── config.py         # languages, categories, model config — single source of truth
    ├── rag.py             # location-first retrieval
    ├── prompts.py          # anti-hallucination system prompts
    ├── chain.py            # LLM call + structured JSON parsing
    ├── conversation.py     # session state, intent/location extraction
    ├── service.py          # process_query orchestration (the /converse logic)
    ├── api.py               # FastAPI routes
    └── main.py               # `python -m src.main` entrypoint
```

## Interface contract (locked with Teams A & C)

`POST /converse`

Request:
```json
{
  "text": "I need a birth certificate",
  "language": "ta",
  "session_id": "123",
  "state": "Tamil Nadu",
  "district": "Chennai"
}
```

Response:
```json
{
  "response": "full natural language answer",
  "language": "ta",
  "session_id": "123",
  "structured": {
    "service": "Birth Certificate",
    "category": "vital_records",
    "state": "Tamil Nadu",
    "district": "Chennai",
    "requirements": ["..."],
    "steps": ["1. ...", "2. ..."],
    "fee": "...",
    "processing_time": "...",
    "office": "...",
    "source_url": "https://...",
    "official_portals": ["https://..."]
  }
}
```

## Guardrails implemented

- [x] Location-first retrieval (filter before semantic search)
- [x] Never hallucinate — empty retrieval → honest fallback + portal link
- [x] Same backend serves phone and app
- [x] Structured fields ready for Team C's result screen
- [x] `session_id` threaded through
- [x] Low temperature (0.15) + strict system prompt
