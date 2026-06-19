#!/usr/bin/env python3
"""academic_aggregator — daily (4am). Fetches recent papers from OpenAlex (primary)
+ arXiv (preprints) + PubMed (biomed), embeds title+abstract (fastembed) for
similar-paper search, and upserts into Supabase papers. Author profiles are
populated on demand by the author_profile tool (live OpenAlex + cache).

Manual:  python academic_aggregator.py            # last LOOKBACK_HOURS
         python academic_aggregator.py 168         # last 7 days
"""
from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone

import academic_sources as src
import config
import embed
import supa

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("acad.agg")


async def run_aggregation(hours_back: int | None = None) -> dict:
    hours = hours_back or config.LOOKBACK_HOURS
    date_from = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%d")
    days = max(1, hours // 24)
    log.info(f"aggregating papers since {date_from}")

    results = await asyncio.gather(
        src.fetch_openalex(date_from),
        src.fetch_arxiv(),
        src.fetch_pubmed(days),
        return_exceptions=True,
    )
    rows = []
    for r in results:
        if isinstance(r, Exception):
            log.warning(f"source error: {r}")
        else:
            rows.extend(r)

    # Embed title + abstract.
    texts = [f"{r.get('title') or ''}. {r.get('abstract') or ''}".strip() for r in rows]
    vecs = await asyncio.to_thread(embed.embed_many, texts)
    for r, v in zip(rows, vecs):
        if v is not None:
            r["embedding"] = "[" + ",".join(f"{x:.6f}" for x in v) + "]"

    written = await supa.upsert_papers(rows)
    out = {"fetched": len(rows), "written": written}
    log.info(f"done: {out}")
    return out


async def main() -> None:
    args = [a for a in sys.argv[1:] if a.strip()]
    hours = int(args[0]) if args and args[0].isdigit() else None
    print(await run_aggregation(hours))


if __name__ == "__main__":
    asyncio.run(main())
