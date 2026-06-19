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
    rows = await fetch_missing()
    log.info(f"{len(rows)} papers missing embeddings")
    if not rows:
        return
    texts = [f"{r.get('title') or ''}. {r.get('abstract') or ''}".strip() for r in rows]
    vecs = await asyncio.to_thread(embed.embed_many, texts)
    payload = []
    for r, v in zip(rows, vecs):
        if v is not None:
            payload.append({"source": r["source"], "paper_id": r["paper_id"],
                            "embedding": "[" + ",".join(f"{x:.6f}" for x in v) + "]"})
    log.info(f"embedded {len(payload)} / {len(rows)}; upserting")
    written = await supa.upsert_papers(payload)
    log.info(f"DONE: embedded={len(payload)} written={written}")


if __name__ == "__main__":
    asyncio.run(main())
