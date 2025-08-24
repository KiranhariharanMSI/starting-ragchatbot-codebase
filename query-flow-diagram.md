# RAG System Query Processing Flow

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend<br/>(script.js)
    participant API as FastAPI<br/>(app.py)
    participant RAG as RAG System<br/>(rag_system.py)
    participant SM as Session Manager
    participant AI as AI Generator<br/>(ai_generator.py)
    participant Claude as Anthropic Claude
    participant TM as Tool Manager<br/>(search_tools.py)
    participant VS as Vector Store<br/>(vector_store.py)
    participant DB as ChromaDB

    %% User Input Phase
    U->>FE: Types query & hits Enter
    FE->>FE: Disable input, show loading
    FE->>FE: Add user message to chat

    %% API Call Phase
    FE->>+API: POST /api/query<br/>{query, session_id}
    API->>API: Validate request
    
    %% Session Management
    alt No session_id provided
        API->>SM: create_session()
        SM-->>API: new_session_id
    end

    %% RAG Processing
    API->>+RAG: query(query, session_id)
    RAG->>SM: get_conversation_history(session_id)
    SM-->>RAG: previous_messages[]
    
    RAG->>TM: get_tool_definitions()
    TM-->>RAG: search_tool_schema

    %% AI Generation Phase
    RAG->>+AI: generate_response(query, history, tools, tool_manager)
    AI->>AI: Build system prompt + context
    
    %% Claude API Call
    AI->>+Claude: messages.create()<br/>{prompt, tools, context}
    Claude->>Claude: Analyze query
    
    %% Tool Decision & Execution
    alt Claude decides to search
        Claude-->>AI: tool_use request<br/>search_courses(query="...")
        AI->>+TM: execute_tool("search_courses", params)
        TM->>+VS: search(query, course_name, lesson_number)
        VS->>+DB: query(embeddings, filters)
        DB-->>-VS: matching_chunks[]
        VS->>VS: Format results + metadata
        VS-->>-TM: SearchResults{documents, metadata, distances}
        TM->>TM: Track sources for frontend
        TM-->>-AI: "**Result 1** Course: Title...\n**Result 2**..."
        
        %% Final Response Generation
        AI->>+Claude: Final call with tool results
        Claude->>Claude: Synthesize answer using retrieved content
        Claude-->>-AI: Generated response text
    else Claude answers directly
        Claude-->>-AI: Direct response (no tools needed)
    end
    
    %% Response Assembly
    AI-->>-RAG: response_text
    RAG->>TM: get_last_sources()
    TM-->>RAG: sources[]
    RAG->>TM: reset_sources()
    RAG->>SM: add_exchange(session_id, query, response)
    RAG-->>-API: (response, sources)

    %% API Response
    API->>API: Build QueryResponse object
    API-->>-FE: JSON{answer, sources, session_id}

    %% Frontend Display
    FE->>FE: Remove loading animation
    FE->>FE: Parse markdown in response
    FE->>FE: Add assistant message + sources
    FE->>FE: Re-enable input, focus
    FE->>U: Display formatted response
```

## Architecture Components

```mermaid
graph TB
    %% Frontend Layer
    subgraph Frontend ["🎨 Frontend Layer"]
        HTML[index.html<br/>Chat Interface]
        JS[script.js<br/>Event Handlers]
        CSS[style.css<br/>Styling]
    end

    %% API Layer
    subgraph API ["🔌 API Layer"]
        FastAPI[app.py<br/>FastAPI Server]
        Routes["/api/query<br/>/api/courses"]
        Models[models.py<br/>Pydantic Schemas]
    end

    %% RAG Core
    subgraph RAG ["🧠 RAG Core System"]
        RAGSys[rag_system.py<br/>Main Orchestrator]
        AIGen[ai_generator.py<br/>Claude Integration]
        SessionMgr[session_manager.py<br/>Conversation History]
    end

    %% Search & Tools
    subgraph Tools ["🔍 Search & Tools"]
        ToolMgr[search_tools.py<br/>Tool Manager]
        SearchTool[CourseSearchTool<br/>Vector Search]
    end

    %% Data Layer
    subgraph Data ["📊 Data Layer"]
        VectorStore[vector_store.py<br/>ChromaDB Interface]
        DocProcessor[document_processor.py<br/>Text Chunking]
        ChromaDB[(ChromaDB<br/>Vector Database)]
        Docs[(docs/<br/>Course Files)]
    end

    %% External Services
    subgraph External ["☁️ External Services"]
        Claude[Anthropic Claude<br/>claude-sonnet-4]
        Embeddings[SentenceTransformers<br/>all-MiniLM-L6-v2]
    end

    %% Connections
    HTML --> JS
    JS --> FastAPI
    FastAPI --> RAGSys
    RAGSys --> AIGen
    RAGSys --> SessionMgr
    RAGSys --> ToolMgr
    AIGen --> Claude
    ToolMgr --> SearchTool
    SearchTool --> VectorStore
    VectorStore --> ChromaDB
    VectorStore --> Embeddings
    DocProcessor --> ChromaDB
    DocProcessor --> Docs

    %% Styling
    classDef frontend fill:#e1f5fe
    classDef api fill:#f3e5f5
    classDef rag fill:#e8f5e8
    classDef tools fill:#fff3e0
    classDef data fill:#fce4ec
    classDef external fill:#f1f8e9

    class HTML,JS,CSS frontend
    class FastAPI,Routes,Models api
    class RAGSys,AIGen,SessionMgr rag
    class ToolMgr,SearchTool tools
    class VectorStore,DocProcessor,ChromaDB,Docs data
    class Claude,Embeddings external
```

## Data Flow Summary

```mermaid
flowchart LR
    A[👤 User Query] --> B[🎨 Frontend UI]
    B --> C[📡 HTTP POST]
    C --> D[🔌 FastAPI Endpoint]
    D --> E[🧠 RAG System]
    E --> F[🤖 Claude AI + Tools]
    F --> G[🔍 Vector Search]
    G --> H[📊 ChromaDB]
    H --> I[📋 Search Results]
    I --> J[✨ AI Response]
    J --> K[📤 JSON Response]
    K --> L[🎨 UI Update]
    L --> M[👁️ User Sees Answer]

    style A fill:#ffeb3b
    style M fill:#4caf50
    style F fill:#2196f3
    style G fill:#ff9800
    style H fill:#9c27b0
```

## Key Decision Points

1. **Session Creation**: New vs existing conversation
2. **Claude Tool Decision**: Search needed vs direct answer
3. **Vector Search**: Course filtering vs general search  
4. **Response Format**: Markdown rendering + source attribution
5. **Error Handling**: Graceful fallbacks at each layer