-- Academic Research Intelligence — schema for academic_aggregator + academic-intel-mcp.
-- Standalone Supabase project. Idempotent. pgvector for similar-paper search.

create extension if not exists vector;
create extension if not exists pg_trgm;

create table if not exists papers (
  id            uuid primary key default gen_random_uuid(),
  source        text not null,        -- semantic_scholar | arxiv | pubmed | openalex
  paper_id      text not null,        -- source-specific id
  doi           text,
  title         text,
  abstract      text,
  authors       jsonb,                -- [{name, author_id, affiliation}]
  year          integer,
  publication_date date,
  venue         text,
  categories    jsonb,                -- arxiv categories / fields of study
  citation_count integer,
  reference_count integer,
  influential_citation_count integer,
  is_open_access boolean,
  pdf_url       text,
  tldr          text,
  embedding     vector(384),          -- fastembed bge-small on title+abstract
  source_url    text,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (source, paper_id)
);
create index if not exists idx_papers_pubdate on papers (publication_date desc nulls last);
create index if not exists idx_papers_year on papers (year desc nulls last);
create index if not exists idx_papers_cites on papers (citation_count desc nulls last);
create index if not exists idx_papers_doi on papers (doi);
create index if not exists idx_papers_title_trgm on papers using gin (title gin_trgm_ops);
create index if not exists idx_papers_cats on papers using gin (categories);
create index if not exists idx_papers_embedding on papers using hnsw (embedding vector_cosine_ops);

create or replace function match_papers(query_embedding text, match_count int default 10)
returns table (paper_id text, source text, title text, abstract text, authors jsonb,
               year integer, venue text, citation_count integer, pdf_url text,
               source_url text, similarity float)
language sql stable as $$
  select p.paper_id, p.source, p.title, p.abstract, p.authors, p.year, p.venue,
         p.citation_count, p.pdf_url, p.source_url,
         1 - (p.embedding <=> query_embedding::vector) as similarity
  from papers p
  where p.embedding is not null
  order by p.embedding <=> query_embedding::vector
  limit match_count;
$$;

-- ── author_profiles ──────────────────────────────────────────────────────────
create table if not exists author_profiles (
  author_id        text primary key,
  name             text,
  affiliation      text,
  h_index          integer,
  paper_count      integer,
  citation_count   integer,
  primary_field    text,
  recent_papers_90d integer,
  updated_at       timestamptz not null default now()
);
create index if not exists idx_authors_name on author_profiles using gin (name gin_trgm_ops);

-- ── free-tier counter + payments ─────────────────────────────────────────────
create table if not exists acad_query_usage (
  agent_key text not null, day date not null,
  count integer not null default 0, updated_at timestamptz not null default now(),
  primary key (agent_key, day)
);
create or replace function acad_claim_free_query(p_agent_key text, p_day date, p_cap integer)
returns jsonb language plpgsql as $$
declare cur integer; ok boolean;
begin
  insert into acad_query_usage (agent_key, day, count, updated_at)
  values (p_agent_key, p_day, 0, now())
  on conflict (agent_key, day) do nothing;
  select count into cur from acad_query_usage
    where agent_key = p_agent_key and day = p_day for update;
  if cur < p_cap then
    update acad_query_usage set count = count + 1, updated_at = now()
      where agent_key = p_agent_key and day = p_day;
    ok := true; cur := cur + 1;
  else ok := false; end if;
  return jsonb_build_object('allowed', ok, 'count', cur, 'cap', p_cap);
end; $$;

create table if not exists acad_payments (
  tx_signature text primary key, intent text, agent_key text, tool text,
  amount_usdc numeric, payer_wallet text, recipient text, status text,
  block_time bigint, created_at timestamptz not null default now()
);
