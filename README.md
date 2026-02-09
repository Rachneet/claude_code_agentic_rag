<p align="center">
  <h1 align="center">Agentic RAG Masterclass</h1>
  <p align="center">
    Build a production-grade Agentic RAG system from scratch — powered by Claude Code.
  </p>
  <p align="center">
    <a href="#modules">Modules</a> &middot;
    <a href="#architecture">Architecture</a> &middot;
    <a href="#getting-started">Getting Started</a> &middot;
    <a href="#configuration">Configuration</a> &middot;
    <a href="#project-structure">Project Structure</a>
  </p>
</p>

---

## What This Is

A hands-on masterclass where you collaborate with **Claude Code** to build a fully featured Agentic RAG (Retrieval-Augmented Generation) application across 9 progressive modules. You guide the AI — it writes the code.

**You don't need to know how to code.** You need to be technically minded and willing to learn about APIs, databases, and system architecture.

By the end you'll have a working system with:

- Chat interface with streaming responses, threaded conversations, and markdown rendering
- Document ingestion pipeline supporting PDF, DOCX, HTML, and plain text
- Hybrid search (vector + full-text) with cross-encoder reranking
- Tool calling (web search, calculator, URL reader, date/time)
- Autonomous sub-agents with multi-turn reasoning (Research, Document Q&A, Task Planner)
- Full observability via LangSmith tracing
- Multi-provider LLM support (HuggingFace, Google Gemini, OpenRouter)

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19, TypeScript, Vite 7, Tailwind CSS 4, shadcn/ui, Radix UI |
| **Backend** | Python, FastAPI, Pydantic, SSE streaming |
| **Database** | Supabase (PostgreSQL + pgvector + Auth + Storage + Realtime) |
| **LLM Providers** | HuggingFace Inference API, Google Gemini, OpenRouter |
| **Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions) |
| **Reranking** | `BAAI/bge-reranker-v2-m3` cross-encoder |
| **Web Search** | Tavily Search API |
| **Observability** | LangSmith |

> **Design constraint:** No LangChain, no LangGraph — raw SDK calls only. This is intentional so you understand every layer.

---

## Modules

Each module builds on the previous one. Follow them in order.

### Module 1: App Shell + Observability
Foundation layer. Supabase schema, FastAPI backend, React frontend with auth, threaded chat with SSE streaming, LangSmith tracing.

### Module 2: BYO Retrieval + Memory
Document ingestion pipeline (upload, chunk, embed, store), pgvector similarity search, RAG integration with tool calling (Gemini) and context injection (HuggingFace), Supabase Realtime status updates.

### Module 3: Multi-Provider Support
OpenRouter as a third LLM provider. Provider abstraction layer (ABC + factory pattern) so you can swap backends via a single env var. Capability-based tool calling (`supports_tools` property).

### Module 4: Record Manager
Content-hash deduplication for document chunks. On re-upload, only new/changed chunks get embedded — saves time and API costs. SHA-256 content addressing with reconciliation logic.

### Module 5: Metadata Extraction
LLM-powered metadata extraction (title, document type, topics, entities, language, summary). Metadata-filtered retrieval. Frontend badges showing document properties.

### Module 6: Multi-Format Support
PDF extraction (pypdf), DOCX extraction (python-docx), HTML extraction (BeautifulSoup4). MIME-type dispatcher with UTF-8 fallback. Granular ingestion status (extracting → chunking → embedding).

### Module 7: Hybrid Search + Reranking
PostgreSQL full-text search alongside pgvector. Reciprocal Rank Fusion (RRF) to merge ranked lists. Cross-encoder reranking via HuggingFace Inference API. Configurable search strategy (`auto`, `vector`, `hybrid`).

### Module 8: Additional Tools
Web search (Tavily), calculator (safe math eval), URL fetcher (content extraction), date/time tool. Dynamic tool registry with per-tool feature flags.

### Module 9: Sub-Agents
Three autonomous agents with multi-turn ReAct loops:
- **Research Agent** — searches documents + web, synthesizes with citations
- **Document Q&A Agent** — multi-hop reasoning over uploaded documents
- **Task Planner Agent** — decomposes complex requests into sequential steps

Recursion guard prevents agents from invoking other agents.

---

## Architecture

### High-Level Overview

```
                                    +------------------+
                                    |    Frontend      |
                                    |  React + Vite    |
                                    |  Tailwind + UI   |
                                    +--------+---------+
                                             |
                                        SSE / REST
                                             |
                                    +--------+---------+
                                    |    Backend       |
                                    |    FastAPI       |
                                    +--------+---------+
                                             |
                    +------------------------+------------------------+
                    |                        |                        |
           +--------+-------+     +---------+--------+     +---------+--------+
           |  LLM Providers |     |    Ingestion     |     |   Supabase       |
           |                |     |    Pipeline       |     |                  |
           | - HuggingFace  |     | - Extract (PDF,  |     | - PostgreSQL     |
           | - Gemini       |     |   DOCX, HTML)    |     | - pgvector       |
           | - OpenRouter   |     | - Chunk          |     | - Auth (JWT)     |
           +--------+-------+     | - Metadata (LLM) |     | - Storage        |
                    |             | - Deduplicate    |     | - Realtime       |
                    |             | - Embed          |     +------------------+
                    |             | - Store          |
                    |             +------------------+
                    |
        +-----------+-----------+
        |                       |
  +-----+------+        +------+------+
  |   Tools    |        |  Sub-Agents |
  |            |        |             |
  | - Search   |        | - Research  |
  | - Web      |        | - DocQA     |
  | - Calc     |        | - Planner   |
  | - URL      |        |             |
  | - DateTime |        | (ReAct Loop)|
  +------------+        +-------------+
```

### Data Flows

**Chat (with tool calling):**
```
User message → Save to DB → Build conversation history
  → LLM with tools → Tool call detected → Execute tool
  → Tool result back to LLM → Stream response via SSE → Save to DB
```

**Chat (with sub-agent):**
```
User message → LLM detects complex query → Delegates to agent
  → Agent ReAct loop: (LLM → Tool call → Execute → Observe) × N
  → Agent final answer → Stream to user via SSE
```

**Document ingestion:**
```
Upload → Supabase Storage → Extract text (PDF/DOCX/HTML/TXT)
  → Sentence-boundary chunking → LLM metadata extraction
  → Content-hash deduplication → Embed new chunks (HF API)
  → Store vectors in pgvector → Realtime status update to UI
```

**Hybrid search:**
```
Query → [Vector search (pgvector cosine)] + [Full-text search (tsvector)]
  → Reciprocal Rank Fusion → Cross-encoder reranking → Top-K results
```

### LLM Provider Abstraction

All three providers implement the same interface:

```python
class LLMProvider(ABC):
    supports_tools: bool

    def chat_completion(messages, ...) -> str
    async def chat_completion_stream(messages, ...) -> AsyncGenerator[str]
    def chat_completion_with_tools(messages, tools, ...) -> dict
    async def chat_completion_stream_with_tools(messages, tools, ...) -> AsyncGenerator[str]
    def format_tool_messages(response, tool_results) -> list[dict]
```

Switch providers with a single env var:

```bash
LLM_PROVIDER=gemini       # Google Gemini (recommended, full tool calling)
LLM_PROVIDER=openrouter   # OpenRouter (any model, full tool calling)
LLM_PROVIDER=huggingface  # HuggingFace Inference (tool calling via cerebras)
```

---

## Getting Started

### Prerequisites

- **Python 3.9+**
- **Node.js 18+**
- **Supabase project** — [Create one free](https://supabase.com/dashboard)
- **HuggingFace account** — [Get a token](https://huggingface.co/settings/tokens)
- **Claude Code** — [Install it](https://docs.anthropic.com/en/docs/claude-code)
- At least one LLM provider API key (HuggingFace, Google, or OpenRouter)

### 1. Clone the repository

```bash
git clone https://github.com/Rachneet/claude-code-agentic-rag-masterclass.git
cd claude-code-agentic-rag-masterclass
```

### 2. Set up Supabase

1. Create a new project at [supabase.com/dashboard](https://supabase.com/dashboard)
2. Run the SQL migrations in order in the **SQL Editor**:
   ```
   backend/supabase/migrations/001_initial_schema.sql
   backend/supabase/migrations/002_documents_and_vectors.sql
   backend/supabase/migrations/002b_storage_bucket.sql
   backend/supabase/migrations/003_record_manager.sql
   backend/supabase/migrations/004_metadata_extraction.sql
   backend/supabase/migrations/005_multi_format_storage.sql
   backend/supabase/migrations/006_granular_status.sql
   backend/supabase/migrations/007_hybrid_search.sql
   ```
3. Copy your project URL, anon key, and service role key from **Settings > API**

### 3. Set up the backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env` from the example:

```bash
cp .env.example .env
```

Fill in your keys (see [Configuration](#configuration) below).

### 4. Set up the frontend

```bash
cd frontend
npm install
```

Create `frontend/.env` from the example:

```bash
cp .env.example .env
```

Fill in your Supabase URL and anon key.

### 5. Start both services

From the project root:

```bash
./dev.sh
```

Or start them separately:

```bash
# Terminal 1 — Backend
cd backend && source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm run dev
```

### 6. Open the app

Navigate to **http://localhost:5173**, create an account, and start chatting.

### 7. Follow with Claude Code

Open the project in your IDE and run `claude` in the terminal. Use the `/onboard` command to get oriented, then follow the modules in the [PRD](./PRD.md).

---

## Configuration

### Backend Environment Variables

Create `backend/.env` with these values:

#### Required

| Variable | Description |
|---|---|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anonymous/public key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key (server-side only) |
| `HF_TOKEN` | HuggingFace API token (used for embeddings + reranking) |
| `LLM_PROVIDER` | `huggingface`, `gemini`, or `openrouter` |

#### LLM Provider Keys (at least one required)

| Variable | Description | Default |
|---|---|---|
| `GOOGLE_API_KEY` | Google AI API key (for Gemini) | — |
| `GEMINI_MODEL` | Gemini model to use | `gemini-2.5-flash` |
| `OPENROUTER_API_KEY` | OpenRouter API key | — |
| `OPENROUTER_MODEL` | OpenRouter model ID | `google/gemini-2.5-flash` |
| `OPENROUTER_BASE_URL` | OpenRouter API base URL | `https://openrouter.ai/api/v1` |
| `HF_PROVIDER` | HuggingFace routing provider | `auto` |
| `HF_TOOL_PROVIDER` | HF provider for tool calls | `cerebras` |

#### Observability

| Variable | Description | Default |
|---|---|---|
| `LANGSMITH_API_KEY` | LangSmith API key | — |
| `LANGSMITH_PROJECT` | LangSmith project name | `rag-masterclass` |
| `LANGSMITH_TRACING` | Enable LangSmith tracing | `true` |

#### Retrieval & Reranking

| Variable | Description | Default |
|---|---|---|
| `HF_EMBEDDING_MODEL` | Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| `RERANKER_ENABLED` | Enable cross-encoder reranking | `true` |
| `RERANKER_MODEL` | Reranker model | `BAAI/bge-reranker-v2-m3` |
| `HYBRID_SEARCH_ENABLED` | Enable hybrid (vector + FTS) search | `true` |

#### Tools

| Variable | Description | Default |
|---|---|---|
| `TAVILY_API_KEY` | Tavily API key (for web search) | — |
| `TOOLS_WEB_SEARCH_ENABLED` | Enable web search tool | `true` |
| `TOOLS_CALCULATOR_ENABLED` | Enable calculator tool | `true` |
| `TOOLS_URL_FETCHER_ENABLED` | Enable URL fetcher tool | `true` |
| `TOOLS_DATETIME_ENABLED` | Enable date/time tool | `true` |
| `URL_FETCHER_MAX_CHARS` | Max characters from fetched pages | `8000` |
| `URL_FETCHER_TIMEOUT` | URL fetch timeout (seconds) | `15` |

#### Sub-Agents

| Variable | Description | Default |
|---|---|---|
| `AGENTS_RESEARCH_ENABLED` | Enable Research Agent | `true` |
| `AGENTS_DOCQA_ENABLED` | Enable Document Q&A Agent | `true` |
| `AGENTS_PLANNER_ENABLED` | Enable Task Planner Agent | `true` |
| `AGENT_MAX_ITERATIONS` | Max ReAct loop iterations | `6` |
| `AGENT_MAX_TOKENS` | Max tokens per agent response | `4096` |

### Frontend Environment Variables

Create `frontend/.env`:

| Variable | Description |
|---|---|
| `VITE_SUPABASE_URL` | Your Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Supabase anonymous/public key |
| `VITE_API_URL` | Backend URL (default: `http://localhost:8000`) |

---

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── agents/                # Sub-agents (Module 9)
│   │   │   ├── base.py            #   BaseAgent with ReAct loop
│   │   │   ├── research.py        #   Research Agent (docs + web)
│   │   │   ├── docqa.py           #   Document Q&A Agent
│   │   │   └── planner.py         #   Task Planner Agent
│   │   ├── auth/
│   │   │   └── dependencies.py    #   JWT authentication
│   │   ├── chat/
│   │   │   ├── router.py          #   Chat REST endpoints
│   │   │   ├── service.py         #   Chat orchestration + RAG
│   │   │   ├── tools.py           #   Tool definitions + dispatcher
│   │   │   ├── calculator.py      #   Safe math evaluation
│   │   │   ├── datetime_tool.py   #   Timezone-aware date/time
│   │   │   ├── web_search.py      #   Tavily web search
│   │   │   └── url_fetcher.py     #   URL content extraction
│   │   ├── db/
│   │   │   └── supabase.py        #   Supabase client
│   │   ├── ingestion/
│   │   │   ├── router.py          #   Document upload endpoints
│   │   │   ├── service.py         #   Ingestion pipeline
│   │   │   ├── chunking.py        #   Text chunking
│   │   │   ├── embeddings.py      #   HF embedding service
│   │   │   ├── extractors.py      #   PDF/DOCX/HTML extraction
│   │   │   ├── metadata.py        #   LLM metadata extraction
│   │   │   ├── record_manager.py  #   Hash-based deduplication
│   │   │   ├── retrieval.py       #   Hybrid search + reranking
│   │   │   └── reranker.py        #   Cross-encoder reranking
│   │   ├── llm/
│   │   │   ├── base.py            #   LLMProvider abstract base
│   │   │   ├── factory.py         #   Provider factory
│   │   │   ├── huggingface.py     #   HuggingFace Inference
│   │   │   ├── gemini.py          #   Google Gemini
│   │   │   └── openrouter.py      #   OpenRouter
│   │   ├── models/
│   │   │   └── schemas.py         #   Pydantic models
│   │   ├── config.py              #   Settings (env vars)
│   │   └── main.py                #   FastAPI app
│   ├── supabase/
│   │   └── migrations/            # 8 SQL migration files
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── auth/              # Login, Signup, AuthPage
│   │   │   ├── chat/              # ChatView, MessageList, MessageInput, ThreadSidebar
│   │   │   ├── documents/         # DocumentsView, DocumentList, FileUpload
│   │   │   ├── layout/            # AppLayout, Header
│   │   │   └── ui/                # shadcn/ui components
│   │   ├── contexts/
│   │   │   └── AuthContext.tsx     # Supabase auth provider
│   │   ├── lib/
│   │   │   ├── api.ts             # API client + SSE streaming
│   │   │   └── supabase.ts        # Supabase client
│   │   ├── types/
│   │   │   └── index.ts           # TypeScript type definitions
│   │   └── App.tsx                # Main routing
│   ├── package.json
│   └── .env.example
│
├── .agent/plans/                  # Detailed implementation plans per module
├── CLAUDE.md                      # Context for Claude Code
├── PRD.md                         # Product requirements (all modules)
├── PROGRESS.md                    # Module completion tracker
├── dev.sh                         # Start both services
└── README.md
```

---

## API Endpoints

### Chat

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/threads` | Create a new thread |
| `GET` | `/api/threads` | List user's threads |
| `PATCH` | `/api/threads/{id}` | Rename a thread |
| `DELETE` | `/api/threads/{id}` | Delete a thread |
| `GET` | `/api/threads/{id}/messages` | Get thread messages |
| `POST` | `/api/chat` | Stream chat response (SSE) |

### Documents

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/documents/upload` | Upload a document |
| `GET` | `/api/documents` | List user's documents |
| `DELETE` | `/api/documents/{id}` | Delete a document |

### System

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |

All endpoints (except `/health`) require a Bearer token from Supabase Auth.

---

## Database Schema

### Tables

| Table | Purpose |
|---|---|
| `threads` | Chat conversation threads |
| `messages` | Individual messages (user + assistant) |
| `documents` | Uploaded document metadata + ingestion status |
| `document_chunks` | Chunked text with embeddings (pgvector) + FTS index |

### Key Features

- **Row-Level Security** on all tables — users only see their own data
- **pgvector** HNSW index for fast cosine similarity search
- **tsvector** GIN index for full-text search
- **Realtime** enabled on `documents` table for live status updates
- **Content-hash** unique index for chunk deduplication
- **GIN indexes** on JSONB metadata columns for filtered retrieval

---

## Tools & Agents

### Available Tools (8 total)

| Tool | Description | Requires |
|---|---|---|
| `search_documents` | Vector/hybrid search over uploaded docs | Documents uploaded |
| `web_search` | Search the web via Tavily | `TAVILY_API_KEY` |
| `calculate` | Safe mathematical expression evaluation | — |
| `fetch_url` | Extract content from any URL | — |
| `get_datetime` | Current date/time in any timezone | — |
| `research_agent` | Multi-source research with citations | — |
| `docqa_agent` | Multi-hop document analysis | Documents uploaded |
| `planner_agent` | Decompose and execute multi-step tasks | — |

### How Agents Work

Each agent runs an independent **ReAct loop** (Reason → Act → Observe):

```
1. Receive task from outer LLM
2. Loop (up to max_iterations):
   a. Send messages + tools to LLM
   b. If LLM returns content → done, return answer
   c. If LLM returns tool calls → execute each tool
   d. Append tool results to conversation → go to (a)
3. If iteration cap reached → ask LLM for final answer without tools
```

Agents are called as tools by the outer LLM, which decides when to delegate:

- **Simple questions** → direct tool call (fast)
- **Complex research** → `research_agent` (thorough)
- **Cross-document analysis** → `docqa_agent` (multi-hop)
- **Multi-step tasks** → `planner_agent` (sequential)

---

## Observability

All LLM calls, tool executions, and agent runs are traced via **LangSmith**:

- Chat completions → `chat_stream` chain
- Thread title generation → `generate_thread_title` chain
- Agent runs → `agent_run` chain with nested tool calls
- Document metadata extraction → `extract_metadata` chain

Set `LANGSMITH_TRACING=true` and provide your `LANGSMITH_API_KEY` to enable.

---

## Development

### Start both services

```bash
./dev.sh
```

This kills any existing processes on ports 8000/5173, starts the backend with hot reload, and starts the Vite dev server.

### Backend only

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### Frontend only

```bash
cd frontend
npm run dev
```

### Build frontend for production

```bash
cd frontend
npm run build
```

Output goes to `frontend/dist/`.

### Working with Claude Code

```bash
claude                    # Start Claude Code
/onboard                  # Get oriented with the codebase
/status                   # Check module progress
```

Plans for each module are in `.agent/plans/`. Progress is tracked in `PROGRESS.md`.

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **No LangChain / LangGraph** | Raw SDK calls so you understand every layer |
| **Service role key + manual filtering** | Avoids RLS performance overhead on server-side queries |
| **SSE over WebSocket** | Browser-native streaming, simpler than WebSocket for one-way data |
| **Sentence-boundary chunking** | Preserves semantic units better than fixed character splits |
| **Content-hash deduplication** | Only re-embed changed chunks on document re-upload |
| **Reciprocal Rank Fusion** | Combines vector + keyword rankings without score normalization |
| **Provider abstraction** | Swap LLM backends via env var, no code changes needed |
| **Recursion guard** | Agents cannot invoke other agents — prevents infinite loops |
| **Temperature 0.3 for agents** | More deterministic tool-calling behavior than conversational chat |
| **Graceful fallbacks** | Reranking and metadata extraction skip silently on error |

---

## Docs

| File | Description |
|---|---|
| [PRD.md](./PRD.md) | Full product requirements — what to build in each module |
| [CLAUDE.md](./CLAUDE.md) | Context and rules for Claude Code |
| [PROGRESS.md](./PROGRESS.md) | Module completion tracker |
| [.agent/plans/](./.agent/plans/) | Detailed implementation plans for each module |

---

## License

This project is for educational purposes as part of the Agentic RAG Masterclass.
