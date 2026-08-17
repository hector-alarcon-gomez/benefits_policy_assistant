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

Nine constraint types that any policy dataset may contain. The `answer()` function tags each response with the applicable types (see `metadata.constraints` in the JSON response schema). When adding new policies, annotate them with the types they introduce.

| Constraint tag | Pattern | Current handbook example |
|---|---|---|
| `version_conflict` | A newer policy supersedes terms in an older one, with a future effective date. Both are retrieved; answer must surface both and state which applies when. | POL-015 supersedes match/vesting in POL-007, effective 2026-01-01. POL-007 terms are current until then. |
| `internal_contradiction` | A single policy contains logically inconsistent statements. | POL-016: eligible after 5 years continuous FT service, but approval requires 7 years. |
| `unanswerable_question` | The topic is genuinely absent from the handbook. Must decline rather than extrapolate. | Q13: PTO accrual rate during parental leave — not mentioned in POL-008 or POL-010. |
| `compound_eligibility` | Correct answer requires combining 2+ policies — either to build a complete answer or because one policy prohibits a benefit granted by another. | POL-006 bars Healthcare FSA + HSA in the same year; both POL-005 and POL-006 must be retrieved. |
| `scope_exclusion` | A policy explicitly restricts or excludes a class of person (employment type, enrollment state). Answering without applying the scope gate is incorrect. | POL-001 gates all benefits by employment class; POL-005 restricts HSA to HDHP enrollees; POL-011 excludes on-site-only employees. |
| `temporal_ambiguity` | Answer depends on a specific date — a future effective date or an event-anchored deadline. | POL-002: QLE changes must be submitted within 30 days. POL-019: repayment applies if employee leaves within 12 months. |
| `partial_coverage` | Handbook mentions the topic but omits a key detail. Distinct from `unanswerable_question` (where the topic itself is absent). | POL-017: first bereavement request needs no documentation; subsequent requests are unaddressed. |
| `calculation_required` | Correct answer requires arithmetic over policy numbers (pro-rating, offsets, tier selection). Data is present but the answer is a computation. | POL-019: pro-rated relocation repayment (1/12 per completed month). POL-018: jury duty pay is the shortfall vs. court stipend. POL-008: three PTO tiers by tenure. |
| `external_reference` | Policy references external law/system not defined in the handbook. Answer only from policy text; decline on the external-law specifics. | POL-010: parental leave "runs concurrently with FMLA" — FMLA terms are outside the handbook. |

## Tech Stack

- Language: Python 3
- Embedding: OpenAI, sentence-transformers, or local (choice left to implementer — document it)
- LLM: Claude (`anthropic` SDK)
- Vector store: in-memory numpy, FAISS, or Chroma (all acceptable)
