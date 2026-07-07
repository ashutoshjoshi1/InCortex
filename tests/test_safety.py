"""Phase 7 tests — tools, permissions, and human approval.

The phase's success criterion (Design_Doc §21): InCortex uses tools only
after safety approval. Every invocation flows through the Eq 7.1-7.2 gate;
level-4 tools need a human 'yes'; sandboxed file tools refuse to escape;
and the default approver denies everything (fail-closed).
"""

import pytest

from incortex.core import CortexCore
from incortex.memory import MemoryManager
from incortex.organs import SafetyOrgan, ToolOrgan
from incortex.safety import BaseApprover, CallbackApprover, DenyAllApprover
from incortex.tools import (
    ApiTool,
    BaseTool,
    ReadFileTool,
    RunPythonTool,
    SearchMemoryTool,
    ToolRegistry,
    ToolResult,
    WriteFileTool,
)


class EchoTool(BaseTool):
    name = "echo"
    description = "repeats its input"
    permission_level = 1
    harm_probability = 0.01
    impact = 0.01

    def validate(self, request):
        super().validate(request)
        if not isinstance(request.get("text"), str):
            raise ValueError("echo needs a 'text' string")

    def _execute(self, request):
        return {"echoed": request["text"]}


class ExplodingTool(BaseTool):
    name = "exploder"
    description = "always fails"
    permission_level = 1
    harm_probability = 0.01
    impact = 0.01

    def _execute(self, request):
        raise RuntimeError("boom")


class FakeResponse:
    def __init__(self, body):
        self._body = body

    def read(self, limit=-1):
        return self._body[:limit] if limit > 0 else self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


# ---------------------------------------------------------------------------
# BaseTool — the muscle fiber contract
# ---------------------------------------------------------------------------


class TestBaseTool:
    def test_execute_wraps_success(self):
        result = EchoTool().execute({"text": "hi"})
        assert result == ToolResult(tool_name="echo", success=True,
                                    output={"echoed": "hi"}, error=None)

    def test_execution_errors_are_captured_never_swallowed(self):
        result = ExplodingTool().execute({})
        assert result.success is False
        assert "RuntimeError: boom" in result.error

    def test_validation_errors_raise_to_the_caller(self):
        with pytest.raises(ValueError):
            EchoTool().execute({"text": 42})
        with pytest.raises(ValueError):
            EchoTool().execute("not a dict")

    def test_defaults_are_fail_closed(self):
        # An unconfigured tool is maximally restricted (level 5, worst-case risk)
        assert BaseTool.permission_level == 5
        assert BaseTool.harm_probability == 1.0
        assert BaseTool.impact == 1.0
        with pytest.raises(NotImplementedError):
            BaseTool().execute({})

    def test_info_shape(self):
        info = EchoTool().info()
        assert info == {"name": "echo", "description": "repeats its input",
                        "permission_level": 1, "harm_probability": 0.01,
                        "impact": 0.01}


# ---------------------------------------------------------------------------
# ToolRegistry
# ---------------------------------------------------------------------------


class TestToolRegistry:
    def test_register_and_get(self):
        registry = ToolRegistry()
        tool = EchoTool()
        registry.register(tool)
        assert registry.get("echo") is tool
        assert len(registry) == 1

    def test_rejects_duplicates_and_non_tools(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        with pytest.raises(ValueError):
            registry.register(EchoTool())
        with pytest.raises(ValueError):
            registry.register("not a tool")

    def test_unknown_tool_is_an_error(self):
        with pytest.raises(ValueError):
            ToolRegistry().get("missing")

    def test_enable_disable(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        assert registry.is_enabled("echo") is True
        registry.disable("echo")
        assert registry.is_enabled("echo") is False
        registry.enable("echo")
        assert registry.is_enabled("echo") is True
        with pytest.raises(ValueError):
            registry.disable("missing")

    def test_list_tools(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        registry.disable("echo")
        listing = registry.list_tools()
        assert listing[0]["name"] == "echo"
        assert listing[0]["enabled"] is False
        assert listing[0]["permission_level"] == 1


# ---------------------------------------------------------------------------
# File tools — sandboxed (security: no path escapes, ever)
# ---------------------------------------------------------------------------


class TestFileTools:
    def test_write_then_read_roundtrip(self, tmp_path):
        write = WriteFileTool(tmp_path)
        read = ReadFileTool(tmp_path)
        written = write.execute({"path": "notes/hello.txt", "content": "Hello"})
        assert written.success is True
        assert written.output["bytes_written"] == 5
        result = read.execute({"path": "notes/hello.txt"})
        assert result.output["content"] == "Hello"

    def test_traversal_escape_is_rejected_at_validation(self, tmp_path):
        with pytest.raises(ValueError, match="sandbox"):
            ReadFileTool(tmp_path).execute({"path": "../outside.txt"})
        with pytest.raises(ValueError, match="sandbox"):
            WriteFileTool(tmp_path).execute({"path": "../../evil", "content": "x"})

    def test_absolute_paths_are_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="sandbox"):
            ReadFileTool(tmp_path).execute({"path": "/etc/passwd"})

    def test_missing_file_is_a_captured_failure(self, tmp_path):
        result = ReadFileTool(tmp_path).execute({"path": "nowhere.txt"})
        assert result.success is False
        assert result.error

    def test_oversized_file_is_refused(self, tmp_path):
        (tmp_path / "big.txt").write_text("x" * 100)
        result = ReadFileTool(tmp_path, max_bytes=10).execute({"path": "big.txt"})
        assert result.success is False
        assert "too large" in result.error

    def test_request_validation(self, tmp_path):
        with pytest.raises(ValueError):
            ReadFileTool(tmp_path).execute({})
        with pytest.raises(ValueError):
            WriteFileTool(tmp_path).execute({"path": "a.txt", "content": 42})

    def test_permission_levels_match_the_design_doc(self, tmp_path):
        assert ReadFileTool(tmp_path).permission_level == 1   # read-only
        assert WriteFileTool(tmp_path).permission_level == 2  # local safe write


# ---------------------------------------------------------------------------
# Search, code, and API tools
# ---------------------------------------------------------------------------


class TestSearchMemoryTool:
    def test_searches_the_memory_manager(self):
        manager = MemoryManager()
        manager.remember("photosynthesis turns sunlight into food")
        tool = SearchMemoryTool(manager)
        result = tool.execute({"query": "photosynthesis"})
        assert result.success is True
        assert "photosynthesis" in result.output["results"][0]["content"]

    def test_validates_query(self):
        with pytest.raises(ValueError):
            SearchMemoryTool(MemoryManager()).execute({"query": "  "})
        with pytest.raises(ValueError):
            SearchMemoryTool(MemoryManager()).execute({"query": "x", "top_k": 0})


class TestRunPythonTool:
    def test_runs_code_and_captures_output(self):
        result = RunPythonTool().execute({"code": "print(2 + 2)"})
        assert result.success is True
        assert result.output["stdout"] == "4\n"

    def test_failing_code_is_a_captured_failure(self):
        result = RunPythonTool().execute({"code": "raise ValueError('nope')"})
        assert result.success is False
        assert "nope" in result.error

    def test_timeout_is_enforced(self):
        tool = RunPythonTool(timeout_seconds=0.5)
        result = tool.execute({"code": "import time; time.sleep(5)"})
        assert result.success is False
        assert "timed out" in result.error

    def test_is_a_level_4_tool(self):
        # Design_Doc §12.9: code execution always requires a human
        assert RunPythonTool().permission_level == 4

    def test_validates_code(self):
        with pytest.raises(ValueError):
            RunPythonTool().execute({"code": "   "})


class TestApiTool:
    def test_fetches_a_url(self):
        tool = ApiTool(opener=lambda url, timeout: FakeResponse(b"hello api"))
        result = tool.execute({"url": "https://example.test/data"})
        assert result.success is True
        assert result.output["body"] == "hello api"

    def test_only_http_schemes_are_allowed(self):
        tool = ApiTool(opener=lambda url, timeout: FakeResponse(b""))
        with pytest.raises(ValueError, match="http"):
            tool.execute({"url": "file:///etc/passwd"})

    def test_oversized_responses_are_refused(self):
        tool = ApiTool(opener=lambda url, timeout: FakeResponse(b"123456"),
                       max_bytes=5)
        result = tool.execute({"url": "https://example.test/big"})
        assert result.success is False
        assert "too large" in result.error

    def test_is_a_level_3_tool(self):
        assert ApiTool().permission_level == 3


# ---------------------------------------------------------------------------
# Approvers — the human in the loop
# ---------------------------------------------------------------------------


class TestApprovers:
    def test_default_denies_everything(self):
        approver = DenyAllApprover()
        assert approver.request("run_python", "level 4") is False
        assert approver.decisions[0] == {"action": "run_python",
                                         "reason": "level 4", "granted": False}

    def test_callback_approver_asks_the_callback(self):
        approver = CallbackApprover(lambda action, reason: action == "run_python")
        assert approver.request("run_python", "r") is True
        assert approver.request("send_email", "r") is False

    def test_decision_log_is_bounded(self):
        approver = DenyAllApprover(log_size=2)
        for i in range(3):
            approver.request(f"action_{i}", "r")
        assert len(approver.decisions) == 2
        assert approver.decisions[0]["action"] == "action_1"

    def test_base_approver_is_abstract(self):
        with pytest.raises(NotImplementedError):
            BaseApprover().request("x", "r")

    def test_callback_must_be_callable(self):
        with pytest.raises(ValueError):
            CallbackApprover("not callable")


# ---------------------------------------------------------------------------
# ToolOrgan — the muscle system (gate before every execution)
# ---------------------------------------------------------------------------


def make_organ(approver=None, safety=None, extra_tools=()):
    registry = ToolRegistry()
    registry.register(EchoTool())
    registry.register(RunPythonTool())
    for tool in extra_tools:
        registry.register(tool)
    return ToolOrgan(registry=registry, safety=safety, approver=approver)


class TestToolOrgan:
    def test_safe_tool_executes_without_bothering_a_human(self):
        approver = DenyAllApprover()
        organ = make_organ(approver=approver)
        out = organ.invoke("echo", {"text": "hi"})
        assert out.content["decision"] == "executed"
        assert out.content["output"] == {"echoed": "hi"}
        assert approver.decisions == ()  # never consulted

    def test_level_4_tool_is_denied_by_the_default_approver(self):
        organ = make_organ()  # DenyAllApprover by default: fail-closed
        out = organ.invoke("run_python", {"code": "print(1)"})
        assert out.content["decision"] == "denied"
        assert out.content["executed"] is False

    def test_level_4_tool_runs_after_a_human_yes(self):
        organ = make_organ(approver=CallbackApprover(lambda a, r: True))
        out = organ.invoke("run_python", {"code": "print(2 + 2)"})
        assert out.content["decision"] == "approved_and_executed"
        assert out.content["output"]["stdout"] == "4\n"

    def test_over_ceiling_tool_is_blocked_even_with_a_willing_approver(self):
        # api_get is level 3: above the default ceiling (2), below the
        # always-ask tier (4), low risk -> block; approval is never an option
        approver = CallbackApprover(lambda a, r: True)
        organ = make_organ(approver=approver,
                           extra_tools=[ApiTool(opener=lambda u, timeout=None: FakeResponse(b"x"))])
        out = organ.invoke("api_get", {"url": "https://example.test/"})
        assert out.content["decision"] == "blocked"
        assert approver.decisions == ()

    def test_raising_the_ceiling_unlocks_level_3(self):
        organ = make_organ(
            safety=SafetyOrgan(max_auto_level=3),
            extra_tools=[ApiTool(opener=lambda u, timeout=None: FakeResponse(b"ok"))],
        )
        out = organ.invoke("api_get", {"url": "https://example.test/"})
        assert out.content["decision"] == "executed"
        assert out.content["output"]["body"] == "ok"

    def test_disabled_tools_are_refused(self):
        organ = make_organ()
        organ.registry.disable("echo")
        out = organ.invoke("echo", {"text": "hi"})
        assert out.content["decision"] == "disabled"
        assert out.content["executed"] is False

    def test_unknown_tools_are_an_error(self):
        with pytest.raises(ValueError):
            make_organ().invoke("missing")

    def test_blocklisted_names_stay_blocked(self):
        organ = make_organ(
            safety=SafetyOrgan(blocked_actions=frozenset({"echo"})))
        assert organ.invoke("echo", {"text": "x"}).content["decision"] == "blocked"

    def test_failed_execution_has_low_confidence(self):
        organ = make_organ(extra_tools=[ExplodingTool()])
        out = organ.invoke("exploder", {})
        assert out.content["success"] is False
        assert out.confidence == pytest.approx(0.2)

    def test_every_invocation_is_gate_logged(self):
        organ = make_organ()
        organ.invoke("echo", {"text": "one"})
        organ.invoke("run_python", {"code": "print(1)"})
        actions = [entry["action"] for entry in organ.safety.decisions]
        assert actions == ["echo", "run_python"]

    def test_process_takes_a_dict(self):
        organ = make_organ()
        out = organ.process({"tool": "echo", "request": {"text": "hi"}})
        assert out.content["output"] == {"echoed": "hi"}
        with pytest.raises(ValueError):
            organ.process("not a dict")

    def test_health_is_active(self):
        assert make_organ().health_check()["status"] == "active"


# ---------------------------------------------------------------------------
# Cortex integration + Phase 7 success criterion (Design_Doc §21):
# InCortex uses tools only after safety approval.
# ---------------------------------------------------------------------------


class TestPhase7SuccessCriteria:
    def test_cortex_health_includes_the_tool_organ(self):
        core = CortexCore(tools=make_organ())
        names = {organ["name"] for organ in core.health_check()["organs"]}
        assert "tool_organ" in names

    def test_tools_run_only_after_safety_approval(self):
        asked = []

        def human(action, reason):
            asked.append(action)
            return len(asked) > 1  # deny the first request, grant the second

        organ = make_organ(approver=CallbackApprover(human))
        denied = organ.invoke("run_python", {"code": "print('should not run')"})
        assert denied.content["executed"] is False
        granted = organ.invoke("run_python", {"code": "print('approved')"})
        assert granted.content["output"]["stdout"] == "approved\n"
        assert asked == ["run_python", "run_python"]
