"""DevelopmentOrgan — InCortex helping develop itself, safely (Design_Doc §12.10).

It can read the codebase, analyze issues, run tests (through the level-4
gate: a human must approve), suggest patches as unified diffs, and draft
pull requests. It deliberately has NO merge capability — the safe
self-development rule: suggest, never approve your own changes.
"""

import difflib
import re
import time
import uuid

from incortex.cells.cell_math import clip01
from incortex.organs.base_organ import BaseOrgan, OrganOutput
from incortex.organs.tool_organ import ToolOrgan
from incortex.tools import ListProjectFilesTool, ReadFileTool, TestRunnerTool, ToolRegistry

CAPABILITIES = (
    "code", "patch", "diff", "test", "tests", "issue", "bug",
    "pull", "branch", "develop", "refactor", "codebase",
)
ISSUE_KEYWORDS = {
    "bug": ("bug", "crash", "error", "broken", "fails", "breaks", "wrong",
            "raises", "exception"),
    "feature": ("add", "support", "feature", "implement", "new", "allow"),
    "docs": ("doc", "docs", "documentation", "readme", "explain", "typo"),
    "test": ("test", "tests", "coverage", "flaky"),
}
ISSUE_TYPE_CONFIDENCE = 0.8
UNKNOWN_ISSUE_CONFIDENCE = 0.3
_FILE_MENTION_RE = re.compile(r"[\w./-]+\.(?:py|md|toml|txt|yml|yaml|json)")
_SLUG_RE = re.compile(r"[^a-z0-9]+")
MERGE_NOTE = ("This pull request was drafted by InCortex. A human must review "
              "and merge it - InCortex cannot and will not merge its own changes.")


class DevelopmentOrgan(BaseOrgan):
    def __init__(self, name="development_organ", project_root=".",
                 tools=None, approver=None, learning=None, clock=time.time):
        super().__init__(name, capability_keywords=CAPABILITIES,
                         confidence_mode="min")
        from pathlib import Path
        self.project_root = Path(project_root).resolve()
        self._learning = learning
        self._clock = clock
        self._patches = []
        if tools is None:
            registry = ToolRegistry()
            registry.register(ReadFileTool(self.project_root))
            registry.register(ListProjectFilesTool(self.project_root))
            registry.register(TestRunnerTool(self.project_root))
            tools = ToolOrgan(name=f"{name}_tools", registry=registry,
                              approver=approver)
        self.tools = tools
        # The gate cell carries this organ's health, as in the ToolOrgan.
        self.add_cell(self.tools.safety.cells[0], critical=True)

    # -- gated abilities ------------------------------------------------------

    def read_file(self, path):
        """Read one project file through the gate (level 1)."""
        return self._rewrap(self.tools.invoke("read_file", {"path": path}))

    def list_files(self, subdir=None):
        """Inventory the codebase through the gate (level 1)."""
        request = {} if subdir is None else {"subdir": subdir}
        return self._rewrap(self.tools.invoke("list_project_files", request))

    def run_tests(self, args=""):
        """Run the test suite through the gate (level 4 — human approval).

        §12.10: 'learn from failed tests' — outcomes feed the Learning Organ.
        """
        out = self.tools.invoke("run_tests", {"args": args})
        content = out.content
        if self._learning is not None and content["executed"] and content["success"]:
            failed = content["output"]["failed"]
            self._learning.score(
                {"success": failed == 0},
                description=(f"test run '{args or 'all'}': "
                             f"{content['output']['passed']} passed, "
                             f"{failed} failed"),
            )
        return self._rewrap(out)

    # -- pure computation (no side effects, nothing to gate) -------------------

    def analyze_issue(self, title, body=""):
        """Understand an issue: classify it, spot file mentions, plan steps."""
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"{self.name}: issue title must be a non-empty string")
        if not isinstance(body, str):
            raise ValueError(f"{self.name}: issue body must be a string")
        text = f"{title} {body}".lower()
        words = set(re.findall(r"[a-z]+", text))
        issue_type = "unknown"
        for candidate, keywords in ISSUE_KEYWORDS.items():
            if words & set(keywords):
                issue_type = candidate
                break
        mentioned = sorted(set(_FILE_MENTION_RE.findall(f"{title} {body}")))
        steps = [f"Read the mentioned files: {', '.join(mentioned)}"
                 if mentioned else "List the project files and locate the area"]
        steps.append("Run the existing tests to establish a baseline")
        if issue_type == "bug":
            steps.append("Write a failing test that reproduces the bug")
        steps.append("Suggest a patch and draft a pull request for human review")
        confidence = (ISSUE_TYPE_CONFIDENCE if issue_type != "unknown"
                      else UNKNOWN_ISSUE_CONFIDENCE)
        content = {
            "issue_type": issue_type,
            "mentioned_files": mentioned,
            "suggested_steps": steps,
        }
        return OrganOutput(organ_name=self.name, content=content,
                           confidence=confidence, stage_outputs=())

    def suggest_patch(self, file_path, find, replace, description):
        """Draft a unified-diff patch. Never touches the file itself."""
        if not isinstance(find, str) or not find:
            raise ValueError(f"{self.name}: 'find' must be a non-empty string")
        if not isinstance(replace, str):
            raise ValueError(f"{self.name}: 'replace' must be a string")
        if not isinstance(description, str) or not description.strip():
            raise ValueError(f"{self.name}: 'description' must be non-empty")
        read = self.tools.invoke("read_file", {"path": file_path})
        if not (read.content["executed"] and read.content["success"]):
            return self._patch_refusal(read.content["error"])
        original = read.content["output"]["content"]
        if find not in original:
            return self._patch_refusal(
                f"'find' text not found in {file_path}")
        modified = original.replace(find, replace, 1)
        diff = "\n".join(difflib.unified_diff(
            original.splitlines(), modified.splitlines(),
            fromfile=f"a/{file_path}", tofile=f"b/{file_path}", lineterm="",
        ))
        patch = {
            "patch_id": uuid.uuid4().hex,
            "file_path": file_path,
            "description": description.strip(),
            "diff": diff,
            "created_at": self._clock(),
        }
        self._patches.append(patch)
        content = {"patch": patch, "error": None,
                   "drafted_patches": len(self._patches)}
        return OrganOutput(organ_name=self.name, content=content,
                           confidence=clip01(read.confidence),
                           stage_outputs=(read,))

    def draft_pull_request(self, title, description=""):
        """Bundle the suggested patches into a PR draft for a human to review.

        There is no merge method on this organ, by design (§12.10).
        """
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"{self.name}: PR title must be a non-empty string")
        if not self._patches:
            content = {"pull_request": None, "error": "no patches drafted yet"}
            return OrganOutput(organ_name=self.name, content=content,
                               confidence=1.0, stage_outputs=())
        slug = _SLUG_RE.sub("-", title.lower()).strip("-")
        lines = [description.strip(), "", "## Patches"]
        for patch in self._patches:
            lines.append(f"- `{patch['file_path']}`: {patch['description']}")
        lines += ["", "## Review checklist",
                  "- [ ] A human has reviewed every diff",
                  "- [ ] Tests pass", "", MERGE_NOTE]
        draft = {
            "pr_id": uuid.uuid4().hex,
            "title": title.strip(),
            "branch_name": f"incortex/{slug}",
            "body": "\n".join(lines).strip(),
            "patches": tuple(self._patches),
            "status": "draft",
            "created_at": self._clock(),
        }
        content = {"pull_request": draft, "error": None}
        return OrganOutput(organ_name=self.name, content=content,
                           confidence=1.0, stage_outputs=())

    def process(self, message):
        if not isinstance(message, dict):
            raise ValueError(f"{self.name}: message must be a dict")
        return self.analyze_issue(message.get("title"), message.get("body", ""))

    # -- helpers ----------------------------------------------------------------

    def _patch_refusal(self, error):
        content = {"patch": None, "error": error,
                   "drafted_patches": len(self._patches)}
        return OrganOutput(organ_name=self.name, content=content,
                           confidence=1.0, stage_outputs=())

    def _rewrap(self, tool_output):
        return OrganOutput(organ_name=self.name, content=tool_output.content,
                           confidence=tool_output.confidence,
                           stage_outputs=(tool_output,))
