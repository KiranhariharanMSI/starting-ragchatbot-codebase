# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Starting the Application
#### Local Development
```bash
# Quick start
chmod +x run.sh
./run.sh

# Manual start
cd backend
uv run uvicorn app:app --reload --port 8000
```

### Dependency Management
```bash
# Install all dependencies
uv sync

# Add new dependency
uv add <package-name>
```

### Environment Setup
Create `.env` file in root with any available keys (router picks first available):
```
# Preferred order: OpenAI → Anthropic → Google → xAI
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
GOOGLE_API_KEY=...
XAI_API_KEY=...

# Optional model overrides
OPENAI_MODEL=gpt-4o
ANTHROPIC_MODEL=claude-sonnet-4-20250514
GEMINI_MODEL=gemini-1.5-pro-002
GROK_MODEL=grok-2-latest
```

## Architecture Overview

This is a **multi-LLM Retrieval-Augmented Generation (RAG) system** with unified function calling support across all providers. It answers questions about course materials using semantic search and AI responses with consistent tool-based document retrieval.

### Core Components

**FastAPI Backend** (`backend/app.py`):
- Main API server with CORS middleware
- Two endpoints: `/api/query` (chat) and `/api/courses` (analytics)
- Auto-loads documents from `docs/` folder on startup
- Serves frontend as static files

**RAG System** (`backend/rag_system.py`):
- Main orchestrator coordinating all components
- **Multi-provider tool integration** with automatic format conversion
- Session management for conversation context
- Document processing and vector storage integration

**AI Integration** (`backend/ai_generator.py`):
- **Unified multi-LLM support with function calling**:
  - OpenAI via AISuite (with OpenAI function calling)
  - Anthropic via Anthropic SDK (with native tool use)
  - Google Gemini via AISuite (with OpenAI-compatible function calling)
  - xAI Grok via AISuite (with OpenAI-compatible function calling)
- **All providers now support tool execution** for RAG functionality

**Vector Search** (`backend/vector_store.py` + `backend/search_tools.py`):
- ChromaDB for semantic document search
- Course-aware filtering (search within specific courses)
- **Unified tool interface** with provider-specific format conversion
- Tool-based search that all LLMs can invoke dynamically

**Document Processing** (`backend/document_processor.py`):
- Chunks documents (800 chars, 100 overlap)
- Extracts course metadata from filenames and content
- Supports PDF, DOCX, TXT files

### Key Architecture Decisions

1. **Provider Router**: OpenAI → Anthropic → Google → xAI based on API key presence
2. **Tool-Based RAG**: Tool calls supported on Anthropic path today
3. **Session Management**: Tracks conversation history (configurable, default 2 messages)
4. **Course-Aware Search**: Can filter searches by course name or lesson number
5. **ChromaDB Persistence**: Vector database stored in `./chroma_db` (see `backend/config.py`)

### Data Flow
1. User query → Frontend → FastAPI endpoint
2. RAG System creates/retrieves session
3. AI Generator selects provider based on keys and calls model
4. If Anthropic and tool-use requested, executes tools and re-calls model
5. Model generates response (with retrieved context when tools used)
6. Response + sources returned to frontend

### Configuration
All settings in `backend/config.py`:
- Chunk size: 800 characters (100 overlap)
- Max search results: 5
- Max conversation history: 2 messages
- Embedding model: `all-MiniLM-L6-v2`
- LLM models and API keys for OpenAI, Anthropic, Google Gemini, xAI Grok

### File Structure
- `backend/`: All Python backend code
- `frontend/`: Static HTML/CSS/JS files
- `docs/`: Course documents (auto-loaded on startup)
- `query-flow-diagram.md`: Detailed sequence diagrams of system flow

## Development Notes

- Uses `uv` for Python dependency management
- Backend runs on port 8000 with auto-reload
- Frontend served as static files from FastAPI
- ChromaDB creates persistent vector store on first run
- Documents in `docs/` folder are automatically indexed on server startup