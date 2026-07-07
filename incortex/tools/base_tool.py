"""BaseTool — a controlled external ability (Design_Doc §18.1).

Tools are muscles (§11): they execute, they never decide. Every tool
declares its permission level and risk estimates (the Eq 7.1 inputs), and
the class defaults are fail-closed — an unconfigured tool is level 5 with
worst-case risk, so forgetting to classify a tool locks it down rather
than opening it up. Tools must only be invoked through the ToolOrgan,
which runs the safety gate before every execution.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolResult:
    """The outcome of one tool execution. Failures are captured, not raised."""

    tool_name: str
    success: bool
    output: Any = None
    error: str | None = None


class BaseTool:
    # Fail-closed defaults: subclasses must consciously lower these.
    name = "base_tool"
    description = "abstract tool"
    permission_level = 5
    harm_probability = 1.0
    impact = 1.0

    def validate(self, request):
        """Reject malformed requests loudly — a bad request is a caller bug."""
        if not isinstance(request, dict):
            raise ValueError(f"{self.name}: request must be a dict")

    def execute(self, request):
        """Template: validate (raises), run, capture any execution failure."""
        self.validate(request)
        try:
            output = self._execute(request)
        except NotImplementedError:
            raise  # an unimplemented tool is a programming error, not a failure
        except Exception as error:
            return ToolResult(tool_name=self.name, success=False,
                              error=f"{type(error).__name__}: {error}")
        return ToolResult(tool_name=self.name, success=True, output=output)

    def _execute(self, request):
        raise NotImplementedError

    def info(self):
        return {
            "name": self.name,
            "description": self.description,
            "permission_level": self.permission_level,
            "harm_probability": self.harm_probability,
            "impact": self.impact,
        }
