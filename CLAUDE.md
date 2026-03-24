# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
# Start the server (creates docs dir, validates structure, launches FastAPI)
./run.sh

# Or directly
cd backend && uv run uvicorn app:app --reload --port 8000
```

- Web UI: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`

## Setup

```bash
# Install dependencies (requires uv and Python 3.13+)
uv sync
```

Always use `uv` to manage packages and run Python — never use `pip` directly.

Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY`.

## Architecture

This is a RAG (Retrieval-Augmented Generation) chatbot that answers questions about course transcripts stored in `docs/`.

**Request flow:**
1. On startup, `rag_system.py` loads course transcripts from `docs/`, chunks them (800 chars, 100 overlap), and stores embeddings in ChromaDB (`backend/chroma_db/`)
2. User query hits `POST /api/query` in `app.py`
3. `rag_system.py` orchestrates: passes query + conversation history to `ai_generator.py`
4. Claude autonomously decides to call the `search_course_content` tool (defined in `search_tools.py`)
5. Tool execution hits `vector_store.py` for semantic search via `all-MiniLM-L6-v2` embeddings
6. Results returned to Claude, which generates the final answer
7. Session history stored in `session_manager.py`

**Backend modules** (`backend/`):
- `app.py` — FastAPI entry point, two endpoints: `POST /api/query`, `GET /api/courses`
- `rag_system.py` — Central orchestrator; wires all components together
- `ai_generator.py` — Anthropic SDK calls; handles tool use loop
- `vector_store.py` — ChromaDB read/write; embedding generation
- `document_processor.py` — Parses `.txt` course files, chunks with overlap
- `search_tools.py` — Tool schema definitions passed to Claude
- `session_manager.py` — In-memory conversation history (configurable `MAX_HISTORY`)
- `config.py` — All config via env vars with defaults
- `models.py` — Pydantic models: `Course`, `Lesson`, `CourseChunk`

**Frontend** (`frontend/`): Vanilla JS/HTML/CSS served as static files by FastAPI. No build step.

**Key config** (env vars with defaults):
- `ANTHROPIC_MODEL` — default `claude-sonnet-4-20250514`
- `CHUNK_SIZE` / `CHUNK_OVERLAP` — default 800 / 100
- `MAX_RESULTS` — default 5 (search results returned to Claude)
- `MAX_HISTORY` — default 2 (conversation turns kept in session)
- `CHROMA_PATH` — default `./chroma_db`
