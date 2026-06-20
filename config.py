"""Env-driven configuration for academic-intel-mcp.

Academic research intelligence over free scholarly sources — OpenAlex (primary,
keyless) + arXiv + PubMed, with Semantic Scholar as an optional enhancement (TLDR/
relevance via S2_API_KEY; keyless S2 rate-limits hard). Papers cached in a
standalone Supabase project with pgvector (fastembed) for similar-paper search.
7 tools, x402 metered. Part of the FoundryNet Data Network.

Required:
  SUPABASE_URL, SUPABASE_SERVICE_KEY
Optional:
  S2_API_KEY           Semantic Scholar key (TLDR + relevance; else throttled/skipped)
  OPENALEX_MAILTO      polite-pool email for OpenAlex (default hello@foundrynet.io)
  PORT, REQUEST_TIMEOUT, FREE_TIER_DAILY (25), AGG_HOUR_UTC (12 ≈4am PT)
  LOOKBACK_HOURS (48), EMBED_MODEL, PRICE_*
"""
from __future__ import annotations

import os


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def _flag(name: str, default: bool) -> bool:
    return _env(name, "true" if default else "false").strip().lower() in ("1", "true", "yes", "on")


SUPABASE_URL         = _env("SUPABASE_URL", "https://uwausvajwxymmnofhqqn.supabase.co").rstrip("/")
SUPABASE_SERVICE_KEY = _env("SUPABASE_SERVICE_KEY")

PORT            = int(_env("PORT", "8080"))
REQUEST_TIMEOUT = int(_env("REQUEST_TIMEOUT", "30"))

# ── Sources ──────────────────────────────────────────────────────────────────
OPENALEX_API   = "https://api.openalex.org/works"
OPENALEX_AUTHORS = "https://api.openalex.org/authors"
OPENALEX_MAILTO = _env("OPENALEX_MAILTO", "hello@foundrynet.io")
ARXIV_API      = "https://export.arxiv.org/api/query"
PUBMED_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
S2_API         = "https://api.semanticscholar.org/graph/v1"
S2_API_KEY     = _env("S2_API_KEY")
SOURCE_USER_AGENT = _env("SOURCE_USER_AGENT", "FoundryNet Data Network hello@foundrynet.io")

LOOKBACK_HOURS = int(_env("LOOKBACK_HOURS", "48"))
AGG_HOUR_UTC   = int(_env("AGG_HOUR_UTC", "12"))   # ≈4am PT
# OpenAlex concept ids for high-activity fields (AI, ML, NLP, security, comp-bio, stats).
OPENALEX_CONCEPTS = _env("OPENALEX_CONCEPTS",
                         "C154945302,C119857082,C204321447,C38652104,C70721500,C105795698")
ARXIV_CATEGORIES = _env("ARXIV_CATEGORIES", "cs.AI,cs.LG,cs.CL,cs.CR,q-bio,stat.ML").split(",")

# ── Embeddings (fastembed) ───────────────────────────────────────────────────
EMBED_MODEL = _env("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
EMBED_DIM   = int(_env("EMBED_DIM", "384"))

# ── x402 per-tool pricing ────────────────────────────────────────────────────
X402_ENABLED      = _flag("X402_ENABLED", True)
SOLANA_WALLET     = _env("SOLANA_WALLET", "wUumjWWvtFEr69qkTw3wHNVQVxLA8DTyJSyVgGmLThd")
PAYMENT_RECIPIENT = _env("PAYMENT_RECIPIENT", SOLANA_WALLET).strip()
PAYMENT_VERIFY_RPC = _env("PAYMENT_VERIFY_RPC", "https://api.mainnet-beta.solana.com").rstrip("/")
PAYMENT_USDC_MINT  = _env("PAYMENT_USDC_MINT", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v").strip()
PAYMENT_EXPIRY_SECONDS = int(_env("PAYMENT_EXPIRY_SECONDS", "300"))

FREE_TIER_DAILY = int(_env("FREE_TIER_DAILY", "25"))

PRICE_SEARCH    = float(_env("PRICE_SEARCH", "0.01"))
PRICE_CITATION  = float(_env("PRICE_CITATION", "0.01"))
PRICE_AUTHOR    = float(_env("PRICE_AUTHOR", "0.01"))
PRICE_TRENDING  = float(_env("PRICE_TRENDING", "0.01"))
PRICE_SIMILAR   = float(_env("PRICE_SIMILAR", "0.02"))

# ── FoundryNet Data Network cross-promo ──────────────────────────────────────
MINT_MCP_URL  = _env("MINT_MCP_URL", "https://mint-mcp-production.up.railway.app/mcp")
MINT_INFO_URL = _env("MINT_INFO_URL", "https://mint.foundrynet.io")
SISTER_SERVERS = {
    "mint-mcp":                "https://mint-mcp-production.up.railway.app/mcp",
    "foundrynet-mcp":          "https://foundrynet-mcp-production.up.railway.app/mcp",
    "gov-contracts-mcp":       "https://gov-contracts-mcp-production.up.railway.app/mcp",
    "brand-intel-mcp":         "https://brand-intel-mcp-production.up.railway.app/mcp",
    "patent-intel-mcp":        "https://patent-intel-mcp-production.up.railway.app/mcp",
    "financial-signals-mcp":   "https://financial-signals-mcp-production.up.railway.app/mcp",
    "weather-intel-mcp":       "https://weather-intel-mcp-production.up.railway.app/mcp",
    "cyber-intel-mcp":         "https://cyber-intel-mcp-production.up.railway.app/mcp",
    "compliance-mcp":          "https://compliance-mcp-production.up.railway.app/mcp",
    "fact-check-mcp":          "https://fact-check-mcp-production.up.railway.app/mcp",
    "oss-intel-mcp":           "https://oss-intel-mcp-production.up.railway.app/mcp",
    "social-intel-mcp":        "https://social-intel-mcp-production.up.railway.app/mcp",
    "crypto-intel-mcp":        "https://crypto-intel-mcp-production.up.railway.app/mcp",
    "market-data-mcp":         "https://market-data-mcp-production.up.railway.app/mcp",
    "email-verify-mcp":        "https://email-verify-mcp-production.up.railway.app/mcp",
    "currency-intel-mcp":      "https://currency-intel-mcp-production.up.railway.app/mcp",
}

PUBLIC_MCP_URL = _env("PUBLIC_MCP_URL", "https://academic-intel-mcp-production.up.railway.app/mcp")
