# Design Note

## 1. Chunking Strategy

**Selected: policy-boundary split** — `re.split(r"(?=^## POL-)", text)`, yielding one chunk per policy (19 chunks).

Benchmark (Step 2.1, `sandbox/RAG.ipynb`):

| Strategy | n_chunks | header_cov | recall@3 | compound@3 |
|---|---|---|---|---|
| policy-boundary | 19 | 100% | 14/14 (100%) | 3/3 (100%) |
| sliding-window | 7 | 100% | 14/14 (100%) | 3/3 (100%) |
| paragraph+header | 20 | 100% | 14/14 (100%) | 3/3 (100%) |

All three strategies hit the same recall ceiling. Policy-boundary was chosen because it produces the fewest chunks (19), minimizing retrieval noise. The critical structural reason: POL-016 contains two contradictory paragraphs (5-year eligibility vs. 7-year approval) that Q12 requires in the same retrieved chunk. Paragraph+header splits POL-016 into two chunks, requiring k≥4 to recover both halves. Sliding-window crosses policy boundaries, mixing unrelated content and making POL-NNN citation unreliable.

---

## 2. Embedding Model

**Selected: `all-MiniLM-L6-v2`** via `sentence-transformers`, loaded through `_load_model()` helper.

Benchmark (Step 3.1, `sandbox/RAG.ipynb`):

| Strategy | dim | size | embed_time | recall@3 | compound@3 |
|---|---|---|---|---|---|
| TF-IDF | 390 | <1 MB | 0.00s | 11/14 (79%) | 2/3 (67%) |
| all-MiniLM-L6-v2 | 384 | ~80 MB | 0.15s | 14/14 (100%) | 3/3 (100%) |
| all-mpnet-base-v2 | 768 | ~420 MB | 1.05s | 14/14 (100%) | 3/3 (100%) |

TF-IDF misses 3 questions (Q02, Q07, Q11) where employee phrasing differs from policy wording — e.g., "home internet" fails to match "Remote Work Stipend" in POL-011, and "401k match" fails to surface both POL-007 and POL-015 for the version-conflict question. `all-mpnet-base-v2` ties with MiniLM on all metrics but requires 5× the disk space and is 7× slower, with no benefit on this 19-policy corpus.

---

## 3. Retrieval

**Selected: cosine similarity, k = 3.**

Distance metric benchmark (Step 4.1, `sandbox/RAG.ipynb`):

| Strategy | recall@3 | compound@3 |
|---|---|---|
| cosine similarity | 14/14 (100%) | 3/3 (100%) |
| dot product | 14/14 (100%) | 3/3 (100%) |
| euclidean distance | 14/14 (100%) | 3/3 (100%) |

k-sensitivity (cosine, Step 4.1):

| k | recall@k | compound@k |
|---|---|---|
| 1 | 11/14 (79%) | 1/3 (33%) |
| 2 | 13/14 (93%) | 3/3 (100%) |
| 3 | 14/14 (100%) | 3/3 (100%) |
| 4 | 14/14 (100%) | 3/3 (100%) |
| 5 | 14/14 (100%) | 3/3 (100%) |

All three distance metrics tie at k=3. Cosine is chosen because it is magnitude-invariant — rankings depend only on the angle between vectors, so results are unaffected by policy length variation. Euclidean conflates angle and magnitude; longer policies produce larger-magnitude vectors that inflate distance even for semantically close pairs. Dot product equals cosine when vectors are near-unit-length (which MiniLM produces) but diverges on corpora with higher length variance.

k=3 is the minimum that recovers all compound questions: Q04 requires both POL-005 and POL-006; Q02 and Q11 each require both POL-007 and POL-015. At k=2, Q04 is missed (2/3 compound recall).

---

## 4. Grounding and Citation

The `answer()` function enforces strict context grounding through four mechanisms (Step 5, `sandbox/RAG.ipynb`):

**SYSTEM_PROMPT rules:** Answer only from provided policy excerpts; cite every `POL-NNN` ID relied upon; when policies conflict or contradict each other, state both positions and which applies when — never silently choose one side; when the topic is absent, decline with the exact phrase `'I don't know — this is not covered in the handbook.'`

**Forced tool use:** `tool_choice={"type": "tool", "name": "report_answer"}` forces the model to call `report_answer` with a validated JSON schema (`answer_type` enum, `policies` array, `constraints` enum array, `confidence`, `retrieval_sufficient`). The model cannot return free-form prose that bypasses grounding rules; `answer_type="declined"` is a machine-checkable signal, not a prose similarity check.

**Prompt injection isolation:** The user turn wraps both untrusted inputs in XML tags — `<context>…</context>` for retrieved chunks and `<question>…</question>` for the employee question — separating content from instructions and preventing injection via crafted question text.

**Input validation:** `_validate_question()` rejects empty strings and questions over 500 characters before any API call. `answer()` wraps `client.messages.create()` in a retry loop catching `APIConnectionError` and `RateLimitError` with exponential backoff (2^attempt seconds, up to `MAX_RETRIES=3`), and validates `response.content[0].type == "tool_use"` before accessing `.input`.

---

## 5. Failure Modes

- At first, there was no response schema was defined which generated different responses to the text 'I don't know — this is not covered in the handbook.'; the answer was correct but verifying it required generating a vector and hardcoded text emplying the same answer. A response schema was validate the answers and get consistent results easier to test.
- Claude created over 10 taxonomies which generated variant results during the tests, 5 categories were defined to adddress this issue.
