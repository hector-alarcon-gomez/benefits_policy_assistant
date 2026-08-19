"""RAG policy assistant — single-file pipeline over data/benefits_policies.md.

Embedding: all-MiniLM-L6-v2 (sentence-transformers, CPU, ~80 MB, no API key).
LLM: Claude via Anthropic SDK, routed through the Portkey gateway.
Retrieval: in-memory cosine similarity (numpy), k=3.

Required .env keys: PORTKEY_API_KEY, MY_MODEL
"""
import os
import re
import time
from pathlib import Path

import anthropic
import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

from prompt import SYSTEM_PROMPT
from tool import ANSWER_TOOL

# ── Paths ──────────────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
POLICIES = DATA_DIR / "benefits_policies.md"

# ── Config ─────────────────────────────────────────────────────────────────────
MAX_QUESTION_LEN = 500
MAX_RETRIES = 3

# ── Credentials ────────────────────────────────────────────────────────────────
load_dotenv()
_missing = [k for k in ("PORTKEY_API_KEY", "MY_MODEL") if not os.environ.get(k)]
if _missing:
    raise EnvironmentError(f"Missing required env vars: {', '.join(_missing)}. Check your .env file.")

MODEL = os.environ["MY_MODEL"]

client = anthropic.Anthropic(
    api_key=os.environ["PORTKEY_API_KEY"],
    base_url="https://portkeygateway.perficient.com",
    default_headers={"x-portkey-api-key": os.environ["PORTKEY_API_KEY"]},
)

# ── Helpers ────────────────────────────────────────────────────────────────────
def _load_model(model_name):
    """Load SentenceTransformer from local cache; download only on first run."""
    try:
        return SentenceTransformer(model_name, local_files_only=True)
    except Exception:
        print(f"Cache miss — downloading {model_name} (one-time download)...")
        return SentenceTransformer(model_name)


def _validate_question(question):
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question must be a non-empty string.")
    if len(question) > MAX_QUESTION_LEN:
        raise ValueError(
            f"Question exceeds {MAX_QUESTION_LEN}-character limit ({len(question)} chars)."
        )
    return question.strip()


# Load once at startup; subsequent calls reuse the cached model.
EMBED_MODEL = _load_model("all-MiniLM-L6-v2")

# ── Pipeline functions ─────────────────────────────────────────────────────────
def load_documents(path=POLICIES):
    """Read the markdown handbook and return its raw text."""
    return path.read_text(encoding="utf-8")


def chunk(text, target_tokens=200):
    """Policy-boundary split — one chunk per ## POL-NNN block, header always present.

    Each policy averages ~79 tokens (max ~138), well within the target_tokens window,
    so sub-chunking adds noise without improving recall. Keeping each policy intact
    is also required for conflict detection (e.g., POL-016 has two contradictory
    paragraphs that must appear together for Q12).
    """
    parts = re.split(r"(?=^## POL-)", text, flags=re.MULTILINE)
    return [p.strip() for p in parts if p.strip().startswith("## POL-")]


def embed(chunks):
    """Encode each chunk with all-MiniLM-L6-v2; return float32 array aligned with chunks."""
    vectors = EMBED_MODEL.encode(chunks, convert_to_numpy=True, show_progress_bar=False)
    return vectors.astype("float32")


def retrieve(question, chunks, vectors, k=3):
    """Cosine similarity top-k retrieval.

    k=3 is the minimum that recovers all compound questions (verified via benchmark).
    Increase to 4–5 if policies grow and compound questions start missing the second hit.
    """
    q_vec = EMBED_MODEL.encode([question], convert_to_numpy=True).astype("float32")
    norms = np.linalg.norm(vectors, axis=1)
    q_norm = float(np.linalg.norm(q_vec))
    sims = (vectors @ q_vec.T).squeeze() / (norms * q_norm + 1e-9)
    top_k_idx = np.argsort(sims)[::-1][:k]
    return [chunks[i] for i in top_k_idx]


def answer(question, retrieved, max_retries=MAX_RETRIES):
    """Prompt Claude with retrieved chunks; return structured dict via forced tool use.

    Wraps user inputs in XML tags to isolate them from the system prompt (prompt-injection
    defense). Retries on transient API errors with exponential backoff.
    """
    question = _validate_question(question)
    context = "\n\n".join(retrieved)
    content = (
        f"<context>\n{context}\n</context>\n\n"
        f"<question>{question}</question>"
    )
    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=1024,
                temperature=0,
                system=SYSTEM_PROMPT,
                tools=[ANSWER_TOOL],
                tool_choice={"type": "tool", "name": "report_answer"},
                messages=[{"role": "user", "content": content}],
            )
            if not response.content or response.content[0].type != "tool_use":
                raise ValueError(
                    f"Unexpected response: stop_reason={response.stop_reason}, "
                    f"blocks={[b.type for b in response.content]}"
                )
            return response.content[0].input
        except (anthropic.APIConnectionError, anthropic.RateLimitError) as e:
            last_exc = e
            if attempt < max_retries:
                wait = 2 ** attempt
                print(f"  Attempt {attempt}/{max_retries} failed ({e.__class__.__name__}), retrying in {wait}s...")
                time.sleep(wait)
    raise last_exc


# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    text = load_documents()
    chunks = chunk(text)
    vectors = embed(chunks)
    q = "How much does the company match on my 401k and when does it vest?"
    retrieved = retrieve(q, chunks, vectors)
    print(answer(q, retrieved)["answer"])


if __name__ == "__main__":
    main()
