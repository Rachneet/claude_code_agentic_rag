-- ============================================
-- Module 6: Multi-Format Storage Support
-- Run this in Supabase SQL Editor
-- Updates the documents bucket to accept PDF, DOCX, and HTML files
-- ============================================

update storage.buckets
set allowed_mime_types = array[
  'text/plain',
  'text/markdown',
  'text/csv',
  'application/json',
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/html'
]
where id = 'documents';
