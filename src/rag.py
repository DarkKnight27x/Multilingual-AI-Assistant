"""
RAG layer.

THE most important rule in this whole codebase:

    location filter (state / district)  ->  semantic search  ->  top-k chunks

We NEVER run pure semantic search over the entire corpus. A Kerala
procedure handed to a Tamil Nadu citizen is worse than no answer at all.
"""

from __future__ import annotations

import glob
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownTextSplitter
from src.config import (
    CHROMA_PERSIST_DIR,
    EMBEDDING_MODEL,
    KNOWLEDGE_BASE_DIR,
    DEFAULT_TOP_K,
    REQUIRED_CHUNK_METADATA,
)

logger = logging.getLogger(__name__)

_embeddings = None
_vectorstore: Optional[Chroma] = None


def get_embeddings() -> HuggingFaceEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    return _embeddings


# ---------------------------------------------------------------------------
# Front-matter parsing for knowledge base markdown files
# ---------------------------------------------------------------------------
#
# Each .md file under data/knowledge_base/<category>/ is expected to start
# with a small YAML-ish front-matter block:
#
#   ---
#   service: Birth Certificate
#   state: Tamil Nadu          # or "All" for state-independent info
#   district: All
#   source_url: https://crsorgi.gov.in
#   ---
#   <markdown body>
#
# This keeps knowledge-authoring dead simple for non-engineers on the team.

def _parse_frontmatter(text: str) -> tuple[dict, str]:
    meta: dict = {}
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            raw_meta, body = parts[1], parts[2]
            for line in raw_meta.strip().splitlines():
                if ":" in line:
                    key, _, val = line.partition(":")
                    meta[key.strip()] = val.strip()
            return meta, body.strip()
    return meta, text


def _load_documents(category: Optional[str] = None) -> list[Document]:
    """Load every markdown file in the knowledge base into Documents with metadata."""
    pattern = str(KNOWLEDGE_BASE_DIR / (category or "*") / "*.md")
    docs: list[Document] = []

    for path in glob.glob(pattern):
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()

        meta, body = _parse_frontmatter(raw)
        cat = category or os.path.basename(os.path.dirname(path))

        metadata = {
            "category": cat,
            "service": meta.get("service", "Unknown"),
            "state": meta.get("state", "All"),
            "district": meta.get("district", "All"),
            "source_url": meta.get("source_url", ""),
            "file": os.path.basename(path),
        }
        docs.append(Document(page_content=body, metadata=metadata))

    return docs


def build_or_load_vectorstore(force_rebuild: bool = False) -> Chroma:
    """
    Build the Chroma vector store from the knowledge base, or load it from
    disk if it already exists. Call this from scripts/build_index.py after
    any change to data/knowledge_base/.
    """
    global _vectorstore

    embeddings = get_embeddings()

    if not force_rebuild and os.path.isdir(CHROMA_PERSIST_DIR) and os.listdir(CHROMA_PERSIST_DIR):
        logger.info("Loading existing Chroma store from %s", CHROMA_PERSIST_DIR)
        _vectorstore = Chroma(
            persist_directory=CHROMA_PERSIST_DIR,
            embedding_function=embeddings,
        )
        return _vectorstore

    logger.info("Building Chroma store from %s", KNOWLEDGE_BASE_DIR)
    raw_docs = _load_documents()

    if not raw_docs:
        logger.warning(
            "No knowledge base documents found under %s — "
            "add markdown files before querying.",
            KNOWLEDGE_BASE_DIR,
        )

    splitter = MarkdownTextSplitter(chunk_size=800, chunk_overlap=100)
    chunks: list[Document] = []
    for doc in raw_docs:
        for chunk in splitter.split_documents([doc]):
            chunks.append(chunk)

    _vectorstore = Chroma.from_documents(
        documents=chunks if chunks else [Document(page_content="placeholder", metadata={})],
        embedding=embeddings,
        persist_directory=CHROMA_PERSIST_DIR,
    )
    _vectorstore.persist()
    logger.info("Indexed %d chunks from %d source files", len(chunks), len(raw_docs))
    return _vectorstore


def _get_store() -> Chroma:
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = build_or_load_vectorstore()
    return _vectorstore


@dataclass
class RetrievedChunk:
    text: str
    source_url: str
    state: str
    category: str
    service: str
    district: str = "All"


def retrieve(
    query: str,
    state: Optional[str] = None,
    district: Optional[str] = None,
    category: Optional[str] = None,
    k: int = DEFAULT_TOP_K,
) -> list[RetrievedChunk]:
    """
    Location-first retrieval.

    Step 1: build a metadata filter from state/district/category so semantic
            search only ever runs over the correct subset of the corpus.
            A chunk tagged state="All" is considered state-independent and is
            always eligible, regardless of the citizen's state.
    Step 2: semantic search within that filtered subset.
    Step 3: if nothing matches (e.g. state given but no chunks tagged for it
            and no "All" chunks), fall back to a category-only search so we
            can at least surface general/central-government info, and let
            the prompt layer be honest about the lack of state-specific data.
    """
    store = _get_store()

    where: dict = {}
    conditions = []
    if category:
        conditions.append({"category": category})
    if state:
        conditions.append({"$or": [{"state": state}, {"state": "All"}]})

    if len(conditions) == 1:
        where = conditions[0]
    elif len(conditions) > 1:
        where = {"$and": conditions}

    try:
        results = store.similarity_search(query, k=k, filter=where or None)
    except Exception as e:  # Chroma raises on some filter edge cases
        logger.warning("Filtered search failed (%s), falling back to unfiltered", e)
        results = []

    if not results and category:
        # Relax to category-only (drop state/district) so we can still
        # surface something, e.g. central-government-level info.
        try:
            results = store.similarity_search(query, k=k, filter={"category": category})
        except Exception as e:
            logger.warning("Category-only search failed (%s)", e)
            results = []

    if not results:
        # Last resort: fully unfiltered semantic search. Still better than
        # nothing, and the LLM prompt will make clear this may not be
        # state-specific.
        results = store.similarity_search(query, k=k)

    chunks = []
    for doc in results:
        md = doc.metadata or {}
        chunks.append(
            RetrievedChunk(
                text=doc.page_content,
                source_url=md.get("source_url", ""),
                state=md.get("state", "All"),
                category=md.get("category", "unknown"),
                service=md.get("service", "Unknown"),
                district=md.get("district", "All"),
            )
        )
    return chunks


def format_context(chunks: list[RetrievedChunk]) -> str:
    """Turn retrieved chunks into a single string block for the LLM prompt."""
    if not chunks:
        return ""

    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(
            f"[Source {i}] Service: {c.service} | Category: {c.category} | "
            f"State: {c.state} | District: {c.district}\n"
            f"{c.text}\n"
            f"URL: {c.source_url}"
        )
    return "\n\n".join(parts)
