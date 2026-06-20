from typing import Optional

import core
import identity


def register(mcp) -> None:
    @mcp.tool
    async def citation_graph(
        paper_id: str,
        direction: str = "citations",
        depth: Optional[int] = 1,
        agent_id: Optional[str] = None,
        payment_tx: Optional[str] = None,
    ) -> dict:
        """Analyze the citation graph for a paper via live OpenAlex — list the papers
        citing it ("citations") or the papers it references ("references"). Citation
        analysis for tracing influence and prior work in a literature review.

        PAID: $0.01 USDC per query after the daily free allowance (25/day). On a
        402, pay the returned Solana memo and re-call with the SAME args plus
        payment_tx=<signature>. An Authorization: Bearer fnet_ key bypasses it.

        Args:
            paper_id: an OpenAlex work id (Wxxxx) — from a search/detail result's source.
            direction: "citations" (who cites this) or "references" (what this cites).
            depth: reserved (depth 1).
            agent_id: stable id for your agent (scopes the free-tier counter).
            payment_tx: Solana tx signature, when re-calling after a 402.
        """
        return await core.do_citation_graph(paper_id, direction, depth,
                                            agent_key=identity.resolve_agent_key(agent_id),
                                            payment_tx=payment_tx, api_key=identity.bearer())
