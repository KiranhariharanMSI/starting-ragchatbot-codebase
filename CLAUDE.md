# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Starting the Application

#### Docker (Recommended for Production)
```bash
# Build and start container
docker-compose up -d

# Check container status
docker-compose ps

# View logs
docker logs -f course-rag-system

# Stop container
docker-compose down
```

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
Create `.env` file in root with:
```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

## Architecture Overview

This is a Retrieval-Augmented Generation (RAG) system that answers questions about course materials using semantic search and AI responses.

### Core Components

**FastAPI Backend** (`backend/app.py`):
- Main API server with CORS middleware
- Two endpoints: `/api/query` (chat) and `/api/courses` (analytics)
- Auto-loads documents from `docs/` folder on startup
- Serves frontend as static files

**RAG System** (`backend/rag_system.py`):
- Main orchestrator coordinating all components
- Tool-based architecture where Claude decides when to search
- Session management for conversation context
- Document processing and vector storage integration

**AI Integration** (`backend/ai_generator.py`):
- Anthropic Claude integration with tool calling
- Uses `claude-sonnet-4-20250514` model
- Implements conversation history and tool execution

**Vector Search** (`backend/vector_store.py` + `backend/search_tools.py`):
- ChromaDB for semantic document search
- Course-aware filtering (search within specific courses)
- Tool-based search that Claude can invoke dynamically

**Document Processing** (`backend/document_processor.py`):
- Chunks documents (800 chars, 100 overlap)
- Extracts course metadata from filenames and content
- Supports PDF, DOCX, TXT files

### Key Architecture Decisions

1. **Tool-Based RAG**: Claude decides when to search rather than always searching
2. **Session Management**: Tracks conversation history (configurable, default 2 messages)
3. **Course-Aware Search**: Can filter searches by course name or lesson number
4. **ChromaDB Persistence**: Vector database stored in `./backend/chroma_db/`

### Data Flow
1. User query → Frontend → FastAPI endpoint
2. RAG System creates/retrieves session
3. AI Generator calls Claude with query + tool definitions
4. Claude optionally uses search tool to find relevant content
5. Claude generates response using retrieved context
6. Response + sources returned to frontend

### Configuration
All settings in `backend/config.py`:
- Chunk size: 800 characters (100 overlap)
- Max search results: 5
- Max conversation history: 2 messages
- Embedding model: `all-MiniLM-L6-v2`

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
- use the docker route to run and test this