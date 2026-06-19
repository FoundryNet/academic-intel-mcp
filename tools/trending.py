from typing import Optional

import core
import identity


def register(mcp) -> None:
    @mcp.tool
    async def trending_research(
        field: Optional[str] = None,
        days: int = 30,
        metric: str = "citations",
        agent_id: Optional[str] = None,
        payment_tx: Optional[str] = None,
    ) -> dict:
        """Trending research — the most-cited recent papers and the topics with the
        highest publication volume in a window, optionally scoped to a field.

        PAID: $0.01 USDC per query after the daily free allowance (25/day). On a
        402, pay the returned Solana memo and re-call with the SAME args plus
        payment_tx=<signature>. An Authorization: Bearer fnet_ key bypasses it.

        Args:
            field: optional field-of-study filter.
            days: look-back window (1-365, default 30).
            metric: "citations" (most-cited) or "volume" (publication volume).
            agent_id: stable id for your agent (scopes the free-tier counter).
            payment_tx: Solana tx signature, when re-calling after a 402.
        """
        return await core.do_trending(field, days, metric,
                                      agent_key=identity.resolve_agent_key(agent_id),
                                      payment_tx=payment_tx, api_key=identity.bearer())
