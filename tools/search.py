from typing import Optional

import core
import identity


def register(mcp) -> None:
    @mcp.tool
    async def search_papers(
        query: str,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        field: Optional[str] = None,
        venue: Optional[str] = None,
        min_citations: Optional[int] = None,
        open_access_only: Optional[bool] = None,
        limit: int = 25,
        agent_id: Optional[str] = None,
        payment_tx: Optional[str] = None,
    ) -> dict:
        """Search academic papers / scientific literature by query, year range,
        field, venue, citation count, or open-access — for research and literature
        review. Returns title, authors, abstract, citation count (sorted by cites).

        PAID: $0.01 USDC per query after a daily free allowance (25/day). On a 402,
        pay the returned Solana memo and re-call with the SAME args plus
        payment_tx=<signature>. agent_id scopes your allowance; an Authorization:
        Bearer fnet_ key bypasses it.

        Args:
            query: free-text over title + abstract.
            year_from / year_to: publication year bounds.
            field: field-of-study / category tag (e.g. "Machine learning").
            venue: journal/conference name, partial match.
            min_citations: minimum citation count.
            open_access_only: true → only open-access papers.
            limit: max rows (1-100, default 25).
            agent_id: stable id for your agent (scopes the free-tier counter).
            payment_tx: Solana tx signature, when re-calling after a 402.
        """
        filters = {"query": query, "year_from": year_from, "year_to": year_to, "field": field,
                   "venue": venue, "min_citations": min_citations,
                   "open_access_only": open_access_only, "limit": limit}
        return await core.do_search(filters, agent_key=identity.resolve_agent_key(agent_id),
                                    payment_tx=payment_tx, api_key=identity.bearer())
