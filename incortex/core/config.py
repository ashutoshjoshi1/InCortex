"""Configuration — the brain's tunables in one typed place (Design_Doc §24).

Files are TOML rather than the design doc's YAML sketch: Python 3.11
ships a TOML parser in the standard library (tomllib), so the zero-
dependency rule holds; the structure maps 1:1. Loading is strict —
unknown sections or keys are errors, and every value is validated at
construction (fail fast at the boundary).
"""

import tomllib
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from incortex.memory.memory_manager import DEFAULT_HALF_LIFE_SECONDS

SECONDS_PER_DAY = 24 * 3600.0


@dataclass(frozen=True)
class MemoryConfig:
    db_path: str = ":memory:"
    half_life_days: float = DEFAULT_HALF_LIFE_SECONDS / SECONDS_PER_DAY
    short_term_capacity: int = 100

    def __post_init__(self):
        if not isinstance(self.db_path, str) or not self.db_path.strip():
            raise ValueError("memory.db_path must be a non-empty string")
        if not isinstance(self.half_life_days, (int, float)) or self.half_life_days <= 0:
            raise ValueError("memory.half_life_days must be positive")
        if not isinstance(self.short_term_capacity, int) or self.short_term_capacity < 1:
            raise ValueError("memory.short_term_capacity must be a positive integer")


@dataclass(frozen=True)
class LearningConfig:
    log_path: str | None = None

    def __post_init__(self):
        if self.log_path is not None and (
                not isinstance(self.log_path, str) or not self.log_path.strip()):
            raise ValueError("learning.log_path must be a non-empty string or absent")


@dataclass(frozen=True)
class SafetyConfig:
    max_auto_level: int = 2

    def __post_init__(self):
        if (isinstance(self.max_auto_level, bool)
                or not isinstance(self.max_auto_level, int)
                or not 0 <= self.max_auto_level <= 5):
            raise ValueError("safety.max_auto_level must be an integer 0-5")


@dataclass(frozen=True)
class ToolsConfig:
    enabled: bool = False
    sandbox_dir: str = "data/sandbox"

    def __post_init__(self):
        if not isinstance(self.enabled, bool):
            raise ValueError("tools.enabled must be a bool")
        if not isinstance(self.sandbox_dir, str) or not self.sandbox_dir.strip():
            raise ValueError("tools.sandbox_dir must be a non-empty string")


@dataclass(frozen=True)
class ApiConfig:
    host: str = "127.0.0.1"
    port: int = 8000

    def __post_init__(self):
        if not isinstance(self.host, str) or not self.host.strip():
            raise ValueError("api.host must be a non-empty string")
        if (isinstance(self.port, bool) or not isinstance(self.port, int)
                or not 1 <= self.port <= 65535):
            raise ValueError("api.port must be an integer 1-65535")


_SECTIONS = {
    "memory": MemoryConfig,
    "learning": LearningConfig,
    "safety": SafetyConfig,
    "tools": ToolsConfig,
    "api": ApiConfig,
}


@dataclass(frozen=True)
class CortexConfig:
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    learning: LearningConfig = field(default_factory=LearningConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    tools: ToolsConfig = field(default_factory=ToolsConfig)
    api: ApiConfig = field(default_factory=ApiConfig)

    @classmethod
    def from_dict(cls, data):
        """Build a config from nested dicts, strictly: unknown names error."""
        if not isinstance(data, dict):
            raise ValueError("config data must be a dict")
        unknown_sections = set(data) - set(_SECTIONS)
        if unknown_sections:
            raise ValueError(f"unknown config sections: {sorted(unknown_sections)}")
        sections = {}
        for name, section_type in _SECTIONS.items():
            values = data.get(name, {})
            if not isinstance(values, dict):
                raise ValueError(f"config section '{name}' must be a table")
            known = {f.name for f in fields(section_type)}
            unknown_keys = set(values) - known
            if unknown_keys:
                raise ValueError(
                    f"unknown keys in [{name}]: {sorted(unknown_keys)}")
            sections[name] = section_type(**values)
        return cls(**sections)

    def to_dict(self):
        return asdict(self)


def load_config(path):
    """Read a TOML config file strictly; missing files are loud errors."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"no config file at {path}")
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    return CortexConfig.from_dict(data)


def build_cortex(config, approver=None):
    """Assemble a CortexCore whose behavior matches the config.

    No approver means fail-closed: level-4 tools are denied (DenyAll).
    """
    # Imports here to avoid a cycle: organs import core pieces at module load.
    from incortex.core.cortex import CortexCore
    from incortex.learning import LearningLog
    from incortex.memory import MemoryManager
    from incortex.organs import LearningOrgan, MemoryOrgan, SafetyOrgan, ToolOrgan
    from incortex.tools import (
        ReadFileTool,
        RunPythonTool,
        SearchMemoryTool,
        ToolRegistry,
        WriteFileTool,
    )

    manager = MemoryManager(
        db_path=config.memory.db_path,
        half_life_seconds=config.memory.half_life_days * SECONDS_PER_DAY,
        short_term_capacity=config.memory.short_term_capacity,
    )
    memory = MemoryOrgan(manager=manager)
    learning = (LearningOrgan(log=LearningLog(config.learning.log_path))
                if config.learning.log_path else LearningOrgan())
    safety = SafetyOrgan(max_auto_level=config.safety.max_auto_level)
    tools = None
    if config.tools.enabled:
        registry = ToolRegistry()
        registry.register(ReadFileTool(config.tools.sandbox_dir))
        registry.register(WriteFileTool(config.tools.sandbox_dir))
        registry.register(SearchMemoryTool(manager))
        registry.register(RunPythonTool())
        tools = ToolOrgan(
            registry=registry,
            safety=SafetyOrgan(name="tool_organ_gate",
                               max_auto_level=config.safety.max_auto_level),
            approver=approver,
        )
    return CortexCore(memory=memory, learning=learning, safety=safety,
                      tools=tools)
