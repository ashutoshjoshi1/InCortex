"""Development tools — the Development Organ's gated abilities (Design_Doc §12.10).

- ListProjectFilesTool (L1): sandboxed codebase inventory
- TestRunnerTool (L4): run pytest in a separate process — code execution,
  so a human must approve; test FAILURES come back as data, not errors,
  because failed tests are what the organ learns from
- CreateGitHubIssueTool (L3): the first GitHub integration — external API,
  locked behind the permission ceiling until configuration raises it
"""

import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

from incortex.tools.base_tool import BaseTool

DEFAULT_EXTENSIONS = (".py", ".md", ".toml", ".txt", ".yml", ".yaml", ".json")
DEFAULT_MAX_FILES = 500
DEFAULT_TEST_TIMEOUT_SECONDS = 120.0
GITHUB_API = "https://api.github.com"
GITHUB_TIMEOUT_SECONDS = 10.0
_SUMMARY_RE = re.compile(r"(\d+) (passed|failed|errors?)")


class ListProjectFilesTool(BaseTool):
    name = "list_project_files"
    description = "inventory the project's source files"
    permission_level = 1  # read-only
    harm_probability = 0.01
    impact = 0.05

    def __init__(self, root, extensions=DEFAULT_EXTENSIONS,
                 max_files=DEFAULT_MAX_FILES):
        self._root = Path(root).resolve()
        self._extensions = extensions
        self._max_files = max_files

    def validate(self, request):
        super().validate(request)
        subdir = request.get("subdir")
        if subdir is not None:
            if not isinstance(subdir, str) or not subdir.strip():
                raise ValueError(f"{self.name}: 'subdir' must be a non-empty string")
            target = (self._root / subdir).resolve()
            if not target.is_relative_to(self._root):
                raise ValueError(f"{self.name}: subdir escapes the sandbox")

    def _execute(self, request):
        base = self._root
        if request.get("subdir"):
            base = (self._root / request["subdir"]).resolve()
        files = []
        truncated = False
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix not in self._extensions:
                continue
            relative = path.relative_to(self._root)
            if any(part.startswith(".") or part == "__pycache__"
                   for part in relative.parts):
                continue
            if len(files) >= self._max_files:
                truncated = True
                break
            files.append({"path": str(relative), "bytes": path.stat().st_size})
        return {"files": files, "truncated": truncated}


class TestRunnerTool(BaseTool):
    __test__ = False  # the name looks like a test class to pytest; it is not
    name = "run_tests"
    description = "run the project's pytest suite in a separate process"
    permission_level = 4  # code execution: always requires a human (Eq 7.2)
    harm_probability = 0.3
    impact = 0.5

    def __init__(self, project_root, timeout_seconds=DEFAULT_TEST_TIMEOUT_SECONDS):
        self._root = Path(project_root).resolve()
        self._timeout = timeout_seconds

    def validate(self, request):
        super().validate(request)
        args = request.get("args", "")
        if not isinstance(args, str):
            raise ValueError(f"{self.name}: 'args' must be a string")

    def _execute(self, request):
        argv = [sys.executable, "-m", "pytest", "-q", "--no-header", "-p",
                "no:cacheprovider"]
        argv += request.get("args", "").split()
        try:
            completed = subprocess.run(argv, cwd=self._root, capture_output=True,
                                       text=True, timeout=self._timeout)
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"timed out after {self._timeout} seconds")
        # Exit 0 = all passed, 1 = some tests failed: both are DATA — the
        # Development Organ learns from failures. Anything else (collection
        # or usage errors) is a genuinely broken invocation.
        if completed.returncode not in (0, 1):
            raise RuntimeError(
                f"pytest exit code {completed.returncode}: "
                f"{(completed.stderr or completed.stdout).strip()[-400:]}"
            )
        counts = {kind: int(number) for number, kind
                  in _SUMMARY_RE.findall(completed.stdout)}
        tail = completed.stdout.strip().splitlines()[-5:]
        return {
            "passed": counts.get("passed", 0),
            "failed": counts.get("failed", 0),
            "exit_code": completed.returncode,
            "tail": tail,
        }


class CreateGitHubIssueTool(BaseTool):
    name = "create_github_issue"
    description = "open an issue on the project's GitHub repository"
    permission_level = 3  # external API action (Design_Doc §12.9)
    harm_probability = 0.2
    impact = 0.4

    def __init__(self, repo, token=None, opener=urllib.request.urlopen):
        if not isinstance(repo, str) or "/" not in repo:
            raise ValueError("repo must look like 'owner/name'")
        self._repo = repo
        self._token = token
        self._opener = opener

    def validate(self, request):
        super().validate(request)
        title = request.get("title")
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"{self.name}: 'title' must be a non-empty string")
        body = request.get("body", "")
        if not isinstance(body, str):
            raise ValueError(f"{self.name}: 'body' must be a string")
        if not self._token:
            raise ValueError(f"{self.name}: no GitHub token configured")

    def _execute(self, request):
        payload = {"title": request["title"], "body": request.get("body", "")}
        http_request = urllib.request.Request(
            f"{GITHUB_API}/repos/{self._repo}/issues",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with self._opener(http_request, timeout=GITHUB_TIMEOUT_SECONDS) as response:
            reply = json.loads(response.read().decode("utf-8"))
        return {"number": reply.get("number"), "url": reply.get("html_url")}
