-- ============================================
-- Module 2: Storage Bucket for Documents
-- Run this in Supabase SQL Editor AFTER 002_documents_and_vectors.sql
-- ============================================

-- Create private storage bucket for documents (10MB limit)
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'documents',
  'documents',
  false,
  10485760,  -- 10MB
  array['text/plain', 'text/markdown', 'text/csv', 'application/json']
);

-- Storage RLS: Users can upload to their own folder
create policy "Users can upload to own folder"
  on storage.objects for insert
  with check (
    bucket_id = 'documents'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

-- Storage RLS: Users can read from their own folder
create policy "Users can read own folder"
  on storage.objects for select
  using (
    bucket_id = 'documents'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

-- Storage RLS: Users can delete from their own folder
create policy "Users can delete from own folder"
  on storage.objects for delete
  using (
    bucket_id = 'documents'
    and (storage.foldername(name))[1] = auth.uid()::text
  );
