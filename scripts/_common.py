"""Shared setup for the command-line scripts: load .env, put src/ on the path, and open the knowledge base
exactly as the deep_research graph does (same file, same embedding model, same Ollama address), so a script
can never build or query the library with different settings than the app uses.

Usage at the top of a script (it lives next to this file):

    from _common import OLLAMA_URL, ROOT, open_kb
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from research_assistant import knowledge  # noqa: E402
from research_assistant.documents import make_embeddings  # noqa: E402

OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "ollama:qwen3-embedding:0.6b")


def default_paths() -> dict:
    """Project-relative defaults, so scripts work from any working directory."""
    return {"qa": str(ROOT / "evals" / "retrieval_qa.json"), "sheet": str(ROOT / "evals" / "faithfulness_sheet.csv")}


def open_kb(path: str | None = None, embedding_model: str | None = None, check_model: bool = True):
    """Open the library. ``check_model=False`` skips the embedding-model check (used by the rebuild that
    changes the model)."""
    model = embedding_model or EMBEDDING_MODEL
    return knowledge.KnowledgeBase(path or knowledge.default_kb_path(), make_embeddings(model, OLLAMA_URL),
                                   embedding_model=model if check_model else "")
