# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

RAG assistant over `data/benefits_policies.md` (synthetic HR handbook, 19 policies). Given an employee question it must: retrieve the relevant policy section(s), answer strictly from retrieved context, cite `POL-NNN` IDs, and decline gracefully when the handbook doesn't cover the question. Evaluate against `data/sample_questions.csv` (15 questions).

The handbook header pins edition date **1 October 2025** — treat that as "today" when answering date-sensitive questions.

## Common Commands

```bash
# Install dependencies (once requirements.txt exists)
pip install -r requirements.txt

# Run the pipeline
python starter/rag_starter.py

# Run against all 15 sample questions (once a batch runner exists)
python starter/rag_starter.py --eval

# Run tests
pytest

# Run a single test
pytest tests/test_foo.py::test_bar

# Lint
ruff check .
```

## Architecture

Single-file RAG pipeline in `starter/rag_starter.py`. Five functions in sequence:

1. **`load_documents()`** — reads `data/benefits_policies.md` as raw text.
2. **`chunk(text, target_tokens=200)`** — splits the handbook into retrievable passages. Each policy begins with `## POL-NNN`; preserving that header in every chunk is critical so the `answer()` function can cite it.
3. **`embed(chunks)`** — converts each chunk to a vector; returns a list aligned with `chunks`.
4. **`retrieve(question, chunks, vectors, k=3)`** — embeds the question, scores against stored vectors, returns top-k chunks.
5. **`answer(question, retrieved)`** — prompts the LLM using only the retrieved chunks. Hard requirements: cite `POL-NNN` IDs, never state something the retrieved text doesn't support, never silently resolve contradictions, say "I don't know" when context is insufficient.

`main()` wires these together and runs one hard-coded test question.

## Coding Rules

These rules apply whenever editing `sandbox/RAG.ipynb` or `starter/rag_starter.py`:

- **Prompt injection isolation** — the user-turn message in `answer()` wraps both untrusted inputs in XML tags: `<context>…</context>` for retrieved chunks and `<question>…</question>` for the employee question. Preserve this structure; do not collapse them into plain f-string interpolation.
- **Embedding model loading** — always use `_load_model(model_name)` instead of `SentenceTransformer(model_name)` directly. The helper tries `local_files_only=True` first (reads from cache, no network) and falls back to a download only on a cache miss. This keeps the notebook usable offline once models are cached.
- **API call error handling** — `client.messages.create()` calls must be wrapped in a retry loop that catches `anthropic.APIConnectionError` and `anthropic.RateLimitError` with exponential backoff. After the retry loop, validate `response.content[0].type == "tool_use"` before indexing — do not access `.input` blindly.
- **Batch resilience** — the Step 6 batch loop must catch per-question exceptions and record an error entry rather than aborting the entire run.

## Critical Data Constraints

Five constraint types that any policy dataset may contain. The `answer()` function tags each response with the applicable types (see `metadata.constraints` in the JSON response schema). When adding new policies, annotate them with the types they introduce.

| Constraint tag | Pattern | Current handbook example |
|---|---|---|
| `conflict` | Two policies disagree (newer supersedes older with effective date) or a single policy contradicts itself. State both positions; never silently choose one side. | POL-015 supersedes match/vesting in POL-007, effective 2026-01-01. POL-016: eligible after 5 years continuous FT service, but approval requires 7 years. |
| `incomplete` | Handbook coverage fails — topic entirely absent (pair with `answer_type='declined'`) or a policy defines one scenario while another foreseeable scenario is unaddressed, even if the other scenario is never explicitly named. Tag when the defined case is present in the retrieved text; the defined case IS the trigger. | Q13: PTO accrual during parental leave absent — tag `incomplete` + `declined`. POL-017: states no documentation for first request; subsequent requests undefined — tag `incomplete` even when answering the defined (first-request) case (Q14). |
| `compound_eligibility` | Answer requires combining 2+ policies (mandatory, not merely co-retrieved), or a policy gates the benefit by employment type or enrollment state. | POL-006 bars Healthcare FSA + HSA in the same year; both POL-005 and POL-006 must be retrieved. POL-001 gates all benefits by employment class. POL-011 excludes on-site-only employees from remote stipend. |
| `derived` | Answer requires processing beyond direct text lookup: a date calculation or event-anchored deadline, arithmetic over policy numbers (pro-rating, offsets, tier selection), or the policy cites external law/system not in the handbook. | POL-002: QLE changes must be submitted within 30 days. POL-019: pro-rated relocation repayment (1/12 per completed month). POL-010: parental leave "runs concurrently with FMLA." |
| `other` | Constraint present that does not fit any of the four defined tags. Use as escape valve when a new dataset introduces a pattern not yet classified. | — |

## Tech Stack

- Language: Python 3
- Embedding: `all-MiniLM-L6-v2` via `sentence-transformers` (384-dim, ~80 MB, CPU, local — no API key required). Load via `_load_model()` helper; never call `SentenceTransformer()` directly.
- LLM: Claude via `anthropic` SDK, routed through the Portkey gateway at `https://portkeygateway.perficient.com`
- Vector store: in-memory numpy cosine similarity (k=3 default)
