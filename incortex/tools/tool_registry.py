"""ToolRegistry — the catalogue of available abilities (Design_Doc §18.2)."""

from incortex.tools.base_tool import BaseTool


class ToolRegistry:
    def __init__(self):
        self._tools = {}
        self._enabled = set()

    def register(self, tool):
        if not isinstance(tool, BaseTool):
            raise ValueError("only BaseTool instances can be registered")
        if tool.name in self._tools:
            raise ValueError(f"a tool named '{tool.name}' is already registered")
        self._tools[tool.name] = tool
        self._enabled.add(tool.name)

    def get(self, name):
        if name not in self._tools:
            raise ValueError(f"no tool named '{name}'")
        return self._tools[name]

    def is_enabled(self, name):
        self.get(name)
        return name in self._enabled

    def enable(self, name):
        self.get(name)
        self._enabled.add(name)

    def disable(self, name):
        self.get(name)
        self._enabled.discard(name)

    def list_tools(self):
        """Catalogue entries, name-sorted: tool info plus its enabled flag."""
        return [
            {**tool.info(), "enabled": name in self._enabled}
            for name, tool in sorted(self._tools.items())
        ]

    def __len__(self):
        return len(self._tools)
