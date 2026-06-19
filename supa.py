"""Supabase PostgREST client for academic-intel-mcp (standalone project)."""
from __future__ import annotations

import logging
from typing import Optional

import config
from http_util import request_json

logger = logging.getLogger("acad.supa")


def configured() -> bool:
    return bool(config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY)


def _headers(extra: Optional[dict] = None) -> dict:
    h = {"apikey": config.SUPABASE_SERVICE_KEY,
         "Authorization": f"Bearer {config.SUPABASE_SERVICE_KEY}",
         "Content-Type": "application/json", "Accept": "application/json"}
    if extra:
        h.update(extra)
    return h


def _url(path: str) -> str:
    return f"{config.SUPABASE_URL}/rest/v1/{path}"


async def select(table: str, params: dict) -> list:
    if not configured():
        return []
    r = await request_json("GET", _url(table), headers=_headers(), params=params,
                           timeout=config.REQUEST_TIMEOUT)
    return r if isinstance(r, list) else []


async def rpc(fn: str, body: dict):
    if not configured():
        return None
    return await request_json("POST", _url(f"rpc/{fn}"), headers=_headers(), body=body,
                              timeout=config.REQUEST_TIMEOUT)


async def _bulk_upsert(table: str, rows: list, on_conflict: str) -> int:
    if not configured() or not rows:
        return 0
    seen, deduped = set(), []
    keys = on_conflict.split(",")
    for r in rows:
        k = tuple(r.get(c) for c in keys)
        if any(x is None for x in k) or k in seen:
            continue
        seen.add(k)
        deduped.append(r)
    allkeys = set()
    for r in deduped:
        allkeys.update(r.keys())
    deduped = [{k: r.get(k) for k in allkeys} for r in deduped]
    written = 0
    for i in range(0, len(deduped), 50):
        resp = await request_json("POST", _url(table),
                                  headers=_headers({"Prefer": "resolution=merge-duplicates,return=minimal"}),
                                  params={"on_conflict": on_conflict},
                                  body=deduped[i:i + 50], timeout=max(config.REQUEST_TIMEOUT, 60))
        if isinstance(resp, dict) and resp.get("error"):
            logger.warning(f"upsert {table} chunk {i}: {str(resp)[:200]}")
        else:
            written += len(deduped[i:i + 50])
    return written


async def upsert_papers(rows: list) -> int:
    return await _bulk_upsert("papers", rows, "source,paper_id")


async def upsert_authors(rows: list) -> int:
    return await _bulk_upsert("author_profiles", rows, "author_id")


_PFIELDS = ("source,paper_id,doi,title,abstract,authors,year,publication_date,venue,categories,"
            "citation_count,reference_count,influential_citation_count,is_open_access,pdf_url,"
            "tldr,source_url")


# ── reads ─────────────────────────────────────────────────────────────────────
async def search_papers(*, query=None, year_from=None, year_to=None, field=None, venue=None,
                        min_citations=None, open_access_only=None, limit=25) -> list:
    p = {"select": _PFIELDS, "order": "citation_count.desc.nullslast",
         "limit": str(min(max(int(limit or 25), 1), 100))}
    if query:
        kw = query.replace("*", "").replace(",", " ")
        p["or"] = f"(title.ilike.*{kw}*,abstract.ilike.*{kw}*)"
    if year_from and year_to:
        p["and"] = f"(year.gte.{year_from},year.lte.{year_to})"
    elif year_from:
        p["year"] = f"gte.{year_from}"
    elif year_to:
        p["year"] = f"lte.{year_to}"
    if field:
        p["categories"] = f'cs.["{field}"]'
    if venue:
        p["venue"] = f"ilike.*{venue}*"
    if min_citations is not None:
        p["citation_count"] = f"gte.{min_citations}"
    if open_access_only:
        p["is_open_access"] = "eq.true"
    return await select("papers", p)


async def paper_by(*, paper_id=None, doi=None, title=None) -> Optional[dict]:
    if paper_id:
        rows = await select("papers", {"select": _PFIELDS, "paper_id": f"eq.{paper_id}", "limit": "1"})
        if rows:
            return rows[0]
    if doi:
        rows = await select("papers", {"select": _PFIELDS, "doi": f"eq.{doi}", "limit": "1"})
        if rows:
            return rows[0]
    if title:
        rows = await select("papers", {"select": _PFIELDS, "title": f"ilike.*{title.replace('*','')}*", "limit": "1"})
        if rows:
            return rows[0]
    return None


async def match_papers(embedding: list, match_count: int = 10) -> list:
    vec = "[" + ",".join(f"{x:.6f}" for x in embedding) + "]"
    r = await rpc("match_papers", {"query_embedding": vec, "match_count": match_count})
    return r if isinstance(r, list) else []


async def trending(*, field=None, since=None, order="citation_count", limit=25) -> list:
    p = {"select": _PFIELDS, "order": f"{order}.desc.nullslast", "limit": str(limit)}
    if since:
        p["publication_date"] = f"gte.{since}"
    if field:
        p["categories"] = f'cs.["{field}"]'
    return await select("papers", p)


async def author_by(*, author_id=None, name=None) -> Optional[dict]:
    if author_id:
        rows = await select("author_profiles", {"select": "*", "author_id": f"eq.{author_id}", "limit": "1"})
        if rows:
            return rows[0]
    if name:
        rows = await select("author_profiles", {"select": "*", "name": f"ilike.*{name}*",
                                                "order": "citation_count.desc.nullslast", "limit": "1"})
        if rows:
            return rows[0]
    return None


# ── free-tier + payments ──────────────────────────────────────────────────────
async def claim_free_query(agent_key: str, day: str, cap: int) -> Optional[dict]:
    r = await rpc("acad_claim_free_query", {"p_agent_key": agent_key, "p_day": day, "p_cap": cap})
    if isinstance(r, dict) and "allowed" in r:
        return r
    if isinstance(r, list) and r and isinstance(r[0], dict):
        return r[0]
    return None


async def payment_tx_used(tx_signature: str) -> bool:
    rows = await select("acad_payments", {"tx_signature": f"eq.{tx_signature}",
                                          "select": "tx_signature", "limit": "1"})
    return bool(rows)


async def insert_payment(row: dict) -> dict:
    if not configured():
        return {"error": "not_configured"}
    r = await request_json("POST", _url("acad_payments"),
                           headers=_headers({"Prefer": "return=minimal"}),
                           body=row, timeout=config.REQUEST_TIMEOUT)
    if isinstance(r, dict) and r.get("error"):
        return r
    return {"data": [row]}
