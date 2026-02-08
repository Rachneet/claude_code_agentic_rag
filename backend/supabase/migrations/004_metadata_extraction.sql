-- ============================================
-- Module 5: Metadata Extraction
-- Run this in Supabase SQL Editor
-- ============================================

-- Add metadata column to documents table
alter table public.documents add column if not exists metadata jsonb default '{}'::jsonb;

-- GIN index on document_chunks.metadata for containment queries
create index if not exists idx_document_chunks_metadata
  on public.document_chunks using gin (metadata);

-- GIN index on documents.metadata
create index if not exists idx_documents_metadata
  on public.documents using gin (metadata);

-- Replace match_document_chunks with metadata filtering support
create or replace function public.match_document_chunks(
  query_embedding vector(384),
  match_user_id uuid,
  match_threshold float default 0.5,
  match_count int default 5,
  metadata_filter jsonb default null
)
returns table (
  id uuid,
  document_id uuid,
  content text,
  chunk_index int,
  token_count int,
  metadata jsonb,
  similarity float
)
language sql stable
as $$
  select
    dc.id,
    dc.document_id,
    dc.content,
    dc.chunk_index,
    dc.token_count,
    dc.metadata,
    1 - (dc.embedding <=> query_embedding) as similarity
  from public.document_chunks dc
  where dc.user_id = match_user_id
    and 1 - (dc.embedding <=> query_embedding) > match_threshold
    and (metadata_filter is null or dc.metadata @> metadata_filter)
  order by dc.embedding <=> query_embedding
  limit match_count;
$$;
