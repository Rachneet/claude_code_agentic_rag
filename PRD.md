# Agentic RAG Masterclass - PRD

## What We're Building

A RAG application with two interfaces:
1. **Chat** (default view) - Threaded conversations with retrieval-augmented responses
2. **Ingestion** - Upload files manually, track processing, manage documents

This is **not** an automated pipeline with connectors. Files are uploaded manually via drag-and-drop. Configuration is via environment variables, no admin UI.

## Target Users

Technically-minded people who want to build production RAG systems using AI coding tools (Claude Code, Cursor, etc.). They don't need to know Python or React - that's the AI's job.

**They need to understand:**
- RAG concepts deeply (chunking, embeddings, retrieval, reranking)
- Codebase structure (what sits where, how pieces connect)
- How to direct AI to build what they need
- How to direct AI to fix things when they break

## Scope

### In Scope
- ✅ Document ingestion and processing
- ✅ Vector search with pgvector
- ✅ Hybrid search (keyword + vector)
- ✅ Reranking
- ✅ Metadata extraction
- ✅ Record management (deduplication)
- ✅ Multi-format support (PDF, DOCX, HTML, Markdown)
- ✅ Text-to-SQL tool
- ✅ Web search fallback
- ✅ Sub-agents with isolated context
- ✅ Chat with threads and memory
- ✅ Streaming responses
- ✅ Auth with RLS

### Out of Scope
- ❌ Knowledge graphs / GraphRAG
- ❌ Code execution / sandboxing
- ❌ Image/audio/video processing
- ❌ Fine-tuning
- ❌ Multi-tenant admin features
- ❌ Billing/payments
- ❌ Data connectors (Google Drive, SFTP, APIs, webhooks)
- ❌ Scheduled/automated ingestion
- ❌ Admin UI (config via env vars)

## Stack

| Layer | Choice |
|-------|--------|
| Frontend | React + TypeScript + Vite + Tailwind + shadcn/ui |
| Backend | Python + FastAPI |
| Database | Supabase (Postgres + pgvector + Auth + Storage + Realtime) |
| LLM (Module 1) | HuggingFace Inference (serverless inference API) |
| LLM (Module 2) | Google Generative AI (Gemini models) |
| LLM (Module 3) | OpenRouter (multi-provider access) |
| Observability | LangSmith |

## Constraints

- No LLM frameworks - raw SDK calls using standard APIs, Pydantic for structured outputs
- Row-Level Security on all tables - users only see their own data
- Streaming chat via SSE
- Ingestion status via Supabase Realtime

---

## Module 1: The App Shell + Observability

**Build:** Auth, chat UI, HuggingFace Inference integration (direct API calls), LangSmith tracing

**Learn:** What RAG is, using serverless inference APIs, building chat interfaces with streaming responses

**Note:** HuggingFace Inference provides serverless access to various models (Llama, Mistral, Zephyr, etc.). Unlike OpenAI's managed Responses API, you'll build your own thread management and retrieval logic from the start, giving you full control and portability.

---

## Architectural Decision: Module 1 → Module 2 and 3 Transition

At the end of Module 1, you have a working chat app using **HuggingFace Inference API**—a serverless solution where you manage threads, memory, and retrieval yourself. In Module 2, you switch to **Google Generative AI (Gemini)** to explore different model capabilities and API patterns. In Module 3, you integrate **OpenRouter** for multi-provider access.

**The decision you need to make:** How do you structure your codebase to support multiple LLM providers? Here are two common approaches, but you're not limited to these—come up with your own if it makes sense for your use case.

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| **A: Replace** | Remove previous provider code entirely, rebuild with new provider | Clean codebase, single pattern, easier to maintain | Lose the ability to use previous providers |
| **B: Provider Abstraction** | Build a provider interface, support multiple backends via configuration | Flexibility to switch providers, compare performance/cost | More complex codebase, abstraction overhead |

There is no right answer—this is a real architectural choice you'll face in building production systems.

**Recommended approach for learning: Option B**—build a provider abstraction layer that allows you to configure which LLM provider to use via environment variables. This teaches you how to build flexible, provider-agnostic systems.

**This is a lesson in steering Claude Code**: you need to clearly communicate your decision and guide the AI to implement it correctly. Be explicit about the abstraction pattern, configuration mechanism, and how providers should be swapped.

---

## Module 2: BYO Retrieval + Memory

**Prerequisites:** Complete the architectural decision above.

**Build:** Ingestion UI, file storage, chunking → embedding → pgvector, retrieval tool, Google Generative AI (Gemini) integration, chat history storage (stateless API - you manage memory), realtime ingestion status

**Learn:** Chunking, embeddings, vector search, tool calling with Gemini, relevance thresholds, managing conversation history, **building provider abstractions**

---

## Module 3: Multi-Provider Support

**Build:** OpenRouter integration, provider configuration system, unified interface across HF/Gemini/OpenRouter

**Learn:** Building provider-agnostic systems, cost/performance tradeoffs, fallback strategies

---

## Module 4: Record Manager

**Build:** Content hashing, detect changes, only process what's new/modified

**Learn:** Why naive ingestion duplicates, incremental updates

---

## Module 5: Metadata Extraction

**Build:** LLM extracts structured metadata, filter retrieval by metadata

**Learn:** Structured extraction, schema design, metadata-enhanced retrieval

---

## Module 6: Multi-Format Support

**Build:** PDF/DOCX/HTML/Markdown via docling, cascade deletes

**Learn:** Document parsing challenges, format considerations

---

## Module 7: Hybrid Search & Reranking

**Build:** Keyword + vector search, RRF combination, reranking

**Learn:** Why vector alone isn't enough, hybrid strategies, reranking

---

## Module 8: Additional Tools

**Build:** Text-to-SQL tool (query structured data), web search fallback (when docs don't have the answer)

**Learn:** Multi-tool agents, routing between structured/unstructured data, graceful fallbacks, attribution for trust

---

## Module 9: Sub-Agents

**Build:** Detect full-document scenarios, spawn isolated sub-agent with its own tools, nested tool call display in UI, show reasoning from both main agent and sub-agents

**Learn:** Context management, agent delegation, hierarchical agent display, when to isolate

---

## Success Criteria

By the end, students should have:
- ✅ A working RAG application they built with AI assistance
- ✅ Deep understanding of RAG concepts (chunking, embedding, retrieval, reranking)
- ✅ Understanding of codebase structure - what lives where, how pieces connect
- ✅ Ability to direct AI coding tools to build new features
- ✅ Ability to direct AI coding tools to debug and fix issues
- ✅ Experience with agentic patterns (multi-tool, sub-agents)
- ✅ Experience with multiple LLM providers and abstraction patterns
- ✅ Observability set up from day one