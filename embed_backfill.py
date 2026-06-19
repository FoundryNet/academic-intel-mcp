#!/usr/bin/env python3
"""Backfill embeddings for papers that have none (re-upsert embedding only)."""
from __future__ import annotations

import asyncio
import logging

import config
import embed
import supa
from http_util import request_json

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("acad.embedfill")


async def fetch_missing(limit=1500) -> list:
    url = f"{config.SUPABASE_URL}/rest/v1/papers"
    h = {"apikey": config.SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {config.SUPABASE_SERVICE_KEY}"}
    rows = await request_json("GET", url, headers=h,
                              params={"select": "source,paper_id,title,abstract",
                                      "embedding": "is.null", "limit": str(limit)},
                              timeout=60)
    return rows if isinstance(rows, list) else []


async def main() -> None:
    total_written = 0
    # PostgREST caps reads at 1000; loop until no rows lack embeddings.
    while True:
        rows = await fetch_missing(limit=1000)
        log.info(f"{len(rows)} papers still missing embeddings")
        if not rows:
            break
        for c in range(0, len(rows), 100):
            chunk = rows[c:c + 100]
            texts = [f"{r.get('title') or ''}. {r.get('abstract') or ''}".strip() for r in chunk]
            vecs = await asyncio.to_thread(embed.embed_many, texts)
            payload = [{"source": r["source"], "paper_id": r["paper_id"],
                        "embedding": "[" + ",".join(f"{x:.6f}" for x in v) + "]"}
                       for r, v in zip(chunk, vecs) if v is not None]
            w = await supa.upsert_papers(payload)
            total_written += w
            log.info(f"  chunk {c//100 + 1}: embedded {len(payload)} (total {total_written})")
    log.info(f"DONE: total embedded/written={total_written}")


if __name__ == "__main__":
    asyncio.run(main())
