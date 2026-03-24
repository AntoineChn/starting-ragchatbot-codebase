"""
API endpoint tests for the RAG chatbot.

Uses the minimal test app defined in conftest.py (no static-file mount)
so tests run without the ../frontend directory present.
"""
import pytest


# ---------------------------------------------------------------------------
# POST /api/query
# ---------------------------------------------------------------------------

class TestQueryEndpoint:

    def test_returns_200_with_valid_payload(self, client, sample_query_payload):
        response = client.post("/api/query", json=sample_query_payload)
        assert response.status_code == 200

    def test_response_shape(self, client, sample_query_payload):
        data = client.post("/api/query", json=sample_query_payload).json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

    def test_answer_and_sources_come_from_rag_system(self, client, sample_query_payload, mock_rag_system):
        mock_rag_system.query.return_value = ("Mocked answer.", ["doc_a.txt"])
        data = client.post("/api/query", json=sample_query_payload).json()
        assert data["answer"] == "Mocked answer."
        assert data["sources"] == ["doc_a.txt"]

    def test_auto_creates_session_when_none_provided(self, client, mock_rag_system):
        mock_rag_system.session_manager.create_session.return_value = "session_99"
        data = client.post("/api/query", json={"query": "Hello"}).json()
        assert data["session_id"] == "session_99"
        mock_rag_system.session_manager.create_session.assert_called_once()

    def test_uses_provided_session_id(self, client, sample_query_with_session, mock_rag_system):
        data = client.post("/api/query", json=sample_query_with_session).json()
        assert data["session_id"] == "session_42"
        # No new session should be created
        mock_rag_system.session_manager.create_session.assert_not_called()

    def test_passes_query_to_rag_system(self, client, mock_rag_system):
        client.post("/api/query", json={"query": "specific question"})
        call_args = mock_rag_system.query.call_args
        assert "specific question" in call_args[0]

    def test_returns_500_when_rag_raises(self, client, mock_rag_system):
        mock_rag_system.query.side_effect = RuntimeError("ChromaDB unavailable")
        response = client.post("/api/query", json={"query": "Will fail"})
        assert response.status_code == 500
        assert "ChromaDB unavailable" in response.json()["detail"]

    def test_missing_query_field_returns_422(self, client):
        response = client.post("/api/query", json={"session_id": "s1"})
        assert response.status_code == 422

    def test_sources_is_a_list(self, client, sample_query_payload):
        data = client.post("/api/query", json=sample_query_payload).json()
        assert isinstance(data["sources"], list)


# ---------------------------------------------------------------------------
# GET /api/courses
# ---------------------------------------------------------------------------

class TestCoursesEndpoint:

    def test_returns_200(self, client):
        response = client.get("/api/courses")
        assert response.status_code == 200

    def test_response_shape(self, client):
        data = client.get("/api/courses").json()
        assert "total_courses" in data
        assert "course_titles" in data

    def test_course_data_comes_from_rag_system(self, client, mock_rag_system):
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 3,
            "course_titles": ["A", "B", "C"],
        }
        data = client.get("/api/courses").json()
        assert data["total_courses"] == 3
        assert data["course_titles"] == ["A", "B", "C"]

    def test_returns_500_when_analytics_raises(self, client, mock_rag_system):
        mock_rag_system.get_course_analytics.side_effect = Exception("DB error")
        response = client.get("/api/courses")
        assert response.status_code == 500

    def test_course_titles_is_a_list(self, client):
        data = client.get("/api/courses").json()
        assert isinstance(data["course_titles"], list)

    def test_total_courses_is_an_integer(self, client):
        data = client.get("/api/courses").json()
        assert isinstance(data["total_courses"], int)


# ---------------------------------------------------------------------------
# DELETE /api/sessions/{session_id}
# ---------------------------------------------------------------------------

class TestClearSessionEndpoint:

    def test_returns_200(self, client):
        response = client.delete("/api/sessions/session_1")
        assert response.status_code == 200

    def test_response_body(self, client):
        data = client.delete("/api/sessions/session_1").json()
        assert data == {"status": "cleared"}

    def test_delegates_to_session_manager(self, client, mock_rag_system):
        client.delete("/api/sessions/session_abc")
        mock_rag_system.session_manager.clear_session.assert_called_once_with("session_abc")
