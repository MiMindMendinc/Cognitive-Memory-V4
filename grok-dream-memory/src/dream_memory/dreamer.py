"""Dream cycle: cross-lane consolidation and reinforcement."""
from __future__ import annotations

import logging
import time
from typing import Optional

from .config import Config
from .memory import MemoryStore

logger = logging.getLogger(__name__)


def dream_cycle(store: Optional[MemoryStore] = None, config: Optional[Config] = None) -> dict:
    """
    Run one dream cycle.

    Steps:
    1. Decay importance of all memories.
    2. Cross-lane consolidation: find high-importance episodic memories
       and mirror a condensed version into the 'rules' lane if not already present.
    3. Prune stale low-importance memories.

    Returns a summary dict with counts.
    """
    cfg = config or Config.from_env()
    ms = store or MemoryStore(cfg)

    start = time.time()
    logger.info("Dream cycle started")

    # Step 1 – decay
    decayed = ms.decay()

    # Step 2 – cross-lane consolidation
    consolidated = 0
    episodic = ms.all_memories(lane="episodic")
    for mem in episodic:
        if float(mem.get("importance", 0)) >= 0.7 and not mem.get("consolidated"):
            condensed = f"[Rule extracted] {mem['text'][:200]}"
            ms.store(condensed, lane="rules", metadata={"source_id": mem["id"], "consolidated": True})
            # mark source as consolidated
            try:
                ms._client.set_payload(
                    collection_name=cfg.collection_name,
                    payload={"consolidated": True},
                    points=[mem["id"]],
                )
            except Exception:
                pass
            consolidated += 1

    # Step 3 – prune
    pruned = ms.prune()

    elapsed = round(time.time() - start, 3)
    summary = {
        "decayed": decayed,
        "consolidated": consolidated,
        "pruned": pruned,
        "elapsed_seconds": elapsed,
    }
    logger.info("Dream cycle complete: %s", summary)
    return summary
