"""Starter skeleton: a minimal RAG policy assistant.

Fill in the TODOs. Keep it single-file and dependency-light so a reviewer can run
it end-to-end. You may swap the embedding/LLM provider, but document your choice.
"""
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
POLICIES = DATA_DIR / "benefits_policies.md"


def load_documents(path=POLICIES):
    """TODO: read the markdown handbook and return its raw text."""
    raise NotImplementedError


def chunk(text, target_tokens=200):
    """TODO: split policy text into retrievable chunks.

    Design your own chunking strategy and document why you chose it. Retrieving
    the single nearest passage is rarely enough to answer an HR question
    correctly - decide what "enough context" means here and defend it.
    """
    raise NotImplementedError


def embed(chunks):
    """TODO: turn each chunk into a vector. Return a list aligned with `chunks`."""
    raise NotImplementedError


def retrieve(question, chunks, vectors, k=3):
    """TODO: embed the question, score against `vectors`, return top-k chunks."""
    raise NotImplementedError


def answer(question, retrieved):
    """TODO: prompt an LLM with the retrieved chunks as context.

    Requirements:
      - Ground the answer ONLY in retrieved text.
      - Cite the policy id(s) you relied on.
      - Never state something the retrieved text does not support, and never
        resolve an apparent disagreement in the source by silently choosing one
        side.
      - If the context does not contain the answer, say so instead of guessing.
    """
    raise NotImplementedError


def main():
    text = load_documents()
    chunks = chunk(text)
    vectors = embed(chunks)
    q = "How much does the company match on my 401k and when does it vest?"
    retrieved = retrieve(q, chunks, vectors)
    print(answer(q, retrieved))


if __name__ == "__main__":
    main()
