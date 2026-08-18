# PROJECT HANDOFF — Team B: RAG + LLM Backend (PS-21, Smart India Hackathon 2026)

Paste this whole file as your first message in the new Claude account/conversation,
along with the attached `team-b-rag-llm.zip`. It contains everything needed to
pick this project up with zero lost context.

---

## 1. What this project is

This is **Team B's** deliverable for a 3-team Smart India Hackathon project (PS-21):

- **Team A** — Telephone / Bhashini helpline (handles language detection + speech)
- **Team B** — *(this project)* Shared RAG + LLM backend
- **Team C** — Mobile app (consumes the same backend, renders richer UI)

Team B's job: turn a citizen's messy question + location into a grounded,
location-correct, **non-hallucinated** answer about Indian government services.
Team B does NOT handle speech or language detection — Team A does that and just
passes a language code.

### Locked interface contract (do not change without re-syncing with Teams A & C)

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

`GET /health` → `{"status": "ok"}`

### Supported languages (fixed set, respect the code — don't translate UI)
`en, hi, ta, mr, ml, gu`

### Six service categories (every KB chunk must be tagged with one)
1. `vital_records` — birth, death, marriage certificates
2. `property_inheritance` — legal heir certificate, property mutation, succession certificate
3. `income_caste_domicile` — income, caste & domicile certificates
4. `business_trade` — Udyam registration, trade license, GST registration
5. `welfare_schemes` — ration card, old-age/widow pension, disability certificate
6. `grievances` — RTI, grievance redressal, consumer complaints

Priority order: **1–3 first** (highest frequency, most standardized), 4–6 are stretch.

---

## 2. Non-negotiable design rules (baked into the code — preserve these)

1. **Location-first retrieval.** Filter the vector store by state/district
   metadata *before* running semantic search — never after. A Kerala
   procedure returned to a Tamil Nadu citizen is worse than no answer.
   Implemented in `src/rag.py::retrieve()`.
2. **Never hallucinate.** If retrieval returns nothing relevant, return an
   honest fallback string + point to the official portal — never invent
   fees, offices, forms, timelines. This is enforced structurally (empty
   context → skip the LLM call entirely and return `get_fallback()`), not
   just via prompt wording.
3. **One backend, two consumers.** Same `/converse` endpoint serves Team A
   (needs mainly `response`) and Team C (needs the full `structured` object).
4. **Never 500 a live phone call.** Every layer (`rag.py`, `chain.py`,
   `service.py`) catches its own exceptions and degrades to a safe fallback
   response rather than raising.
5. **Low temperature (0.15) + strict system prompt** for factual consistency.
6. **`session_id` threaded through** every request/response so Team A/C can
   maintain multi-turn context (e.g., citizen gives state in turn 2).

---

## 3. Tech stack

| Component | Choice |
|---|---|
| LLM | Groq (`openai/gpt-oss-20b`, configurable via `.env`) |
| Framework | LangChain 0.3+ |
| Vector store | Chroma (MVP; pgvector/Supabase is the noted upgrade path) |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` (upgrade path: BGE-M3) |
| API | FastAPI + Pydantic v2 |
| Config | python-dotenv, single root `.env` |

---

## 4. Folder structure (already built)

```
packages/ai/
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
├── Dockerfile
├── docker-compose.yml
│
├── data/knowledge_base/
│   ├── vital_records/            (3 files: birth, birth_TN, death — marriage still TODO)
│   ├── property_inheritance/     (3 files: legal_heir, mutation, succession)
│   ├── income_caste_domicile/    (3 files: income, domicile, caste)
│   ├── business_trade/           (3 files: udyam, trade_license, gst)
│   ├── welfare_schemes/          (2 files: ration_card, disability_pension)
│   └── grievances/               (2 files: rti, consumer_complaint)
│
├── scripts/
│   ├── build_index.py            # rebuild vector store — run after any KB change
│   └── test_query.py             # sample queries across categories/languages
│
├── tests/
│   └── test_service.py           # basic pytest smoke tests
│
└── src/
    ├── __init__.py
    ├── config.py       # SINGLE SOURCE OF TRUTH: languages, categories, model names, paths
    ├── rag.py           # location-first retrieval + Chroma store
    ├── prompts.py        # anti-hallucination system prompt + structured-output prompt
    ├── chain.py           # Groq LLM call + JSON-splitting parser
    ├── conversation.py     # session state (in-memory dict) + intent/location extraction
    ├── service.py            # process_query() — the actual /converse orchestration
    ├── api.py                 # FastAPI routes
    └── main.py                 # `python -m src.main` entrypoint
```

---

## 5. Status as of handoff

**Done:**
- Full skeleton, all 8 `src/` modules written and syntax-checked (`py_compile` clean)
- Knowledge base: all 6 categories now have at least 2 files (see folder tree above)
- `build_index.py` / `test_query.py` scripts
- Dockerfile + docker-compose for one-command local run
- Basic pytest smoke tests
- README with quickstart + architecture

**NOT done yet — pick up here:**
- [ ] Never actually run against a live Groq API key (no key was available in this
      environment) — **first thing to do on the new account: get a Groq API key,
      drop it in `.env`, run `build_index.py` then `test_query.py` and fix whatever
      breaks on first real contact.**
- [ ] `sentence-transformers` / embedding model download hasn't been verified in a
      real environment (no network in the sandbox this was built in).
- [ ] More state-specific KB content — currently only Tamil Nadu has a
      state-specific file (`birth_certificate_tamil_nadu.md`). Add more states as
      time allows, prioritizing whichever state Team A's pilot/demo will use.
- [ ] Marriage certificate KB file (vital_records) — mentioned in scope but not
      yet written.
- [ ] Old-age/widow pension KB file (welfare_schemes) — only disability certificate
      and ration card exist so far.
- [ ] Load-test / concurrency check — in-memory session dict in `conversation.py`
      is NOT safe across multiple uvicorn workers. Fine for a single-worker
      hackathon demo; if you scale workers, move session state to Redis.
- [ ] No auth/rate-limiting on `/converse` — fine for hackathon demo, flag for
      Team A/C integration if this goes anywhere beyond the demo.
- [ ] Real integration test with Team A and Team C's actual request payloads
      (this was built purely against the spec doc, never against their live code).

---

## 6. How to resume work (step by step)

```bash
# 1. Unzip the project
unzip team-b-rag-llm.zip
cd packages/ai

# 2. Set up environment
cp .env.example .env
# edit .env and paste your GROQ_API_KEY

python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Build the vector index from the knowledge base
python scripts/build_index.py

# 4. Sanity check retrieval + generation end to end
python scripts/test_query.py

# 5. Run the API
uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload

# 6. Test it
curl -X POST http://localhost:8000/converse \
  -H "Content-Type: application/json" \
  -d '{"text": "I need a birth certificate", "language": "en", "session_id": "call-1"}'
```

If `test_query.py` throws errors, they will most likely be from:
- Missing/invalid `GROQ_API_KEY`
- `sentence-transformers` model download failing (needs internet on first run —
  it caches locally after)
- Chroma filter syntax mismatch (Chroma's `$and`/`$or` filter syntax has changed
  across versions before — check `chromadb` version in `requirements.txt` matches
  what's installed)

---

## 7. Work division (as originally planned — carry this forward)

**Person 1 — Retrieval & Knowledge**
Owns: `config.py`, `rag.py`, `data/knowledge_base/`, `scripts/build_index.py`
Next tasks: verify Chroma filtering actually excludes wrong-state results with a
real embedding model; add more state-specific files; tune chunk size if answers
come back too short/long.

**Person 2 — LLM, Conversation & API**
Owns: `prompts.py`, `chain.py`, `conversation.py`, `service.py`, `api.py`,
`scripts/test_query.py`
Next tasks: get a real Groq key and confirm the `<<<JSON>>>` structured-output
convention survives real model output (models sometimes ignore formatting
instructions — add a repair/retry step if so); harden intent extraction.

**Shared, end of week:** integration test across all 6 languages + the
missing-location flow; a deliberate hallucination review (ask about something
NOT in the KB, confirm it says "I don't know" + gives a portal link instead of
guessing).

---

## 8. Anything the new Claude instance should ask me if unclear

- Which state/city is the hackathon demo targeting? (determines which
  state-specific KB files to prioritize writing next)
- Do we have a Groq API key yet?
- Has Team A or Team C sent their actual request/response test payloads, or
  are we still working purely from the spec doc?
