from typing import Optional

import core


def register(mcp) -> None:
    @mcp.tool
    async def paper_detail(
        paper_id: Optional[str] = None,
        doi: Optional[str] = None,
        title: Optional[str] = None,
    ) -> dict:
        """Full record for a paper — abstract, all authors, venue, year, citation +
        reference counts, open-access PDF link, TLDR (when available). FREE. Provide
        a paper_id, a DOI, or a title.

        Args:
            paper_id: source paper id (e.g. an OpenAlex Wxxxx or arXiv id).
            doi: the DOI.
            title: a title to look up (best match).
        """
        return await core.do_detail(paper_id, doi, title)
