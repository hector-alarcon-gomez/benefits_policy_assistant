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

## Critical Data Constraints

The handbook has intentional traps that the retriever and answerer must handle correctly:

- **Policy version conflict**: POL-015 supersedes the match/vesting terms in POL-007, effective 2026-01-01. Both policies will likely be retrieved together for 401k questions. The handbook edition date is Oct 2025, so the POL-015 terms are a *future* change — the answer must surface both and clarify the effective date rather than silently picking one.
- **Internal contradiction**: POL-016 states eligibility after 5 years but *approval* after 7 years. The `answer()` function must surface this contradiction explicitly.
- **Unanswerable questions**: Several sample questions (e.g., Q13: PTO accrual *rate* during parental leave) have no answer in the handbook. The assistant must decline rather than extrapolate.
- **Compound eligibility**: Some answers require combining two policies (e.g., HSA+FSA interaction between POL-005 and POL-006). Single-passage retrieval will fail; `k` and chunking strategy must account for this.

## Tech Stack

- Language: Python 3
- Embedding: OpenAI, sentence-transformers, or local (choice left to implementer — document it)
- LLM: Claude (`anthropic` SDK)
- Vector store: in-memory numpy, FAISS, or Chroma (all acceptable)
