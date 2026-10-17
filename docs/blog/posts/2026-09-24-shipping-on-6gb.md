# Shipping real AI on a 6 GB GPU

Constraint is a feature. When you only have **6 GB of VRAM**, you stop reaching for
the biggest model and start engineering.

## What actually fits

- Quantised small-language-models for reasoning steps
- Sentence-transformers for embeddings, batched carefully
- FAISS or a local Qdrant for vectors
- ColPali quantised for visual retrieval

## The discipline

- Profile memory before you profile speed.
- Cache everything that is deterministic.
- Make "no API key" a hard requirement, so anyone can reproduce your work.

The result is not a weaker system. It is a **portable** one — it runs on a friend's
laptop, a lab machine, or a cheap VM. Access is part of ethics in AI.
