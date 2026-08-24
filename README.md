# Benefits Policy RAG Assistant

Answers employee HR questions strictly from a retrieved policy handbook — no hallucination, no out-of-context claims.

## Overview

RAG pipeline over `data/benefits_policies.md`, a synthetic HR handbook for **Meridian Health Group** (19 policies, edition date 1 October 2025). Given an employee question the assistant:

- Retrieves the most relevant policy sections
- Answers strictly from retrieved context
- Cites `POL-NNN` policy IDs in every response
- Declines gracefully when the handbook doesn't cover the topic
- Tags structural constraints (`conflict`, `incomplete`, `compound_eligibility`, `derived`)

Evaluated against `data/sample_questions.csv` (15 questions) — current score **15/15**.

## Demo

Download **[deliverables/demo_rag.zip](deliverables/demo_rag.zip)**, extract it, and open the videos in any media player:

| File | What it shows |
|------|---------------|
| `demo_rag_notebook.mp4` | Full 7-step pipeline walkthrough in `sandbox/RAG.ipynb` — chunking, benchmarks, `answer()` call, batch run, Step 7 assertions (15/15) |
| `demo_rag_python.mp4` | CLI pipeline run via `starter/rag_starter.py` — single question end-to-end |

## Architecture

Five-function pipeline:

| Step | Function | What it does |
|------|----------|--------------|
| 1 | `load_documents()` | Reads `data/benefits_policies.md` as raw text |
| 2 | `chunk()` | Policy-boundary split — one chunk per `## POL-NNN` header |
| 3 | `embed()` | Encodes chunks with `all-MiniLM-L6-v2` (384-dim, CPU, no API key) |
| 4 | `retrieve()` | Cosine similarity top-k=3 over in-memory numpy vectors |
| 5 | `answer()` | Prompts Claude with retrieved chunks via forced tool use; returns structured JSON |

### Key Files

```
benefits_policy_assistant/
├── data/
│   ├── benefits_policies.md   # 19-policy HR handbook
│   └── sample_questions.csv  # 15 evaluation questions (Q01–Q15)
├── sandbox/
│   └── RAG.ipynb              # Primary implementation (7 steps + benchmarks)
├── starter/
│   ├── rag_starter.py         # Runnable CLI pipeline
│   ├── prompt.py              # SYSTEM_PROMPT with grounding rules
│   └── tool.py                # ANSWER_TOOL forced-tool-use schema
└── deliverables/
    ├── demo_rag.zip           # Demo videos (demo_rag_notebook.mp4, demo_rag_python.mp4)
    ├── design_note.md         # Design note: chunking, retrieval, failure modes
    └── effort.md              # Declared effort and token usage statement
```

## Setup

**Prerequisites:** Python 3.x, a Portkey gateway API key.

1. Create a `.env` file in the project root:

   ```
   PORTKEY_API_KEY=your_key_here
   MY_MODEL=claude-sonnet-4-6   # or another Claude model ID
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

   The embedding model (`all-MiniLM-L6-v2`, ~80 MB) downloads automatically on first run and is cached locally for offline use after that.

## Running

```bash
# Activate the virtual environment (Windows)
source .venv/Scripts/activate

# Single question via CLI
python starter/rag_starter.py


# Run without activating (using .venv directly)
.venv/Scripts/python starter/rag_starter.py

# Primary notebook (recommended — includes benchmarks and Step 7 assertions)
jupyter notebook sandbox/RAG.ipynb
```

## Evaluation Summary

| Metric | Result |
|--------|--------|
| Overall accuracy | **15/15 (100%)** |
| Recall@3 — all-MiniLM-L6-v2 | 100% (vs. 79% TF-IDF baseline) |
| Recall@3 — compound questions | 100% at k=3 (vs. 33% at k=1) |
| answer_type distribution | `answered`: 14, `declined`: 1 (Q13) |

Verified by the Step 7 assertion suite in `sandbox/RAG.ipynb`. Q13 correctly returns `declined` — PTO accrual during parental leave is not covered in the handbook.

## Constraint Taxonomy

The system tags each response with the structural complexity it encountered:

| Tag | Pattern |
|-----|---------|
| `conflict` | Two policies disagree, or a single policy contradicts itself |
| `incomplete` | Topic absent from the handbook, or a defined case implies an undefined adjacent case |
| `compound_eligibility` | Answer requires combining 2+ policies, or benefit is gated by employment type / enrollment state |
| `derived` | Answer requires date arithmetic, pro-rating, or references external law not in the handbook |
| `other` | Constraint present that doesn't fit any defined tag |

**Tag frequency across the 15 evaluation questions:** `compound_eligibility`: 3, `conflict`: 3, `incomplete`: 3, `derived`: 1, `other`: 1.

## Token Usage

All LLM calls route through the Portkey gateway to `claude-sonnet-4-6`. Embedding runs entirely on CPU — no API cost.

**Per-call budget (`answer()`):**

| Component | Tokens (est.) |
|-----------|---------------|
| System prompt | ~280 |
| Retrieved context (3 chunks × ~79 tokens avg) | ~240 |
| Employee question (avg ~12 words) | ~15 |
| Structured JSON response (via tool use) | ~200–350 |
| **Total per call** | **~735–885** |

**Full batch run (15 questions):**

| Run | Calls | Input tokens (est.) | Output tokens (est.) |
|-----|-------|---------------------|----------------------|
| Full batch | 15 | ~8,025 | ~3,750 |

**How tokens were kept low:**

- **Local embedding** — `all-MiniLM-L6-v2` runs on CPU; no embedding API calls at any point.
- **Policy-boundary chunking** — each chunk averages ~79 tokens (max ~138). Sliding-window or finer-grained strategies produce more or longer chunks that inflate the retrieved context block.
- **k=3 minimum** — k=3 is the smallest value that achieves 100% recall on all compound questions. Raising to k=4 or k=5 adds ~79 tokens per call with no improvement on the current corpus.

## Response Schema

`answer()` returns a structured dict via forced tool use:

| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | Grounded response citing POL-NNN IDs |
| `answer_type` | enum | `answered` \| `declined` \| `partial` |
| `policies` | string[] | Policy IDs cited (e.g. `["POL-003", "POL-005"]`) |
| `constraints` | string[] | Constraint tags present in this answer |
| `confidence` | string | `high` \| `medium` \| `low` |
| `retrieval_sufficient` | bool | Whether retrieved context was enough to answer |

**Example output** (Q02 — "How much does the company match on my 401k and when does it vest?"):

```json
{
  "answer": "The answer depends on the time period, as the match terms change on January 1, 2026:\n\n**Now (before January 1, 2026) — per POL-007:**\n- **Match:** 100% of your first 3% of eligible pay, plus 50% of the next 2% → maximum employer match of 4%\n- **Vesting:** Graded over three years — one-third vests per year (fully vested after 3 years)\n\n**Starting January 1, 2026 — per POL-015 (supersedes POL-007 match/vesting terms):**\n- **Match:** 100% of your first 4% of eligible pay → maximum employer match of 4%\n- **Vesting:** Immediate — match is fully vested as soon as it is credited\n\nIn both periods, your auto-enrollment default (4%) and your choice between pre-tax or Roth contributions remain unchanged (POL-007).",
  "metadata": {
    "answer_type": "answered",
    "policies": ["POL-007", "POL-015"],
    "constraints": ["conflict"],
    "confidence": "high",
    "retrieval_sufficient": true
  }
}
```


## Benchmarks

Each pipeline stage was benchmarked independently. Winners were selected on recall, then size/speed as a tiebreaker.

### Step 2 — Chunking Strategy

| Strategy | Chunks | Recall@3 | Compound@3 |
|----------|--------|----------|------------|
| **Policy-boundary** (selected) | 19 | 100% | 100% |
| Sliding window | 7 | 100% | 100% |
| Paragraph + header | 20 | 100% | 100% |

**Winner: policy-boundary.** All three tie on recall, so the tiebreaker is structural fit. Sliding window crosses policy boundaries, mixing unrelated content. Paragraph+header splits POL-016 into two chunks, requiring k=4 to reconstruct the internal conflict Q12 depends on. Policy-boundary keeps each policy intact in a single chunk — essential for `conflict` constraint detection.

### Step 3 — Embedding Model

| Model | Dim | Size | Embed time | Recall@3 | Compound@3 |
|-------|-----|------|------------|----------|------------|
| TF-IDF | 390 | <1 MB | 0.00s | 79% | 67% |
| **all-MiniLM-L6-v2** (selected) | 384 | ~80 MB | 0.15s | 100% | 100% |
| all-mpnet-base-v2 | 768 | ~420 MB | 0.95s | 100% | 100% |

**Winner: all-MiniLM-L6-v2.** TF-IDF fails on semantic queries — "home internet" does not match "Remote Work Stipend" (POL-011), causing Q07 to miss. mpnet ties MiniLM on every recall metric but is 5× larger and 6× slower with no benefit on this corpus.

### Step 4 — Retrieval Metric and k

All three metrics (cosine, dot product, euclidean) tie at k=3. Cosine was selected for magnitude-invariance — rankings depend only on vector angle, not policy length.

**k-sensitivity (cosine similarity):**

| k | Recall@k | Compound@k |
|---|----------|------------|
| 1 | 79% | 33% |
| 2 | 93% | 100% |
| 3 | **100%** | **100%** |
| 4 | 100% | 100% |
| 5 | 100% | 100% |

**k=3 is the minimum that recovers all compound questions.** Raising to 4–5 adds ~79 tokens per call with no recall gain on the current corpus.

## Notes & Next Steps

### Hardening applied
- **Prompt injection isolation** — question and retrieved context are wrapped in `<question>`/`<context>` XML tags in the user-turn message, preventing injection via crafted employee input.
- **Input validation** — `_validate_question()` rejects empty strings and questions over 500 characters before any API call.
- **API resilience** — `answer()` retries on `APIConnectionError` and `RateLimitError` with exponential backoff (2 s, 4 s); validates `response.content[0].type == "tool_use"` before indexing.
- **Batch resilience** — Step 6 catches per-question exceptions and records an error entry rather than aborting the run.
- **Offline embedding** — `_load_model()` loads from local cache (`local_files_only=True`) and falls back to download only on a cache miss.

### Business ideas
- Fill out predefined HR forms using retrieved policy data.
- Generate policy-grounded emails for employees.

### Tech ideas
- **Caching** — cache question/response pairs to reduce latency and API cost on repeated queries.
- **Vector database benchmark** — evaluate Chroma, Weaviate, Pinecone as replacements for in-memory numpy when the corpus scales.
- **Database retrieval** — retrieve employee contract and role from an external store to gate benefit eligibility dynamically.
- **Grid search** — test chunk strategy × embedding model × retrieval metric combinations using `RECALL_GT` as the signal; confirm the per-stage winners are also the global optimum.
- **Tuning guidance**: increase `k` to 4–5 if compound questions start missing the second policy; adjust `MAX_QUESTION_LEN` if legitimate questions exceed 500 characters; switch to paragraph+header chunking when individual policies grow beyond ~300 tokens.


## Deliverables

| File | Description |
|------|-------------|
| [deliverables/demo_rag.zip](deliverables/demo_rag.zip) | Demo videos: `demo_rag_notebook.mp4` (full notebook walkthrough) and `demo_rag_python.mp4` (CLI run) |
| [deliverables/design_note.md](deliverables/design_note.md) | One-page design note covering chunking strategy, embedding selection, retrieval tuning, grounding approach, and failure modes found |
| [deliverables/effort.md](deliverables/effort.md) | Declared-effort statement: ~11 hours across 2 sessions, token usage estimates, what was implemented and what was cut |
