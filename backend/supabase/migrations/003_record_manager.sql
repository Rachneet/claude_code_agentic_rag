-- Add content_hash column for deduplication
alter table public.document_chunks add column content_hash text;

-- Unique index: same document cannot have two chunks with identical content
create unique index idx_document_chunks_doc_hash
  on public.document_chunks(document_id, content_hash);

-- Index for efficient ordered chunk retrieval per document
create index idx_document_chunks_doc_index
  on public.document_chunks(document_id, chunk_index);

-- Backfill existing chunks using pgcrypto (available in Supabase)
update public.document_chunks
  set content_hash = encode(digest(content, 'sha256'), 'hex')
  where content_hash is null;

-- Enforce NOT NULL after backfill
alter table public.document_chunks alter column content_hash set not null;
