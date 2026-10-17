# RAG that cites itself

Most RAG demos retrieve a chunk and hope the model stays honest. I wanted the opposite:
a pipeline where **every claim carries a receipt**.

## The loop

```text
query -> retrieve (hybrid dense + BM25) -> synthesise -> verify citations -> publish
```

- **Retrieve** with ColPali late-interaction for visuals and BM25 for exact terms.
- **Synthesise** a report with an LLM, but force inline source markers.
- **Verify** each marker against the retrieved set. Unverifiable claims get dropped.
- **Publish** the eval report, including the failures.

## Why publish failures?

Because a system that hides its misses is lying to you. The eval suite in `citecheck`
prints what it got wrong. That is the whole point — trust is built from evidence, not vibes.
