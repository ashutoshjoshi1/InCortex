"""Phase 8 tests — the Development Organ.

The success criterion (Design_Doc §21): InCortex can suggest code changes
and create draft pull requests, but cannot merge without human approval.
Everything action-like rides the Phase 7 gate: reading is level 1, running
tests is level 4 (a human must say yes), GitHub issue creation is level 3
(locked behind the ceiling), and merging does not exist as a capability.
"""

import json

import pytest

from incortex.organs import DevelopmentOrgan, LearningOrgan
from incortex.safety import CallbackApprover
from incortex.tools import (
    CreateGitHubIssueTool,
    ListProjectFilesTool,
    TestRunnerTool,
)


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class FakeHttpResponse:
    def __init__(self, body):
        self._body = body

    def read(self, limit=-1):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def make_project(tmp_path):
    """A miniature project: one module, one passing test. Idempotent."""
    (tmp_path / "pkg").mkdir(exist_ok=True)
    (tmp_path / "pkg" / "math_utils.py").write_text(
        "def add(a, b):\n    return a + b\n"
    )
    (tmp_path / "test_ok.py").write_text(
        "def test_ok():\n    assert 1 + 1 == 2\n"
    )
    (tmp_path / "README.md").write_text("# Mini project\n")
    (tmp_path / "__pycache__").mkdir(exist_ok=True)
    (tmp_path / "__pycache__" / "junk.pyc").write_text("junk")
    (tmp_path / ".hidden").mkdir(exist_ok=True)
    (tmp_path / ".hidden" / "secret.py").write_text("x = 1")
    return tmp_path


def make_organ(tmp_path, approve=True, learning=None):
    approver = CallbackApprover(lambda action, reason: approve)
    return DevelopmentOrgan(project_root=make_project(tmp_path),
                            approver=approver, learning=learning,
                            clock=FakeClock())


# ---------------------------------------------------------------------------
# ListProjectFilesTool
# ---------------------------------------------------------------------------


class TestListProjectFilesTool:
    def test_lists_source_files_with_sizes(self, tmp_path):
        tool = ListProjectFilesTool(make_project(tmp_path))
        result = tool.execute({})
        paths = [entry["path"] for entry in result.output["files"]]
        assert "pkg/math_utils.py" in paths
        assert "README.md" in paths
        assert all(entry["bytes"] > 0 for entry in result.output["files"])

    def test_skips_caches_and_hidden_directories(self, tmp_path):
        tool = ListProjectFilesTool(make_project(tmp_path))
        paths = [entry["path"] for entry in tool.execute({}).output["files"]]
        assert not any("__pycache__" in path for path in paths)
        assert not any(path.startswith(".hidden") for path in paths)

    def test_subdir_narrows_the_listing(self, tmp_path):
        tool = ListProjectFilesTool(make_project(tmp_path))
        paths = [entry["path"]
                 for entry in tool.execute({"subdir": "pkg"}).output["files"]]
        assert paths == ["pkg/math_utils.py"]

    def test_subdir_cannot_escape_the_sandbox(self, tmp_path):
        tool = ListProjectFilesTool(make_project(tmp_path))
        with pytest.raises(ValueError, match="sandbox"):
            tool.execute({"subdir": "../elsewhere"})
        with pytest.raises(ValueError, match="non-empty"):
            tool.execute({"subdir": 42})

    def test_file_cap_is_enforced(self, tmp_path):
        tool = ListProjectFilesTool(make_project(tmp_path), max_files=2)
        result = tool.execute({})
        assert len(result.output["files"]) == 2
        assert result.output["truncated"] is True

    def test_is_read_only_level_1(self, tmp_path):
        assert ListProjectFilesTool(tmp_path).permission_level == 1


# ---------------------------------------------------------------------------
# TestRunnerTool
# ---------------------------------------------------------------------------


class TestTestRunnerTool:
    def test_passing_suite_reports_counts(self, tmp_path):
        tool = TestRunnerTool(make_project(tmp_path))
        result = tool.execute({"args": "test_ok.py"})
        assert result.success is True
        assert result.output["passed"] == 1
        assert result.output["failed"] == 0
        assert result.output["exit_code"] == 0

    def test_failing_tests_are_data_not_errors(self, tmp_path):
        # Learn-from-failed-tests requires failures to come back as results
        root = make_project(tmp_path)
        (root / "test_bad.py").write_text(
            "def test_bad():\n    assert 1 == 2\n"
        )
        result = TestRunnerTool(root).execute({"args": "test_bad.py"})
        assert result.success is True  # the run itself worked
        assert result.output["failed"] == 1
        assert result.output["exit_code"] == 1

    def test_a_broken_invocation_is_a_failure(self, tmp_path):
        result = TestRunnerTool(make_project(tmp_path)).execute(
            {"args": "does_not_exist.py"}
        )
        assert result.success is False

    def test_is_code_execution_level_4(self, tmp_path):
        assert TestRunnerTool(tmp_path).permission_level == 4

    def test_validates_args(self, tmp_path):
        with pytest.raises(ValueError):
            TestRunnerTool(tmp_path).execute({"args": 42})

    def test_timeout_is_enforced(self, tmp_path):
        root = make_project(tmp_path)
        (root / "test_slow.py").write_text(
            "import time\ndef test_slow():\n    time.sleep(30)\n"
        )
        result = TestRunnerTool(root, timeout_seconds=2.0).execute(
            {"args": "test_slow.py"})
        assert result.success is False
        assert "timed out" in result.error


# ---------------------------------------------------------------------------
# CreateGitHubIssueTool
# ---------------------------------------------------------------------------


class TestCreateGitHubIssueTool:
    def make_tool(self, captured):
        def opener(request, timeout):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            return FakeHttpResponse(
                b'{"number": 7, "html_url": "https://github.test/i/7"}'
            )

        return CreateGitHubIssueTool("owner/repo", token="tok", opener=opener)

    def test_posts_the_issue_and_returns_its_address(self):
        captured = {}
        result = self.make_tool(captured).execute(
            {"title": "Fix the adder", "body": "add() is off by one"}
        )
        assert result.success is True
        assert result.output == {"number": 7,
                                 "url": "https://github.test/i/7"}
        assert captured["url"] == "https://api.github.com/repos/owner/repo/issues"
        assert captured["payload"] == {"title": "Fix the adder",
                                       "body": "add() is off by one"}
        auth = {k.lower(): v for k, v in captured["headers"].items()}
        assert auth["authorization"] == "Bearer tok"

    def test_requires_a_token(self):
        tool = CreateGitHubIssueTool("owner/repo", token=None,
                                     opener=lambda request, timeout: None)
        with pytest.raises(ValueError, match="token"):
            tool.execute({"title": "x"})

    def test_validates_title_and_repo(self):
        with pytest.raises(ValueError, match="repo"):
            CreateGitHubIssueTool("not-a-repo", token="t")
        tool = CreateGitHubIssueTool("owner/repo", token="t",
                                     opener=lambda request, timeout: None)
        with pytest.raises(ValueError):
            tool.execute({"title": "   "})
        with pytest.raises(ValueError):
            tool.execute({"title": "ok", "body": 42})

    def test_is_an_external_api_level_3(self):
        assert CreateGitHubIssueTool("o/r", token="t").permission_level == 3


# ---------------------------------------------------------------------------
# Issue analysis
# ---------------------------------------------------------------------------


class TestIssueAnalysis:
    def test_classifies_a_bug(self, tmp_path):
        organ = make_organ(tmp_path)
        out = organ.analyze_issue("Crash in add()",
                                  "pkg/math_utils.py raises an error on floats")
        assert out.content["issue_type"] == "bug"
        assert "pkg/math_utils.py" in out.content["mentioned_files"]
        assert out.confidence > 0.5

    @pytest.mark.parametrize(
        ("title", "expected"),
        [
            ("Add support for subtraction", "feature"),
            ("Improve the README documentation", "docs"),
            ("Increase test coverage for pkg", "test"),
        ],
    )
    def test_classifies_other_types(self, tmp_path, title, expected):
        organ = make_organ(tmp_path)
        assert organ.analyze_issue(title, "").content["issue_type"] == expected

    def test_unclassifiable_issues_are_honest(self, tmp_path):
        out = make_organ(tmp_path).analyze_issue("Thoughts?", "hmm")
        assert out.content["issue_type"] == "unknown"
        assert out.confidence == pytest.approx(0.3)

    def test_every_analysis_proposes_first_steps(self, tmp_path):
        out = make_organ(tmp_path).analyze_issue("Crash in add()", "bug")
        assert len(out.content["suggested_steps"]) >= 2

    def test_validates_input(self, tmp_path):
        organ = make_organ(tmp_path)
        with pytest.raises(ValueError):
            organ.analyze_issue("   ", "")
        with pytest.raises(ValueError):
            organ.analyze_issue("Title", body=42)

    def test_process_dispatches_to_analyze(self, tmp_path):
        organ = make_organ(tmp_path)
        out = organ.process({"title": "Crash in add()", "body": "bug"})
        assert out.content["issue_type"] == "bug"
        with pytest.raises(ValueError):
            organ.process("not a dict")


# ---------------------------------------------------------------------------
# Patch suggestion
# ---------------------------------------------------------------------------


class TestPatchSuggestion:
    def test_produces_a_unified_diff(self, tmp_path):
        organ = make_organ(tmp_path)
        out = organ.suggest_patch("pkg/math_utils.py",
                                  find="return a + b",
                                  replace="return float(a) + float(b)",
                                  description="Support float coercion")
        patch = out.content["patch"]
        assert patch["file_path"] == "pkg/math_utils.py"
        assert "--- a/pkg/math_utils.py" in patch["diff"]
        assert "+++ b/pkg/math_utils.py" in patch["diff"]
        assert "-    return a + b" in patch["diff"]
        assert "+    return float(a) + float(b)" in patch["diff"]
        assert out.content["drafted_patches"] == 1

    def test_patch_is_a_draft_the_file_is_untouched(self, tmp_path):
        organ = make_organ(tmp_path)
        organ.suggest_patch("pkg/math_utils.py", find="a + b", replace="b + a",
                            description="Commute")
        source = (tmp_path / "pkg" / "math_utils.py").read_text()
        assert "a + b" in source  # suggesting never writes

    def test_find_text_must_exist(self, tmp_path):
        out = make_organ(tmp_path).suggest_patch(
            "pkg/math_utils.py", find="no such line", replace="x",
            description="d")
        assert out.content["patch"] is None
        assert "not found" in out.content["error"]

    def test_validates_input(self, tmp_path):
        organ = make_organ(tmp_path)
        with pytest.raises(ValueError):
            organ.suggest_patch("pkg/math_utils.py", find="", replace="x",
                                description="d")
        with pytest.raises(ValueError):
            organ.suggest_patch("pkg/math_utils.py", find="x", replace=42,
                                description="d")
        with pytest.raises(ValueError):
            organ.suggest_patch("pkg/math_utils.py", find="x", replace="y",
                                description="  ")

    def test_an_unreadable_file_is_a_refusal_not_a_crash(self, tmp_path):
        out = make_organ(tmp_path).suggest_patch(
            "missing.py", find="x", replace="y", description="d")
        assert out.content["patch"] is None
        assert out.content["error"]


# ---------------------------------------------------------------------------
# Pull request drafts
# ---------------------------------------------------------------------------


class TestPullRequestDrafts:
    def test_draft_collects_the_suggested_patches(self, tmp_path):
        organ = make_organ(tmp_path)
        organ.suggest_patch("pkg/math_utils.py", find="a + b", replace="b + a",
                            description="Commute the addition")
        out = organ.draft_pull_request("Fix float handling",
                                       "Coerce operands to float.")
        draft = out.content["pull_request"]
        assert draft["title"] == "Fix float handling"
        assert draft["status"] == "draft"
        assert draft["branch_name"] == "incortex/fix-float-handling"
        assert "Commute the addition" in draft["body"]
        assert "human" in draft["body"].lower()  # the merge note
        assert len(draft["patches"]) == 1

    def test_drafting_without_patches_is_refused(self, tmp_path):
        out = make_organ(tmp_path).draft_pull_request("Empty", "no changes")
        assert out.content["pull_request"] is None
        assert "no patches" in out.content["error"]

    def test_draft_validates_the_title(self, tmp_path):
        with pytest.raises(ValueError):
            make_organ(tmp_path).draft_pull_request("   ")

    def test_merging_is_structurally_impossible(self, tmp_path):
        organ = make_organ(tmp_path)
        assert not hasattr(organ, "merge")
        assert not hasattr(organ, "merge_pull_request")

    def test_merge_as_an_action_needs_a_human_at_level_5(self, tmp_path):
        # Even asked directly, the gate sends merging to a human (Eq 7.2)
        gate = make_organ(tmp_path).tools.safety.check(
            "merge_pull_request", permission_level=5)
        assert gate.content["decision"] == "require_approval"


# ---------------------------------------------------------------------------
# DevelopmentOrgan — gated reading and test-running
# ---------------------------------------------------------------------------


class TestDevelopmentOrgan:
    def test_read_file_via_the_gate(self, tmp_path):
        out = make_organ(tmp_path).read_file("pkg/math_utils.py")
        assert "def add" in out.content["output"]["content"]
        assert out.content["decision"] == "executed"

    def test_list_files_via_the_gate(self, tmp_path):
        out = make_organ(tmp_path).list_files()
        paths = [entry["path"] for entry in out.content["output"]["files"]]
        assert "pkg/math_utils.py" in paths

    def test_list_files_accepts_a_subdir(self, tmp_path):
        out = make_organ(tmp_path).list_files(subdir="pkg")
        paths = [entry["path"] for entry in out.content["output"]["files"]]
        assert paths == ["pkg/math_utils.py"]

    def test_run_tests_requires_human_approval(self, tmp_path):
        denied = make_organ(tmp_path, approve=False).run_tests("test_ok.py")
        assert denied.content["decision"] == "denied"
        granted = make_organ(tmp_path, approve=True).run_tests("test_ok.py")
        assert granted.content["decision"] == "approved_and_executed"
        assert granted.content["output"]["passed"] == 1

    def test_failed_tests_teach_the_learning_organ(self, tmp_path):
        learning = LearningOrgan()
        organ = make_organ(tmp_path, learning=learning)
        (organ.project_root / "test_bad.py").write_text(
            "def test_bad():\n    assert 1 == 2\n"
        )
        organ.run_tests("test_bad.py")
        entry = learning.log.recent(1)[0]
        assert entry["success"] is False
        assert "test_bad.py" in entry["description"]
        assert len(learning.tracker.clusters) == 1

    def test_passing_tests_are_also_recorded(self, tmp_path):
        learning = LearningOrgan()
        make_organ(tmp_path, learning=learning).run_tests("test_ok.py")
        assert learning.log.recent(1)[0]["success"] is True
        assert learning.tracker.clusters == ()

    def test_health_is_active(self, tmp_path):
        assert make_organ(tmp_path).health_check()["status"] == "active"

    def test_relevant_to_development_requests(self, tmp_path):
        assert make_organ(tmp_path).relevance("run the tests and patch it") > 0.0


# ---------------------------------------------------------------------------
# Phase 8 success criterion (Design_Doc §21): suggest changes and draft PRs,
# but never merge without a human.
# ---------------------------------------------------------------------------


class TestPhase8SuccessCriteria:
    def test_the_full_development_loop(self, tmp_path):
        learning = LearningOrgan()
        organ = make_organ(tmp_path, approve=True, learning=learning)

        # Understand the issue
        issue = organ.analyze_issue(
            "Bug: add() breaks on float strings",
            "pkg/math_utils.py should coerce inputs")
        assert issue.content["issue_type"] == "bug"

        # Read the code, run the tests (human approved), suggest a fix
        organ.read_file("pkg/math_utils.py")
        tests = organ.run_tests("test_ok.py")
        assert tests.content["output"]["passed"] == 1
        patched = organ.suggest_patch(
            "pkg/math_utils.py", find="return a + b",
            replace="return float(a) + float(b)",
            description="Coerce operands to float")
        assert patched.content["patch"] is not None

        # Draft the pull request — and confirm merging is not ours to do
        pr = organ.draft_pull_request("Fix float handling in add()",
                                      "Closes the coercion bug.")
        assert pr.content["pull_request"]["status"] == "draft"
        assert not hasattr(organ, "merge")
