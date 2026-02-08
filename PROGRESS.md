# Progress

Track your progress through the masterclass. Update this file as you complete modules - Claude Code reads this to understand where you are in the project.

## Convention
- `[ ]` = Not started
- `[-]` = In progress
- `[x]` = Completed

## Modules

### Module 1: App Shell + Observability
- [x] Supabase schema + env templates
- [x] Backend scaffolding (Python + FastAPI + venv)
- [x] Supabase client + JWT auth dependency
- [x] Frontend scaffolding + Auth UI (React + Vite + Tailwind + shadcn)
- [x] Thread management (backend REST endpoints)
- [x] HuggingFace Inference client + LangSmith tracing
- [x] Chat service + SSE endpoint
- [x] Thread sidebar (frontend)
- [x] Chat view with streaming (frontend)
- [x] Full layout integration
- [x] Error handling + polish (markdown rendering, loading states, validation)
- [x] End-to-end testing (requires Supabase project + HF token configured)

### Module 2: BYO Retrieval + Memory
- [x] Database schema update (migration 002 — documents, document_chunks, pgvector, RLS, Realtime)
- [x] Supabase Storage bucket setup (documents bucket with RLS policies)
- [x] LLM provider abstraction layer (base ABC, factory, HF refactored to class)
- [x] Gemini provider implementation (google-genai SDK, streaming, tool calling)
- [x] Chat service refactored for provider abstraction
- [x] Embedding service (HF Inference API, all-MiniLM-L6-v2, 384 dims)
- [x] Text chunking logic (sentence-boundary aware, configurable size/overlap)
- [x] Document ingestion pipeline (upload, storage, background processing, list/delete)
- [x] Vector search / retrieval service (cosine similarity via pgvector RPC)
- [x] RAG chat integration (Gemini tool calling + HF context injection)
- [x] Ingestion UI (file upload, document list, Realtime status, view switching)
- [ ] End-to-end testing (requires running SQL migrations + storage setup in Supabase)

### Module 3: Multi-Provider Support
- [x] OpenRouter config (api key, model, base URL settings + .env.example)
- [x] OpenRouterProvider implementation (raw httpx, all 4 LLMProvider methods, tool calling)
- [x] Factory registration (openrouter branch in get_provider)
- [x] Capability-based tool calling (`supports_tools` property replaces provider name checks)
- [ ] End-to-end testing (requires OpenRouter API key configured)

### Module 4: Record Manager
- [x] SQL migration — content_hash column, unique index, backfill (003_record_manager.sql)
- [x] Record manager module (compute_content_hash, fetch, reconcile, apply)
- [x] Ingestion service refactored — hash-based reconciliation, only embed new chunks
- [x] Duplicate filename detection — reuse existing document record on re-upload
- [ ] End-to-end testing (requires running SQL migration 003 in Supabase)

### Module 5: Metadata Extraction
- [x] Metadata extraction module (DocumentMetadata model, LLM extraction, fallback)
- [x] SQL migration 004 (documents.metadata column, GIN indexes, updated match_document_chunks RPC with metadata_filter)
- [x] Ingestion pipeline integration (extract after chunking, store on document, propagate to chunks)
- [x] Retrieval with metadata filtering (metadata_filter param, context labels with title/type)
- [x] Chat tools updated (document_type and topic filter params, metadata-aware system prompt)
- [x] Frontend metadata display (DocumentMetadata type, badges on DocumentList, type filter dropdown)
- [ ] End-to-end testing (requires running SQL migration 004 in Supabase)

### Module 6: Multi-Format Support
- [x] Extraction dependencies (pypdf, python-docx, beautifulsoup4)
- [x] Text extractor module (extractors.py — PDF, DOCX, HTML, UTF-8 dispatcher)
- [x] Ingestion service wired to extractor (replaces raw UTF-8 decode)
- [x] Router updated for new MIME types (.pdf, .docx, .html, .htm)
- [x] Frontend file upload accepts new formats
- [x] SQL migration 005 (update storage bucket allowed_mime_types for PDF, DOCX, HTML)
- [ ] End-to-end testing (requires running SQL migration 005 in Supabase, then upload PDF, DOCX, HTML)

### Stage-Based Ingestion Progress
- [x] SQL migration 006 (expand status CHECK constraint: extracting, chunking, embedding)
- [x] Backend granular status updates (extracting → chunking → embedding stages)
- [x] Frontend types updated (new status union)
- [x] Step indicator UI (shows completed/current/pending stages during processing)
- [ ] End-to-end testing (requires running SQL migration 006 in Supabase)

### Module 7: Hybrid Search & Reranking
- [x] SQL migration 007 (fts tsvector column, GIN index, auto-populate trigger, backfill, FTS RPC function)
- [x] Config settings (reranker_enabled, reranker_model, hybrid_search_enabled)
- [x] Reranker module (HF Inference API cross-encoder, graceful fallback)
- [x] Hybrid retrieval (vector + FTS parallel search, Reciprocal Rank Fusion, reranking orchestration)
- [x] Chat tools updated (search_strategy param: auto/vector/hybrid)
- [ ] End-to-end testing (requires running SQL migration 007 in Supabase)

### Module 8: Additional Tools
- [x] Config settings (Tavily API key, per-tool enable flags, URL fetcher limits)
- [x] Web search tool (Tavily Search API via httpx, @traceable)
- [x] Calculator tool (simpleeval safe math evaluation, fallback for basic arithmetic)
- [x] URL fetcher tool (httpx + BeautifulSoup, content extraction + truncation)
- [x] Date/time tool (stdlib datetime + zoneinfo, timezone support)
- [x] Tool registry updated (dynamic get_enabled_tools based on config, extended dispatcher)
- [x] Chat service updated (dynamic tool-aware system prompt, tools available without documents)
- [ ] End-to-end testing (requires Tavily API key for web search)

### Module 9: Sub-Agents
- [ ] Not started
