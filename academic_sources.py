"""Free scholarly sources + mapping.

OpenAlex (primary, keyless, rich) + arXiv (preprints) + PubMed (biomed) for daily
ingestion; Semantic Scholar optional (TLDR enrichment via S2_API_KEY; keyless S2
rate-limits hard). Live OpenAlex powers citation_graph + author_profile fallback.
"""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import config
from http_util import request_json

logger = logging.getLogger("acad.src")

_UA = {"User-Agent": config.SOURCE_USER_AGENT}


def _oa_id(url: str) -> str:
    return (url or "").rstrip("/").split("/")[-1]


def _reconstruct_abstract(inv: dict) -> str | None:
    if not inv:
        return None
    positions = []
    for word, idxs in inv.items():
        for i in idxs:
            positions.append((i, word))
    if not positions:
        return None
    positions.sort()
    return " ".join(w for _, w in positions)[:4000]


# ── OpenAlex ──────────────────────────────────────────────────────────────────
def map_openalex(w: dict) -> dict | None:
    wid = _oa_id(w.get("id"))
    if not wid:
        return None
    # Drop future-dated metadata junk (OpenAlex carries preprints with bogus
    # publication years like 2050/2036); allow current year + 1 for in-press.
    yr = w.get("publication_year")
    if isinstance(yr, int) and yr > datetime.now(timezone.utc).year + 1:
        return None
    if not w.get("title"):
        return None
    authors = []
    for a in (w.get("authorships") or [])[:30]:
        au = a.get("author") or {}
        insts = a.get("institutions") or []
        authors.append({"name": au.get("display_name"), "author_id": _oa_id(au.get("id")),
                        "affiliation": (insts[0].get("display_name") if insts else None)})
    cats = [c.get("display_name") for c in (w.get("concepts") or [])[:6] if c.get("display_name")]
    loc = w.get("primary_location") or {}
    oa = w.get("open_access") or {}
    doi = (w.get("doi") or "").replace("https://doi.org/", "") or None
    return {
        "source": "openalex", "paper_id": wid, "doi": doi, "title": w.get("title"),
        "abstract": _reconstruct_abstract(w.get("abstract_inverted_index")),
        "authors": authors or None, "year": w.get("publication_year"),
        "publication_date": w.get("publication_date"),
        "venue": (loc.get("source") or {}).get("display_name"),
        "categories": cats or None, "citation_count": w.get("cited_by_count"),
        "reference_count": len(w.get("referenced_works") or []),
        "influential_citation_count": None, "is_open_access": oa.get("is_oa"),
        "pdf_url": oa.get("oa_url"), "tldr": None,
        "source_url": w.get("id"),
    }


async def fetch_openalex(date_from: str, max_pages: int = 5) -> list:
    rows, cursor = [], "*"
    flt = f"from_publication_date:{date_from},concepts.id:{config.OPENALEX_CONCEPTS.replace(',', '|')}"
    for page in range(max_pages):
        params = {"filter": flt, "per-page": "200", "cursor": cursor,
                  "sort": "publication_date:desc", "mailto": config.OPENALEX_MAILTO}
        r = await request_json("GET", config.OPENALEX_API, headers=_UA, params=params,
                               timeout=max(config.REQUEST_TIMEOUT, 45))
        if not isinstance(r, dict) or "results" not in r:
            logger.warning(f"OpenAlex page {page} error: {str(r)[:160]}")
            break
        for w in r["results"]:
            m = map_openalex(w)
            if m:
                rows.append(m)
        cursor = (r.get("meta") or {}).get("next_cursor")
        logger.info(f"OpenAlex page {page + 1}: +{len(r['results'])} (total {len(rows)})")
        if not cursor or not r["results"]:
            break
    logger.info(f"OpenAlex: {len(rows)} works since {date_from}")
    return rows


async def openalex_works_by_ids(ids: list) -> list:
    if not ids:
        return []
    flt = "openalex:" + "|".join(_oa_id(i) for i in ids[:50])
    r = await request_json("GET", config.OPENALEX_API, headers=_UA,
                           params={"filter": flt, "per-page": "50", "mailto": config.OPENALEX_MAILTO},
                           timeout=config.REQUEST_TIMEOUT)
    return [map_openalex(w) for w in (r.get("results") or [])] if isinstance(r, dict) else []


async def openalex_citations(work_id: str, limit=25) -> list:
    r = await request_json("GET", config.OPENALEX_API, headers=_UA,
                           params={"filter": f"cites:{_oa_id(work_id)}", "per-page": str(limit),
                                   "sort": "cited_by_count:desc", "mailto": config.OPENALEX_MAILTO},
                           timeout=config.REQUEST_TIMEOUT)
    return [map_openalex(w) for w in (r.get("results") or [])] if isinstance(r, dict) else []


async def openalex_work(work_id: str) -> dict | None:
    r = await request_json("GET", f"{config.OPENALEX_API}/{_oa_id(work_id)}", headers=_UA,
                           params={"mailto": config.OPENALEX_MAILTO}, timeout=config.REQUEST_TIMEOUT)
    if isinstance(r, dict) and r.get("id"):
        m = map_openalex(r)
        m["_referenced_works"] = r.get("referenced_works") or []
        return m
    return None


async def openalex_author(name=None, author_id=None) -> dict | None:
    if author_id:
        r = await request_json("GET", f"{config.OPENALEX_AUTHORS}/{_oa_id(author_id)}", headers=_UA,
                               params={"mailto": config.OPENALEX_MAILTO}, timeout=config.REQUEST_TIMEOUT)
        a = r if isinstance(r, dict) and r.get("id") else None
    else:
        r = await request_json("GET", config.OPENALEX_AUTHORS, headers=_UA,
                               params={"search": name, "per-page": "1", "mailto": config.OPENALEX_MAILTO},
                               timeout=config.REQUEST_TIMEOUT)
        res = (r.get("results") if isinstance(r, dict) else None) or []
        a = res[0] if res else None
    if not a:
        return None
    insts = a.get("last_known_institutions") or []
    xc = a.get("x_concepts") or []
    return {"author_id": _oa_id(a.get("id")), "name": a.get("display_name"),
            "affiliation": (insts[0].get("display_name") if insts else None),
            "h_index": (a.get("summary_stats") or {}).get("h_index"),
            "paper_count": a.get("works_count"), "citation_count": a.get("cited_by_count"),
            "primary_field": (xc[0].get("display_name") if xc else None)}


# ── arXiv ─────────────────────────────────────────────────────────────────────
_ATOM = "{http://www.w3.org/2005/Atom}"


async def fetch_arxiv(max_results: int = 200) -> list:
    cats = " OR ".join(f"cat:{c.strip()}" for c in config.ARXIV_CATEGORIES if c.strip())
    r = await request_json("GET", config.ARXIV_API, headers=_UA,
                           params={"search_query": cats, "max_results": str(max_results),
                                   "sortBy": "submittedDate", "sortOrder": "descending"},
                           timeout=max(config.REQUEST_TIMEOUT, 45))
    # arXiv returns Atom XML; request_json may wrap non-JSON as error — fetch raw.
    rows = []
    try:
        import httpx
        async with httpx.AsyncClient(timeout=45, headers=_UA) as c:
            resp = await c.get(config.ARXIV_API, params={"search_query": cats,
                               "max_results": str(max_results), "sortBy": "submittedDate",
                               "sortOrder": "descending"})
        root = ET.fromstring(resp.text)
        for e in root.findall(f"{_ATOM}entry"):
            rows.append(_map_arxiv(e))
    except Exception as ex:  # noqa: BLE001
        logger.warning(f"arXiv parse failed: {ex}")
    logger.info(f"arXiv: {len(rows)} preprints")
    return [x for x in rows if x]


def _map_arxiv(e) -> dict | None:
    def txt(tag):
        el = e.find(f"{_ATOM}{tag}")
        return el.text.strip() if el is not None and el.text else None
    raw_id = txt("id") or ""
    aid = raw_id.rstrip("/").split("/abs/")[-1].split("/")[-1]
    if not aid:
        return None
    authors = [{"name": a.find(f"{_ATOM}name").text, "author_id": None, "affiliation": None}
               for a in e.findall(f"{_ATOM}author") if a.find(f"{_ATOM}name") is not None]
    cats = [c.get("term") for c in e.findall("{http://arxiv.org/schemas/atom}primary_category")]
    cats += [c.get("term") for c in e.findall(f"{_ATOM}category")]
    pdf = None
    for ln in e.findall(f"{_ATOM}link"):
        if ln.get("title") == "pdf":
            pdf = ln.get("href")
    pub = txt("published")
    return {"source": "arxiv", "paper_id": aid, "doi": None, "title": (txt("title") or "").replace("\n", " ").strip(),
            "abstract": (txt("summary") or "").replace("\n", " ").strip(),
            "authors": authors or None, "year": int(pub[:4]) if pub else None,
            "publication_date": pub[:10] if pub else None, "venue": "arXiv",
            "categories": sorted(set(c for c in cats if c)) or None,
            "citation_count": None, "reference_count": None, "influential_citation_count": None,
            "is_open_access": True, "pdf_url": pdf, "tldr": None,
            "source_url": raw_id}


# ── PubMed (biomed, best-effort) ──────────────────────────────────────────────
async def fetch_pubmed(days: int = 2, retmax: int = 100) -> list:
    es = await request_json("GET", config.PUBMED_ESEARCH, headers=_UA,
                            params={"db": "pubmed", "term": f"\"last {days} days\"[EDAT]",
                                    "retmax": str(retmax), "retmode": "json",
                                    "tool": "foundrynet", "email": config.OPENALEX_MAILTO},
                            timeout=config.REQUEST_TIMEOUT)
    ids = ((es or {}).get("esearchresult") or {}).get("idlist") or []
    if not ids:
        return []
    import httpx
    rows = []
    try:
        async with httpx.AsyncClient(timeout=45, headers=_UA) as c:
            resp = await c.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
                               params={"db": "pubmed", "id": ",".join(ids[:retmax]),
                                       "retmode": "xml", "tool": "foundrynet", "email": config.OPENALEX_MAILTO})
        root = ET.fromstring(resp.text)
        for art in root.findall(".//PubmedArticle"):
            rows.append(_map_pubmed(art))
    except Exception as ex:  # noqa: BLE001
        logger.warning(f"PubMed parse failed: {ex}")
    logger.info(f"PubMed: {len(rows)} articles")
    return [x for x in rows if x]


def _map_pubmed(art) -> dict | None:
    pmid_el = art.find(".//PMID")
    pmid = pmid_el.text if pmid_el is not None else None
    if not pmid:
        return None
    title_el = art.find(".//ArticleTitle")
    abst = " ".join(a.text or "" for a in art.findall(".//AbstractText")).strip() or None
    journal = art.find(".//Journal/Title")
    year_el = art.find(".//PubDate/Year")
    authors = []
    for au in art.findall(".//Author")[:30]:
        ln, fn = au.find("LastName"), au.find("ForeName")
        nm = " ".join(x.text for x in (fn, ln) if x is not None and x.text)
        if nm:
            authors.append({"name": nm, "author_id": None, "affiliation": None})
    doi = None
    for idn in art.findall(".//ArticleId"):
        if idn.get("IdType") == "doi":
            doi = idn.text
    return {"source": "pubmed", "paper_id": pmid, "doi": doi,
            "title": title_el.text if title_el is not None else None, "abstract": abst,
            "authors": authors or None, "year": int(year_el.text) if (year_el is not None and year_el.text) else None,
            "publication_date": None, "venue": journal.text if journal is not None else None,
            "categories": ["biomedical"], "citation_count": None, "reference_count": None,
            "influential_citation_count": None, "is_open_access": None,
            "pdf_url": None, "tldr": None,
            "source_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"}
