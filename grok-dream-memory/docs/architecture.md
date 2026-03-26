# Architecture

## Overview

grok-dream-memory is structured as a lightweight cognitive memory library with an optional FastAPI layer.

```
┌─────────────────────────────────────────────────────┐
│                    User / CLI / API                  │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│                  MemoryStore                         │
│  store() · recall() · all_memories() · decay()       │
│  prune() · count()                                   │
└──────────────┬──────────────────────┬───────────────┘
               │                      │
┌──────────────▼──────┐  ┌────────────▼──────────────┐
│   SentenceTransformer│  │   Qdrant (local embedded) │
│   (embedding)        │  │   ./qdrant_data            │
└─────────────────────┘  └───────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────┐
│                  Dreamer (dream_cycle)                │
│  decay → cross-lane consolidation → prune            │
└──────────────┬──────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────┐
│             Background Scheduler (APScheduler)       │
│             Runs dream_cycle every 5 minutes         │
└─────────────────────────────────────────────────────┘
```

## Memory Lanes

| Lane | Purpose |
|------|---------|
| `episodic` | Events, conversations, context |
| `rules` | Extracted patterns and best practices |
| `safety` | Hard constraints — never pruned aggressively |
| `preferences` | Soft style and tone preferences |

## Dream Cycle

Every 5 minutes (configurable), the dreamer:
1. **Decays** importance of all memories by `decay_rate`
2. **Consolidates** high-importance episodic memories into the `rules` lane
3. **Prunes** memories below `prune_threshold`

## Embeddings

Uses `all-MiniLM-L6-v2` (384-dim, ~80 MB) via `sentence-transformers`. Model is downloaded on first run and cached locally.

## Storage

Qdrant runs embedded — no server, no Docker required. Data lives in `./qdrant_data/`.

## API Layer

FastAPI exposes four endpoints over the same MemoryStore instance used by the CLI.
