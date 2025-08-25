import warnings
warnings.filterwarnings("ignore", message="resource_tracker: There appear to be.*")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import logging
import re
import anthropic

# Create a module logger
logger = logging.getLogger(__name__)

# Ensure logging is configured (useful when running via uv run/uvicorn)
if not logging.getLogger().handlers:
    from .config import config
    log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.ERROR)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )

from .config import config
from .rag_system import RAGSystem

# Initialize FastAPI app
app = FastAPI(title="Course Materials RAG System", root_path="")

# Add trusted host middleware for proxy
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

# Enable CORS with proper settings for proxy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Initialize RAG system
rag_system = RAGSystem(config)

# Pydantic models for request/response
class QueryRequest(BaseModel):
    """Request model for course queries"""
    query: str
    session_id: Optional[str] = None

class QueryResponse(BaseModel):
    """Response model for course queries"""
    answer: str
    sources: List[str]
    session_id: str

class CourseStats(BaseModel):
    """Response model for course statistics"""
    total_courses: int
    course_titles: List[str]

# API Endpoints

@app.post("/api/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Process a query and return response with sources"""
    try:
        # Create session if not provided
        session_id = request.session_id
        if not session_id:
            session_id = rag_system.session_manager.create_session()
        
        # Process query using RAG system
        answer, sources = rag_system.query(request.query, session_id)
        
        return QueryResponse(
            answer=answer,
            sources=sources,
            session_id=session_id
        )
    except anthropic.APIStatusError as e:
        # Return unified message
        err_msg = None
        try:
            # Prefer structured response if present
            resp = getattr(e, "response", None)
            if isinstance(resp, dict):
                err = resp.get("error", {})
                err_msg = err.get("message")
        except Exception:
            pass
        if not err_msg:
            # Try to extract `'message': '...'` or "message": "..." from string form
            s = str(e)
            m = re.search(r"'message'\s*:\s*'([^']+)'", s)
            if not m:
                m = re.search(r'"message"\s*:\s*"([^"]+)"', s)
            if m:
                err_msg = m.group(1)
        logger.exception("Anthropic API error on /api/query. session_id=%s, query=%s", session_id, request.query)
        detail_text = err_msg or str(e) or "Unknown error"
        raise HTTPException(status_code=502, detail=f"call to LLM failed. Message is \"{detail_text}\"")
    except anthropic.AnthropicError as e:
        # Broader Anthropic errors – return unified message including only provider's inner error message when available
        err_msg = None
        try:
            # Many Anthropic errors expose a .response with an 'error' object
            resp = getattr(e, "response", None) or {}
            err = resp.get("error", {}) if isinstance(resp, dict) else {}
            err_msg = err.get("message")
        except Exception:
            pass
        # Fallback: try to extract `'message': '...'` from stringified error
        detail_text = err_msg or str(e) or "Unknown error"
        raise HTTPException(status_code=502, detail=f"call to LLM failed. Message is \"{detail_text}\"")
    except Exception as e:
        logger.exception("/api/query failed. session_id=%s, query=%s", session_id, request.query)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/courses", response_model=CourseStats)
async def get_course_stats():
    """Get course analytics and statistics"""
    try:
        analytics = rag_system.get_course_analytics()
        return CourseStats(
            total_courses=analytics["total_courses"],
            course_titles=analytics["course_titles"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    """Load initial documents on startup"""
    # Get absolute path to docs folder
    current_dir = os.path.dirname(os.path.abspath(__file__))
    docs_path = os.path.join(os.path.dirname(current_dir), "docs")
    
    if os.path.exists(docs_path):
        print(f"Loading initial documents from {docs_path}...")
        try:
            courses, chunks = rag_system.add_course_folder(docs_path, clear_existing=False)
            print(f"Loaded {courses} courses with {chunks} chunks")
        except Exception as e:
            print(f"Error loading documents: {e}")
    else:
        print(f"Documents folder not found at {docs_path}")

# Custom static file handler with no-cache headers for development
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from pathlib import Path


class DevStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if isinstance(response, FileResponse):
            # Add no-cache headers for development
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response
    
    
# Serve static files for the frontend
# Resolve the absolute path to the frontend directory relative to this file
FRONTEND_DIR = (Path(__file__).resolve().parent.parent / "frontend")
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="static")