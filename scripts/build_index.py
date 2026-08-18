"""
Rebuild the vector store from data/knowledge_base/.

Run this after ANY change to the knowledge base markdown files:

    python scripts/build_index.py
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.rag import build_or_load_vectorstore  # noqa: E402

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    store = build_or_load_vectorstore(force_rebuild=True)
    print("Vector store rebuilt successfully.")
