-- Migration 006: Granular ingestion status
-- Replaces single "processing" status with extracting → chunking → embedding stages

ALTER TABLE public.documents
  DROP CONSTRAINT IF EXISTS documents_status_check,
  ADD CONSTRAINT documents_status_check
    CHECK (status IN ('pending', 'extracting', 'chunking', 'embedding', 'completed', 'failed'));
