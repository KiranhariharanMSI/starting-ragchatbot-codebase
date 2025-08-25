# Course Materials RAG System

A Retrieval-Augmented Generation (RAG) system designed to answer questions about course materials using semantic search and AI-powered responses with **multi-LLM function calling support**.

## Overview

This application is a full-stack web application that enables users to query course materials and receive intelligent, context-aware responses. It uses ChromaDB for vector storage and supports multiple LLM providers with unified function calling:

- **OpenAI** (via AISuite with function calling)
- **Anthropic Claude** (native tool use support)
- **Google Gemini** (via AISuite with function calling)
- **xAI Grok** (via AISuite with function calling)

Provider selection is automatic in this order: OpenAI → Anthropic → Google → xAI, based on available API keys.

## Key Features

- **Multi-LLM Support**: Seamless switching between OpenAI, Anthropic, Google, and xAI
- **Unified Function Calling**: All providers support tool-based document search
- **Retrieval-Augmented Generation**: AI responses grounded in course content
- **Semantic Search**: ChromaDB vector store for intelligent document retrieval
- **Real-time Chat Interface**: Interactive web UI with conversation history
- **Provider-Agnostic Tools**: Consistent tool interface across all LLM providers


## Prerequisites

- Python 3.13 or higher
- uv (Python package manager)
- At least one LLM API key (set any of these):
  - OPENAI_API_KEY
  - ANTHROPIC_API_KEY
  - GOOGLE_API_KEY
  - XAI_API_KEY
- **For Windows**: Use Git Bash to run the application commands - [Download Git for Windows](https://git-scm.com/downloads/win)

## Installation

1. **Install uv** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install Python dependencies**
   ```bash
   uv sync
   ```

3. **Set up environment variables**
   
   Create a `.env` file in the root directory:
   ```bash
   # Set any available keys; the app will auto-select the first available provider
   OPENAI_API_KEY=your_openai_key
   ANTHROPIC_API_KEY=your_anthropic_key
   GOOGLE_API_KEY=your_google_gemini_key
   XAI_API_KEY=your_xai_key
   ```

   Optional model overrides (defaults are sensible):
   ```bash
   OPENAI_MODEL=gpt-4o
   ANTHROPIC_MODEL=claude-sonnet-4-20250514
   GEMINI_MODEL=gemini-1.5-pro-002
   GROK_MODEL=grok-2-latest
   ```

## Running the Application

### Quick Start

Use the provided shell script:
```bash
chmod +x run.sh
./run.sh
```

### Manual Start

```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```

The application will be available at:
- Web Interface: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`

## Troubleshooting

- **No provider selected / ValueError: No supported LLM API keys found**
  - Ensure at least one of `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, or `XAI_API_KEY` is set in `.env`.

- **ImportError: aisuite not found**
  - Run `uv sync` to install dependencies from `pyproject.toml`.
  - If needed, run `uv add aisuite`.

- **Model not found / invalid model**
  - Check optional overrides in `.env` (`OPENAI_MODEL`, `ANTHROPIC_MODEL`, `GEMINI_MODEL`, `GROK_MODEL`).
  - Remove overrides to fall back to defaults if unsure.

- **Tool-use not executing**
  - All providers now support function calling/tool use. If tools aren't working, check that documents are loaded correctly and the provider has a valid API key.

- **ChromaDB locked or stale index**
  - Stop the server, then delete the local `./chroma_db/` directory if safe, and restart to re-index documents.

## Architecture

### Multi-LLM Function Calling Implementation

The system implements a unified function calling interface that works across all supported LLM providers:

```python
# Tool definitions automatically adapt to provider format
tools = tool_manager.get_tool_definitions(provider)

# OpenAI format: {"type": "function", "function": {...}}
# Anthropic format: {"name": "...", "description": "...", "input_schema": {...}}
```

**Provider Detection:**
- **AISuite Path**: OpenAI, Google Gemini, xAI Grok (uses OpenAI-compatible function calling)
- **Anthropic Path**: Claude models (uses native tool use API)

**Tool Execution Flow:**
1. User query received
2. Provider-specific tool definitions generated
3. LLM called with tools and query
4. Tool calls executed via unified `ToolManager`
5. Results fed back to LLM for final response

### Key Components

- **`AIGenerator`**: Multi-provider LLM client with function calling support
- **`ToolManager`**: Unified tool registration and execution
- **`CourseSearchTool`**: Semantic search over course documents
- **`RAGSystem`**: Orchestrates document retrieval and AI generation
- **`VectorStore`**: ChromaDB-based semantic search and storage
