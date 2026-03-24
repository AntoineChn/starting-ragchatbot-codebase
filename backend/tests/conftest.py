"""
Shared fixtures for the RAG chatbot test suite.
"""
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Mock RAGSystem fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_rag_system():
    """A fully-mocked RAGSystem with sensible defaults."""
    rag = MagicMock()
    rag.query.return_value = ("Test answer.", ["source1.txt", "source2.txt"])
    rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Python Basics", "Advanced FastAPI"],
    }
    rag.session_manager.create_session.return_value = "session_1"
    rag.session_manager.clear_session.return_value = None
    return rag


# ---------------------------------------------------------------------------
# FastAPI test client using a minimal app (no static-file mount)
# ---------------------------------------------------------------------------

@pytest.fixture
def test_app(mock_rag_system):
    """
    Returns a FastAPI app that mirrors app.py's API routes without the
    frontend static-file mount, so tests don't need the ../frontend directory.
    """
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    from typing import List, Optional

    app = FastAPI(title="Test RAG App")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[str]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()
            answer, sources = mock_rag_system.query(request.query, session_id)
            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/sessions/{session_id}")
    async def clear_session(session_id: str):
        mock_rag_system.session_manager.clear_session(session_id)
        return {"status": "cleared"}

    return app


@pytest.fixture
def client(test_app):
    """Starlette TestClient wrapping the minimal test app."""
    from starlette.testclient import TestClient
    return TestClient(test_app)


# ---------------------------------------------------------------------------
# Reusable test data
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_query_payload():
    return {"query": "What is covered in lesson 3?"}


@pytest.fixture
def sample_query_with_session():
    return {"query": "Tell me more.", "session_id": "session_42"}
