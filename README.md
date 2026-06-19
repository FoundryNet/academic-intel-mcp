# Academic Research Intelligence MCP

**Academic research intelligence for AI agents** — paper search, scientific
literature, citation analysis, arXiv search, author metrics, trending research, and
a **semantic related-work finder** (pgvector). Built on free scholarly sources.

> Part of the **FoundryNet Data Network**. Attest your agent's literature review
> with [MINT Protocol](https://mint-mcp-production.up.railway.app/mcp). See also:
> **gov-contracts-mcp**, **brand-intel-mcp**, **patent-intel-mcp**,
> **financial-signals-mcp**, **weather-intel-mcp**, **compliance-mcp**, **cyber-intel-mcp**.

Live MCP endpoint (Streamable HTTP):
`https://academic-intel-mcp-production.up.railway.app/mcp`

## Tools

| Tool | Price | What it does |
|---|---|---|
| `search_papers` | $0.01 | Paper search by query/year/field/venue/citations/open-access |
| `paper_detail` | **free** | Full record — abstract, authors, citations, references, PDF |
| `citation_graph` | $0.01 | Papers citing this / referenced by it (live OpenAlex) |
| `author_profile` | $0.01 | h-index, papers, citations, primary field, recent activity |
| `trending_research` | $0.01 | Trending topics + most-cited recent papers |
| `similar_papers` | $0.02 | Semantic related-work finder via embeddings (pgvector) — premium |
| `mint_info` | **free** | FoundryNet Data Network + MINT Protocol |

**Free tier:** 25 paid-tool queries/day per agent. Then x402: the tool returns an
HTTP-402 with a Solana USDC payment memo — pay it, re-call with the same args plus
`payment_tx=<signature>`. An `Authorization: Bearer fnet_…` key bypasses the paywall.

## Sources

Daily (~4am PT): **OpenAlex** (primary, keyless, rich metadata + citations),
**arXiv** (CS/physics/math/bio preprints), **PubMed** (biomed). Abstracts are
embedded with **fastembed** (bge-small) for `similar_papers` (pgvector cosine).
`citation_graph` and `author_profile` resolve live from OpenAlex. **Semantic
Scholar** is an optional enhancement (TLDR/relevance via `S2_API_KEY`; keyless S2
rate-limits hard).

## Connect

Smithery: `@foundrynet/academic-intel` · MCP registry: `io.github.FoundryNet/academic-intel-mcp`

```json
{ "mcpServers": { "academic-intel": { "url": "https://academic-intel-mcp-production.up.railway.app/mcp" } } }
```

Built by [FoundryNet](https://foundrynet.io) · hello@foundrynet.io
