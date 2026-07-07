"""ToolOrgan — the muscle system (Design_Doc §11, §18).

The single door through which every tool is invoked. Order of checks:

1. Is the tool registered and enabled?
2. The safety gate (Eq 7.1-7.2 via the SafetyOrgan, blocklist included),
   fed the tool's own declared permission level and risk estimates.
3. If the gate says 'require_approval': ask the human approver. The
   default approver denies everything — an unattended brain runs nothing
   risky (fail-closed).
4. Only then execute — and the muscle contract holds: tools execute,
   they never decide.
"""

from incortex.organs.base_organ import BaseOrgan, OrganOutput
from incortex.organs.safety_organ import SafetyOrgan
from incortex.safety import DenyAllApprover
from incortex.tools import ToolRegistry

CAPABILITIES = (
    "tool", "run", "execute", "read", "write", "file",
    "search", "fetch", "code", "api",
)
FAILED_EXECUTION_CONFIDENCE = 0.2


class ToolOrgan(BaseOrgan):
    def __init__(self, name="tool_organ", registry=None, safety=None,
                 approver=None):
        # min mode: a tool chain is never more trustworthy than its weakest step
        super().__init__(name, capability_keywords=CAPABILITIES,
                         confidence_mode="min")
        self.registry = registry or ToolRegistry()
        self.safety = safety or SafetyOrgan(name=f"{name}_gate")
        self.approver = approver or DenyAllApprover()
        # The gate cell is this organ's health-bearing component.
        self.add_cell(self.safety.cells[0], critical=True)

    def invoke(self, tool_name, request=None):
        """Gate, maybe ask a human, then execute. Returns an OrganOutput
        whose content always carries 'decision' and 'executed'."""
        tool = self.registry.get(tool_name)  # unknown tool: loud error
        if not self.registry.is_enabled(tool_name):
            return self._refusal(tool_name, "disabled",
                                 "tool is disabled in the registry")

        gate = self.safety.check(
            tool_name,
            permission_level=tool.permission_level,
            harm_probability=tool.harm_probability,
            impact=tool.impact,
        )
        decision = gate.content["decision"]
        if decision == "block":
            return self._refusal(tool_name, "blocked", gate.content["reason"])
        if decision == "require_approval":
            granted = self.approver.request(tool_name, gate.content["reason"])
            if not granted:
                return self._refusal(tool_name, "denied",
                                     "human approval was not granted")
            return self._run(tool, request, "approved_and_executed")
        return self._run(tool, request, "executed")

    def _run(self, tool, request, decision):
        result = tool.execute(request or {})
        content = {
            "tool": tool.name,
            "decision": decision,
            "executed": True,
            "success": result.success,
            "output": result.output,
            "error": result.error,
        }
        confidence = 1.0 if result.success else FAILED_EXECUTION_CONFIDENCE
        return self._wrap(content, confidence)

    def _refusal(self, tool_name, decision, reason):
        content = {
            "tool": tool_name,
            "decision": decision,
            "executed": False,
            "success": False,
            "output": None,
            "error": reason,
        }
        return self._wrap(content, 1.0)  # a refusal is a confident act

    def _wrap(self, content, confidence):
        return OrganOutput(organ_name=self.name, content=content,
                           confidence=confidence, stage_outputs=())

    def process(self, message):
        if not isinstance(message, dict):
            raise ValueError(f"{self.name}: message must be a dict")
        return self.invoke(message.get("tool"), message.get("request"))
