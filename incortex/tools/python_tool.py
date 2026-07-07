"""RunPythonTool — code execution, the canonical always-ask-a-human tool.

Level 4 (Design_Doc §12.9: code execution requires approval), run in a
separate interpreter process with no shell and a hard timeout. Non-zero
exit codes and timeouts are captured failures, never silent.
"""

import subprocess
import sys

from incortex.tools.base_tool import BaseTool

DEFAULT_TIMEOUT_SECONDS = 5.0


class RunPythonTool(BaseTool):
    name = "run_python"
    description = "run a Python snippet in a separate process"
    permission_level = 4  # always requires human approval (Eq 7.2)
    harm_probability = 0.4
    impact = 0.6

    def __init__(self, timeout_seconds=DEFAULT_TIMEOUT_SECONDS):
        self._timeout = timeout_seconds

    def validate(self, request):
        super().validate(request)
        code = request.get("code")
        if not isinstance(code, str) or not code.strip():
            raise ValueError(f"{self.name}: 'code' must be a non-empty string")

    def _execute(self, request):
        try:
            completed = subprocess.run(
                [sys.executable, "-c", request["code"]],
                capture_output=True, text=True, timeout=self._timeout,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"timed out after {self._timeout} seconds")
        if completed.returncode != 0:
            raise RuntimeError(
                f"exit code {completed.returncode}: {completed.stderr.strip()}"
            )
        return {"stdout": completed.stdout, "stderr": completed.stderr,
                "returncode": completed.returncode}
