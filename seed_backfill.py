#!/usr/bin/env python3
"""One-off foundational seed for academic-intel-mcp.

The daily aggregator pulls *recent* papers (freshness). For a strong launch
corpus we instead pull the **most-cited** recent papers across our OpenAlex
concepts, plus recent arXiv preprints and PubMed biomed, embed, and upsert.

Run once:  python seed_backfill.py
"""
from __future__ import annotations

import asyncio
import logging

import academic_sources as src
import config
import embed
import supa
from http_util import request_json

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("acad.seed")

_UA = {"User-Agent": config.SOURCE_USER_AGENT}


async def fetch_openalex_cited(date_from: str, pages: int = 4) -> list:
    """Most-cited works since date_from across our concepts (great demo data)."""
    rows, cursor = [], "*"
    flt = f"from_publication_date:{date_from},concepts.id:{config.OPENALEX_CONCEPTS.replace(',', '|')}"
    for page in range(pages):
        params = {"filter": flt, "per-page": "200", "cursor": cursor,
                  "sort": "cited_by_count:desc", "mailto": config.OPENALEX_MAILTO}
        r = await request_json("GET", config.OPENALEX_API, headers=_UA, params=params,
                               timeout=max(config.REQUEST_TIMEOUT, 45))
        if not isinstance(r, dict) or "results" not in r:
            log.warning(f"OpenAlex page {page} error: {str(r)[:160]}")
            break
        for w in r["results"]:
            m = src.map_openalex(w)
            if m:
                rows.append(m)
        cursor = (r.get("meta") or {}).get("next_cursor")
        log.info(f"OpenAlex cited page {page + 1}: total {len(rows)}")
        if not cursor or not r["results"]:
            break
    return rows


async def main() -> None:
    # Most-cited recent papers (last ~3 years) + recent preprints + biomed.
    results = await asyncio.gather(
        fetch_openalex_cited("2023-01-01", pages=4),
        src.fetch_arxiv(max_results=200),
        src.fetch_pubmed(days=7, retmax=100),
        return_exceptions=True,
    )
    rows = []
    for r in results:
        if isinstance(r, Exception):
            log.warning(f"source error: {r}")
        else:
            rows.extend(r)
    log.info(f"fetched {len(rows)} total before embed")

    texts = [f"{r.get('title') or ''}. {r.get('abstract') or ''}".strip() for r in rows]
    vecs = await asyncio.to_thread(embed.embed_many, texts)
    for r, v in zip(rows, vecs):
        if v is not None:
            r["embedding"] = "[" + ",".join(f"{x:.6f}" for x in v) + "]"

    written = await supa.upsert_papers(rows)
    log.info(f"DONE: fetched={len(rows)} written={written}")


if __name__ == "__main__":
    asyncio.run(main())
