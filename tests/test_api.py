"""Phase 10 tests — the REST API (Design_Doc §19).

Every §19.2 endpoint, always answering in the same envelope
{"success", "data", "error"}. The fail-closed rule extends to HTTP: an
unattended server denies level-4 tools, and validation failures are 400s
with readable messages, never stack traces.
"""

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from incortex.api import create_app
from incortex.core import CortexConfig, CortexCore, build_cortex


@pytest.fixture()
def client(tmp_path):
    config = CortexConfig.from_dict(
        {"tools": {"enabled": True, "sandbox_dir": str(tmp_path / "box")}})
    return TestClient(create_app(build_cortex(config)))


def unwrap(response, expected_status=200):
    assert response.status_code == expected_status
    body = response.json()
    assert set(body) == {"success", "data", "error"}
    return body


class TestChatEndpoint:
    def test_teach_answers_and_updates_memory(self, client):
        body = unwrap(client.post(
            "/v1/chat", json={"message": "Teach yourself what gravity is."}))
        assert body["success"] is True
        data = body["data"]
        assert data["response"].startswith("I have learned")
        assert data["accepted"] is True
        assert data["memory_updated"] is True
        assert "language_organ" in data["organs_used"]
        assert 0.0 <= data["confidence"] <= 1.0

    def test_explain_uses_memory(self, client):
        client.post("/v1/chat",
                    json={"message": "Teach yourself what gravity is."})
        data = unwrap(client.post(
            "/v1/chat", json={"message": "What is gravity?"}))["data"]
        assert "From memory" in data["response"]
        assert data["memory_updated"] is False
        assert data["feedback_requested"] is True

    def test_low_confidence_is_not_an_accepted_answer(self, client):
        data = unwrap(client.post(
            "/v1/chat", json={"message": "What is dark matter?"}))["data"]
        assert data["accepted"] is False
        assert "not confident" in data["response"]

    def test_sessions_are_separated(self, client):
        client.post("/v1/chat", json={"message": "hello", "session_id": "a"})
        body = unwrap(client.post(
            "/v1/feedback", json={"success": True, "session_id": "b"}), 400)
        assert body["success"] is False
        assert "session" in body["error"]

    def test_validation_failures_are_readable_400s(self, client):
        body = unwrap(client.post("/v1/chat", json={"message": "   "}), 400)
        assert body["success"] is False
        assert body["data"] is None
        assert "message" in body["error"]
        unwrap(client.post("/v1/chat", json={}), 400)


class TestMemoryEndpoints:
    def test_add_then_search_roundtrip(self, client):
        added = unwrap(client.post(
            "/v1/memory/add",
            json={"content": "photosynthesis turns sunlight into food",
                  "importance": 0.8}))["data"]
        assert added["stored"] == "photosynthesis turns sunlight into food"
        found = unwrap(client.post(
            "/v1/memory/search", json={"query": "photosynthesis"}))["data"]
        assert len(found["results"]) == 1
        assert found["results"][0]["importance"] == pytest.approx(0.8)

    def test_search_respects_top_k(self, client):
        for index in range(4):
            client.post("/v1/memory/add",
                        json={"content": f"cats like fish variant {index}"})
        found = unwrap(client.post(
            "/v1/memory/search",
            json={"query": "cats like fish", "top_k": 2}))["data"]
        assert len(found["results"]) == 2

    def test_validation(self, client):
        unwrap(client.post("/v1/memory/add", json={"content": "  "}), 400)
        unwrap(client.post("/v1/memory/add",
                           json={"content": "x", "importance": 2.0}), 400)
        unwrap(client.post("/v1/memory/search",
                           json={"query": "x", "top_k": 0}), 400)


class TestFeedbackEndpoint:
    def test_feedback_after_a_chat(self, client):
        client.post("/v1/chat",
                    json={"message": "Teach yourself what gravity is."})
        data = unwrap(client.post(
            "/v1/feedback", json={"success": True, "rating": 1.0}))["data"]
        assert data["band"] == "high"
        assert data["learning_score"] == pytest.approx(0.8)

    def test_feedback_with_no_task_is_a_400(self, client):
        body = unwrap(client.post("/v1/feedback", json={"success": True}), 400)
        assert body["success"] is False

    def test_validation(self, client):
        unwrap(client.post("/v1/feedback",
                           json={"success": True, "rating": 1.5}), 400)


class TestIntrospectionEndpoints:
    def test_health_reports_organs_and_system(self, client):
        data = unwrap(client.get("/v1/health"))["data"]
        names = {organ["name"] for organ in data["organs"]}
        assert "language_organ" in names
        assert "tool_organ" in names
        assert data["system"]["tasks_handled"] == 0

    def test_organs_summary(self, client):
        data = unwrap(client.get("/v1/organs"))["data"]
        entry = data["organs"][0]
        assert set(entry) == {"name", "status", "health"}

    def test_cells_are_flattened_across_organs(self, client):
        data = unwrap(client.get("/v1/cells"))["data"]
        names = {cell["name"] for cell in data["cells"]}
        assert {"intent_cell", "vector_memory_cell", "reasoning_cell"} <= names

    def test_logs_return_recent_bus_traffic(self, client):
        client.post("/v1/chat", json={"message": "hello there"})
        data = unwrap(client.get("/v1/logs?count=3"))["data"]
        assert 0 < len(data["messages"]) <= 3
        entry = data["messages"][-1]
        assert {"message_type", "source", "target",
                "confidence", "created_at"} <= set(entry)

    def test_log_count_is_validated(self, client):
        unwrap(client.get("/v1/logs?count=0"), 400)

    def test_log_payloads_are_always_printable(self, client):
        # Payloads may hold arbitrary objects (dicts, lists, tuples,
        # non-JSON types) — the endpoint renders them all
        from incortex.core import new_message
        core = client.app.state.core
        core.bus.publish(new_message(
            "test", "cortex", "system_event",
            {"nested": [1, ("a", object())], "flag": True}))
        data = unwrap(client.get("/v1/logs?count=1"))["data"]
        payload = data["messages"][-1]["payload"]
        assert payload["flag"] is True
        assert isinstance(payload["nested"][1][1], str)


class TestToolsEndpoint:
    def test_safe_tool_executes(self, client):
        client.post("/v1/memory/add", json={"content": "cats like fish"})
        data = unwrap(client.post(
            "/v1/tools/execute",
            json={"tool": "search_memory",
                  "request": {"query": "cats"}}))["data"]
        assert data["decision"] == "executed"
        assert data["output"]["results"]

    def test_level_4_is_denied_on_an_unattended_server(self, client):
        # Fail-closed over HTTP: nobody is at the terminal to say yes
        data = unwrap(client.post(
            "/v1/tools/execute",
            json={"tool": "run_python",
                  "request": {"code": "print(1)"}}))["data"]
        assert data["decision"] == "denied"
        assert data["executed"] is False

    def test_unknown_tool_is_a_404(self, client):
        body = unwrap(client.post(
            "/v1/tools/execute", json={"tool": "warp_drive"}), 404)
        assert "warp_drive" in body["error"]

    def test_no_tool_organ_is_a_clear_400(self):
        toolless = TestClient(create_app(CortexCore()))
        body = unwrap(toolless.post(
            "/v1/tools/execute", json={"tool": "search_memory"}), 400)
        assert "tools" in body["error"]


class TestAppFactory:
    def test_create_app_from_config(self):
        app = create_app(config=CortexConfig())
        client = TestClient(app)
        assert unwrap(client.get("/v1/health"))["success"] is True

    def test_unknown_routes_use_the_envelope_too(self, client):
        body = unwrap(client.get("/v1/telepathy"), 404)
        assert body["success"] is False
