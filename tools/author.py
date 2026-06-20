from typing import Optional

import core
import identity


def register(mcp) -> None:
    @mcp.tool
    async def author_profile(
        author_name: Optional[str] = None,
        author_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        payment_tx: Optional[str] = None,
    ) -> dict:
        """Analyze an author's research profile from OpenAlex — h-index, paper count,
        total citations, primary field, affiliation, and recent papers. Citation
        analysis for evaluating academic authors in a literature review.

        PAID: $0.01 USDC per query after the daily free allowance (25/day). On a
        402, pay the returned Solana memo and re-call with the SAME args plus
        payment_tx=<signature>. An Authorization: Bearer fnet_ key bypasses it.

        Args:
            author_name: the author's name (best match).
            author_id: an OpenAlex author id (Axxxx) for an exact lookup.
            agent_id: stable id for your agent (scopes the free-tier counter).
            payment_tx: Solana tx signature, when re-calling after a 402.
        """
        return await core.do_author(author_name, author_id,
                                    agent_key=identity.resolve_agent_key(agent_id),
                                    payment_tx=payment_tx, api_key=identity.bearer())
