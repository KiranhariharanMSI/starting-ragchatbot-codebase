import warnings
warnings.filterwarnings("ignore", message="resource_tracker: There appear to be.*")

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import os
import logging
import re
import anthropic
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import Response
from datetime import datetime, timezone

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

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Initialize FastAPI app
app = FastAPI(title="Course Materials RAG System", root_path="")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add trusted host middleware with specific allowed hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=config.ALLOWED_HOSTS
)

# Enable CORS with restricted origins for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["*"],
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'"
    )
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response

# Initialize RAG system
rag_system = RAGSystem(config)

# Pydantic models for request/response
class QueryRequest(BaseModel):
    """Request model for course queries with validation"""
    query: str = Field(
        ..., 
        min_length=1, 
        max_length=config.MAX_QUERY_LENGTH,
        description="User query for course content",
        example="What is the main topic of lesson 1?"
    )
    session_id: Optional[str] = Field(
        None,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Optional session ID for conversation context"
    )

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
@limiter.limit(config.RATE_LIMIT_WINDOW)
async def query_documents(request: Request, query_req: QueryRequest):
    """Process a query and return response with sources"""
    try:
        # Create session if not provided
        session_id = query_req.session_id
        if not session_id:
            session_id = rag_system.session_manager.create_session()
        
        # Process query using RAG system
        answer, sources = rag_system.query(query_req.query, session_id)
        
        return QueryResponse(
            answer=answer,
            sources=sources,
            session_id=session_id
        )
    except anthropic.APIStatusError as e:
        # Log detailed error for debugging but return generic message
        logger.error("Anthropic API error on /api/query. session_id=%s, status_code=%s", 
                    session_id, getattr(e, 'status_code', 'unknown'))
        
        # Return generic error message to prevent information disclosure
        if hasattr(e, 'status_code') and e.status_code == 429:
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
        elif hasattr(e, 'status_code') and e.status_code == 401:
            raise HTTPException(status_code=502, detail="Authentication failed with AI service.")
        else:
            raise HTTPException(status_code=502, detail="AI service temporarily unavailable.")
            
    except anthropic.AnthropicError as e:
        # Log detailed error for debugging but return generic message
        logger.error("Anthropic error on /api/query. session_id=%s, error_type=%s", 
                    session_id, type(e).__name__)
        raise HTTPException(status_code=502, detail="AI service error occurred.")
        
    except Exception as e:
        # Log detailed error for debugging but return generic message
        logger.error("/api/query failed. session_id=%s, error_type=%s", 
                    session_id, type(e).__name__)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.get("/api/courses", response_model=CourseStats)
@limiter.limit("30/minute")
async def get_course_stats(request: Request):
    """Get course analytics and statistics"""
    try:
        analytics = rag_system.get_course_analytics()
        return CourseStats(
            total_courses=analytics["total_courses"],
            course_titles=analytics["course_titles"]
        )
    except Exception as e:
        logger.error("/api/courses failed. error_type=%s", type(e).__name__)
        raise HTTPException(status_code=500, detail="Failed to retrieve course statistics.")

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "0.1.0",
        "services": {
            "rag_system": "operational",
            "vector_store": "operational"
        }
    }

@app.get("/api/metrics")
@limiter.limit("10/minute")
async def get_metrics(request: Request):
    """Basic metrics endpoint for monitoring"""
    try:
        course_count = rag_system.vector_store.get_course_count()
        return {
            "total_courses": course_count,
            "status": "operational"
        }
    except Exception as e:
        logger.error("Metrics endpoint failed. error_type=%s", type(e).__name__)
        raise HTTPException(status_code=500, detail="Metrics unavailable.")

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