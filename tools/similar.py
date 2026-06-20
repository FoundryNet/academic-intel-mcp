from typing import Optional

import core
import identity


def register(mcp) -> None:
    @mcp.tool
    async def similar_papers(
        query: Optional[str] = None,
        paper_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        payment_tx: Optional[str] = None,
    ) -> dict:
        """Find related academic papers by semantic similarity — the "related work"
        finder for a literature review. Give a free-text query OR a paper_id and get
        the most similar papers via fastembed semantic similarity (pgvector). Premium.

        PAID: $0.02 USDC per query after the daily free allowance (25/day). On a
        402, pay the returned Solana memo and re-call with the SAME args plus
        payment_tx=<signature>. An Authorization: Bearer fnet_ key bypasses it.

        Args:
            query: free-text description of the topic / idea to match.
            paper_id: a paper id in the dataset to find neighbors of.
            agent_id: stable id for your agent (scopes the free-tier counter).
            payment_tx: Solana tx signature, when re-calling after a 402.
        """
        return await core.do_similar(query, paper_id,
                                     agent_key=identity.resolve_agent_key(agent_id),
                                     payment_tx=payment_tx, api_key=identity.bearer())
