# Declared-Effort Statement

## Summary

**Total hours: ~11 hours.**

**Implemented:** Full 7-step RAG pipeline in `sandbox/RAG.ipynb` and `starter/rag_starter.py` (code ported from notebook, all five pipeline functions working end-to-end) — document loading, policy-boundary chunking, MiniLM embedding, cosine-similarity retrieval (k=3), Claude `answer()` with forced tool use and XML prompt injection isolation, batch runner for all 15 questions, `evaluate()` assertions (15/15 PASS). Three per-stage benchmarks (chunk strategies, embedding models, retrieval metrics). SYSTEM_PROMPT constraint taxonomy with alias mappings to eliminate enum drift. CLAUDE.md context artifact.

**Scoped out:** Demo transcript, response caching and vector database benchmark (corpus too small to justify the investment).

---

## What was implemented

- `sandbox/RAG.ipynb` — full 7-step pipeline with benchmarks
- Step 1 - Load documents 
- Step 2 - Chunk 
- Step 2.1 - Benchmark chunks strategy
- Step 3 - Embedding 
- Step 3.1 - Benchmark embeddings
- Step 4 - Retrieve 
- Step 4.1 - Benchmark retrieve strategies 
- Step 5 — Answer (forced tool use, structured JSON, constraint tagging)
- Step 6 — Batch Evaluation
- Step 7 — Tests (evaluate 15 assertions, answer_type / constraint / policy checks)
- `starter/rag_starter.py` — Final solution. 5 pipeline functions (load, chunk, embed, retrieve, answer). 
- CLAUDE.md — architecture, coding rules, constraint taxonomy 

---

## What was cut

- Response caching: Reduce latency and API cost on repeated queries
- Vector database benchmark (Chroma, Weaviate, Pinecone): In-memory is sufficient for 19 policies
- Using Grid search (chunk × embed × retrieval combinations) to identify the best combination. 


---

## Biggest time sink

The constraint taxonomy (QUESTION_SPEC, TEST_SPEC, SYSTEM_PROMPT definitions) took the longest. The five constraint types (`conflict`, `incomplete`, `compound_eligibility`, `derived`, `other`) required reading all 19 policies carefully, identifying which questions trigger each type, and writing SYSTEM_PROMPT rules precise enough for the model to apply them consistently.
