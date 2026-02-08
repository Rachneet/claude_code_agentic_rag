-- Migration 007: Hybrid Search (Full-Text Search infrastructure)
-- Adds tsvector column, GIN index, auto-populate trigger, and FTS RPC function

-- 1. Add tsvector column
ALTER TABLE public.document_chunks ADD COLUMN IF NOT EXISTS fts tsvector;

-- 2. GIN index for fast full-text search
CREATE INDEX IF NOT EXISTS idx_document_chunks_fts ON public.document_chunks USING gin (fts);

-- 3. Trigger function to auto-populate fts on INSERT/UPDATE
CREATE OR REPLACE FUNCTION public.document_chunks_fts_trigger()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.fts := to_tsvector('english', COALESCE(NEW.content, ''));
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_document_chunks_fts ON public.document_chunks;
CREATE TRIGGER trg_document_chunks_fts
  BEFORE INSERT OR UPDATE OF content ON public.document_chunks
  FOR EACH ROW EXECUTE FUNCTION public.document_chunks_fts_trigger();

-- 4. Backfill existing rows
UPDATE public.document_chunks SET fts = to_tsvector('english', COALESCE(content, '')) WHERE fts IS NULL;

-- 5. FTS RPC function
CREATE OR REPLACE FUNCTION public.match_document_chunks_fts(
  query_text text,
  match_user_id uuid,
  match_count int DEFAULT 5,
  metadata_filter jsonb DEFAULT NULL
)
RETURNS TABLE (
  id uuid,
  document_id uuid,
  content text,
  chunk_index int,
  token_count int,
  metadata jsonb,
  rank real
)
LANGUAGE sql STABLE AS $$
  SELECT
    dc.id,
    dc.document_id,
    dc.content,
    dc.chunk_index,
    dc.token_count,
    dc.metadata,
    ts_rank_cd(dc.fts, websearch_to_tsquery('english', query_text)) AS rank
  FROM public.document_chunks dc
  WHERE dc.user_id = match_user_id
    AND dc.fts @@ websearch_to_tsquery('english', query_text)
    AND (metadata_filter IS NULL OR dc.metadata @> metadata_filter)
  ORDER BY rank DESC
  LIMIT match_count;
$$;
