# grok-dream-memory

> Local AI memory that dreams, decays, and consolidates — zero Docker required.

A lightweight cognitive memory library built on local Qdrant, semantic embeddings, and an automated dream cycle. It remembers across four lanes — episodic, rules, safety, and preferences — and runs a background consolidation pass every five minutes, pruning stale memories and promoting high-value episodic events into durable rules.

Based on 4 months of real-world usage: it remembers like a person. Ask broadly and it retrieves broadly. Give it a light lane hint (e.g. `--lane rules`) and it surfaces the right thing. It won't pretend to be a perfect database — it is a memory, not a lookup table.

---

## Features

- **4 memory lanes** — episodic, rules, safety, preferences
- **Semantic recall** — cosine similarity via `all-MiniLM-L6-v2`
- **Background dreaming** — auto-runs every 5 minutes via APScheduler
- **Importance scoring + decay** — memories age out unless reinforced
- **Cross-lane consolidation** — high-importance episodic memories get distilled into rules
- **Pruning** — stale low-importance memories are removed automatically
- **Zero-Docker default** — Qdrant runs embedded, stores to `./qdrant_data/`
- **FastAPI dashboard** — optional web UI at `http://localhost:8000`
- **Clean CLI** — add, recall, dream, stats from the terminal

---

## Install

```bash
git clone https://github.com/MiMindMendinc/Cognitive-Memory-V4
cd Cognitive-Memory-V4/grok-dream-memory
pip install -r requirements.txt
```

On first run, `sentence-transformers` will download `all-MiniLM-L6-v2` (~80 MB) and cache it.

---

## Usage — CLI

```bash
# Add a memory
python -m src.dream_memory.cli add "Always use type hints in Python" --lane rules

# Recall
python -m src.dream_memory.cli recall "Python best practices"

# Recall from a specific lane
python -m src.dream_memory.cli recall "safety constraints" --lane safety

# Show all memories
python -m src.dream_memory.cli show

# Run a dream cycle manually
python -m src.dream_memory.cli dream

# Stats
python -m src.dream_memory.cli stats
```

---

## Usage — API

```bash
# Start the API server
python -m api.server
# or
python -m src.dream_memory.cli --api
```

Open `http://localhost:8000` for the dashboard, or use the API directly:

```bash
# Add a memory
curl -X POST http://localhost:8000/add \
  -H "Content-Type: application/json" \
  -d '{"text": "I prefer dark mode", "lane": "preferences"}'

# Recall
curl -X POST http://localhost:8000/recall \
  -H "Content-Type: application/json" \
  -d '{"query": "UI preferences", "top_k": 3}'

# Dream
curl -X POST http://localhost:8000/dream

# Show all
curl http://localhost:8000/show
```

API docs: `http://localhost:8000/docs`

---

## Memory Lanes

| Lane | What goes here |
|------|---------------|
| `episodic` | Conversations, events, context snapshots |
| `rules` | Extracted patterns, best practices (partly auto-populated by dreamer) |
| `safety` | Hard constraints — do not delete, do not expose, etc. |
| `preferences` | Style, tone, soft preferences |

When recalling without a lane filter, all lanes are searched simultaneously. Add `--lane` to narrow the search when you know which category you're looking for.

---

## Architecture

```
CLI / API
    │
MemoryStore  ──  Qdrant (local, ./qdrant_data)
    │
Dreamer (dream_cycle)
    │
BackgroundScheduler (every 5 min)
```

See [docs/architecture.md](docs/architecture.md) for more detail.

---

## Run the demo

```bash
python examples/demo.py
```

---

## Tests

```bash
pip install pytest
pytest tests/
```

---

## Optional: Qdrant server mode

If you want to run Qdrant as a separate server (e.g. for multi-process access):

```bash
docker-compose up -d
```

Then set `QDRANT_PATH` to use a URL instead (requires code change — local mode is the default and recommended path).

---

## Configuration

All config can be overridden via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_PATH` | `./qdrant_data` | Local Qdrant storage path |
| `COLLECTION_NAME` | `dream_memory` | Qdrant collection name |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | SentenceTransformer model |
| `DREAM_INTERVAL_MINUTES` | `5` | Dream cycle frequency |
| `DECAY_RATE` | `0.01` | Importance decay per cycle |
| `PRUNE_THRESHOLD` | `0.05` | Prune below this importance |
| `TOP_K_RECALL` | `5` | Default recall results |

---

## Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Write tests for your changes
4. Run `pytest tests/`
5. Open a PR

Code style: PEP 8, type hints throughout, docstrings on public functions.

---

## License

MIT — see [LICENSE](../LICENSE)
