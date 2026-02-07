-- ============================================
-- Module 2: Documents & Vector Storage
-- Run this in Supabase SQL Editor
-- ============================================

-- Enable pgvector extension
create extension if not exists vector with schema extensions;

-- Documents table (tracks uploaded files)
create table public.documents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade not null,
  filename text not null,
  file_size integer not null,
  mime_type text not null,
  status text not null default 'pending' check (status in ('pending', 'processing', 'completed', 'failed')),
  chunk_count integer default 0,
  storage_path text,
  error_message text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Document chunks table (stores text chunks + embeddings)
create table public.document_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid references public.documents(id) on delete cascade not null,
  user_id uuid references auth.users(id) on delete cascade not null,
  content text not null,
  chunk_index integer not null,
  embedding vector(384),
  token_count integer,
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

-- Indexes
create index idx_documents_user_id on public.documents(user_id);
create index idx_documents_status on public.documents(status);
create index idx_documents_created_at on public.documents(created_at desc);
create index idx_document_chunks_document_id on public.document_chunks(document_id);
create index idx_document_chunks_user_id on public.document_chunks(user_id);

-- HNSW index for fast cosine similarity search
create index idx_document_chunks_embedding on public.document_chunks
  using hnsw (embedding vector_cosine_ops);

-- RLS: Documents
alter table public.documents enable row level security;

create policy "Users can select own documents"
  on public.documents for select using (auth.uid() = user_id);
create policy "Users can insert own documents"
  on public.documents for insert with check (auth.uid() = user_id);
create policy "Users can update own documents"
  on public.documents for update using (auth.uid() = user_id);
create policy "Users can delete own documents"
  on public.documents for delete using (auth.uid() = user_id);

-- RLS: Document Chunks
alter table public.document_chunks enable row level security;

create policy "Users can select own document chunks"
  on public.document_chunks for select using (auth.uid() = user_id);
create policy "Users can insert own document chunks"
  on public.document_chunks for insert with check (auth.uid() = user_id);
create policy "Users can update own document chunks"
  on public.document_chunks for update using (auth.uid() = user_id);
create policy "Users can delete own document chunks"
  on public.document_chunks for delete using (auth.uid() = user_id);

-- Auto-update updated_at on documents
create trigger set_documents_updated_at
  before update on public.documents
  for each row execute function public.update_updated_at_column();

-- Similarity search RPC function
create or replace function public.match_document_chunks(
  query_embedding vector(384),
  match_user_id uuid,
  match_threshold float default 0.5,
  match_count int default 5
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
  order by dc.embedding <=> query_embedding
  limit match_count;
$$;

-- Enable Realtime for documents table (status updates)
alter publication supabase_realtime add table public.documents;
