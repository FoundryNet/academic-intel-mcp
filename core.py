"""Shared logic behind the MCP tools + REST routes: 7 operations + x402 gating.
paper_detail and mint_info are free; the rest run payment_gate.precheck(price).
citation_graph + author_profile use live OpenAlex; similar_papers uses pgvector.
"""
from __future__ import annotations

import asyncio
import logging
from collections import Counter
from datetime import datetime, timedelta, timezone

import academic_sources as src
import config
import mint_integration
import embed
import payment_gate
import supa

logger = logging.getLogger("acad.core")


def _days_ago(n):
    return (datetime.now(timezone.utc) - timedelta(days=int(n))).strftime("%Y-%m-%d")


def _billing(d):
    g = d.get("gate")
    if g == "free":
        cap, cnt = d.get("cap"), d.get("count")
        return {"tier": "free", "used_today": cnt, "daily_free": cap,
                "remaining_today": (cap - cnt) if (cap is not None and cnt is not None) else None}
    if g == "paid":
        return {"tier": "paid", "charged_usdc": d.get("amount_usdc")}
    if g == "api_key":
        return {"tier": "api_key", "note": "billed to your Forge account"}
    return {"tier": "free", "note": "gating inert"}


async def do_search(filters, *, agent_key, payment_tx=None, api_key=None):
    params = {k: v for k, v in (filters or {}).items() if v not in (None, "")}
    dec = await payment_gate.precheck("search_papers", params, config.PRICE_SEARCH, agent_key, payment_tx, api_key)
    if dec["gate"] == "blocked":
        return dec["body"]
    rows = await supa.search_papers(**params)
    return {"results": rows, "count": len(rows), "billing": _billing(dec)}


async def do_detail(paper_id, doi, title):
    if not (paper_id or doi or title):
        return {"error": "bad_request", "detail": "paper_id, doi, or title is required"}
    row = await supa.paper_by(paper_id=paper_id, doi=doi, title=title)
    if not row and paper_id and (paper_id.upper().startswith("W") or "openalex" in paper_id.lower()):
        row = await src.openalex_work(paper_id)
        if row:
            row.pop("_referenced_works", None)
    if not row:
        return {"error": "not_found", "detail": "Paper not found (ingests recent papers daily; try search_papers)"}
    return {"paper": row}


async def do_citation_graph(paper_id, direction, depth, *, agent_key, payment_tx=None, api_key=None):
    if not paper_id:
        return {"error": "bad_request", "detail": "paper_id is required"}
    direction = (direction or "citations").lower()
    dec = await payment_gate.precheck("citation_graph", {"paper_id": paper_id, "direction": direction},
                                      config.PRICE_CITATION, agent_key, payment_tx, api_key)
    if dec["gate"] == "blocked":
        return dec["body"]
    if direction == "references":
        work = await src.openalex_work(paper_id)
        refs = (work or {}).get("_referenced_works") or []
        papers = await src.openalex_works_by_ids(refs[:50])
    else:
        papers = await src.openalex_citations(paper_id)
    out = [{"paper_id": p.get("paper_id"), "title": p.get("title"), "year": p.get("year"),
            "venue": p.get("venue"), "citation_count": p.get("citation_count"),
            "source_url": p.get("source_url")} for p in papers if p]
    return {"paper_id": paper_id, "direction": direction, "count": len(out),
            "papers": out, "billing": _billing(dec)}


async def do_author(author_name, author_id, *, agent_key, payment_tx=None, api_key=None):
    if not (author_name or author_id):
        return {"error": "bad_request", "detail": "author_name or author_id is required"}
    dec = await payment_gate.precheck("author_profile", {"name": author_name, "id": author_id},
                                      config.PRICE_AUTHOR, agent_key, payment_tx, api_key)
    if dec["gate"] == "blocked":
        return dec["body"]
    prof = await supa.author_by(author_id=author_id, name=author_name)
    if not prof:
        prof = await src.openalex_author(name=author_name, author_id=author_id)
        if prof:
            await supa.upsert_authors([prof])
    if not prof:
        return {"error": "not_found", "detail": "Author not found"}
    # top recent papers by this author from our table
    top = await supa.search_papers(query=prof.get("name"), limit=10)
    return {"author": prof, "recent_papers": [{"title": p.get("title"), "year": p.get("year"),
                                               "citation_count": p.get("citation_count")} for p in top[:10]],
            "billing": _billing(dec)}


async def do_trending(field, days, metric, *, agent_key, payment_tx=None, api_key=None):
    days = min(max(int(days or 30), 1), 365)
    metric = (metric or "citations").lower()
    dec = await payment_gate.precheck("trending_research", {"field": field, "days": days, "metric": metric},
                                      config.PRICE_TRENDING, agent_key, payment_tx, api_key)
    if dec["gate"] == "blocked":
        return dec["body"]
    order = "citation_count" if metric in ("citations", "social") else "publication_date"
    rows = await supa.trending(field=field, since=_days_ago(days), order=order, limit=200)
    topic_counts = Counter()
    for r in rows:
        for c in (r.get("categories") or []):
            topic_counts[c] += 1
    top_papers = sorted(rows, key=lambda r: (r.get("citation_count") or 0), reverse=True)[:15]
    return {
        "field": field, "days": days, "metric": metric, "papers_in_window": len(rows),
        "trending_topics": [{"topic": t, "papers": n} for t, n in topic_counts.most_common(15)],
        "top_papers": [{"title": p.get("title"), "venue": p.get("venue"), "year": p.get("year"),
                        "citation_count": p.get("citation_count"), "source_url": p.get("source_url")}
                       for p in top_papers],
        "billing": _billing(dec),
    }


async def do_similar(query, paper_id, *, agent_key, payment_tx=None, api_key=None):
    if not (query or paper_id):
        return {"error": "bad_request", "detail": "query or paper_id is required"}
    import hashlib
    key = query or paper_id
    dec = await payment_gate.precheck("similar_papers", {"k": hashlib.sha256(key.encode()).hexdigest()[:16]},
                                      config.PRICE_SIMILAR, agent_key, payment_tx, api_key)
    if dec["gate"] == "blocked":
        return dec["body"]
    text = query
    if not text and paper_id:
        p = await supa.paper_by(paper_id=paper_id)
        if not p:
            return {"error": "not_found", "detail": "paper_id not in dataset; pass a query string instead"}
        text = f"{p.get('title') or ''}. {p.get('abstract') or ''}"
    vec = await asyncio.to_thread(embed.embed_one, text)
    if vec is None:
        return {"error": "embedding_unavailable", "detail": "Could not embed the query"}
    matches = await supa.match_papers(vec, 10)
    return {"query": (query or f"paper:{paper_id}")[:200], "count": len(matches),
            "results": matches, "method": "pgvector cosine similarity on title+abstract embeddings",
            "billing": _billing(dec)}


def mint_info():
    return {
        "network": "FoundryNet Data Network", **mint_integration.network_feed_block(),
        "message": "Attest your agent's literature review / research with MINT Protocol for verifiable proof.",
        "mint_protocol": {"mcp_endpoint": config.MINT_MCP_URL, "info_url": config.MINT_INFO_URL,
                          "tools": ["mint_register", "mint_attest", "mint_verify",
                                    "mint_rate", "mint_recommend", "mint_discover"]},
        "see_also": config.SISTER_SERVERS,
    }


# ── Live network footer on paid responses (added 2026-06-20) ──────────────────
def _net_footer(_fn):
    import functools

    @functools.wraps(_fn)
    async def _wrapped(*a, **k):
        result = await _fn(*a, **k)
        if isinstance(result, dict) and "error" not in result and "payment_required" not in result:
            try:
                result["foundrynet_network"] = await asyncio.to_thread(mint_integration.network_heartbeat)
            except Exception:  # noqa: BLE001
                pass
        return result

    return _wrapped


for _nf in ("do_search", "do_citation_graph", "do_author", "do_trending", "do_similar"):
    if _nf in globals():
        globals()[_nf] = _net_footer(globals()[_nf])
