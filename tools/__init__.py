"""academic-intel-mcp tools — one per file.

  search_papers     ($0.01)  paper search w/ citations + relevance
  paper_detail      (free)   full paper record — drives adoption
  citation_graph    ($0.01)  citing / referenced papers (live OpenAlex)
  author_profile    ($0.01)  h-index, papers, citations, field, recent activity
  trending_research ($0.01)  trending topics + fastest-rising papers
  similar_papers    ($0.02)  semantic related-work finder (pgvector, premium)
  mint_info         (free)   FoundryNet Data Network + MINT cross-promo
"""
from . import search as search_tool
from . import detail as detail_tool
from . import citations as citations_tool
from . import author as author_tool
from . import trending as trending_tool
from . import similar as similar_tool
from . import mint as mint_tool


def register_all(mcp) -> None:
    for m in (search_tool, detail_tool, citations_tool, author_tool, trending_tool,
              similar_tool, mint_tool):
        m.register(mcp)
