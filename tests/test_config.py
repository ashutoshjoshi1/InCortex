"""Phase 10 tests — configuration (Design_Doc §24, TOML adaptation).

CortexConfig carries every tunable the design doc's config example names;
load_config reads TOML strictly (unknown keys are errors, bad values fail
fast); build_cortex assembles a brain whose behavior provably matches the
file — the ceiling, the database path, the learning log.
"""

import pytest

from incortex.core import CortexConfig, build_cortex, load_config


def write_toml(tmp_path, text):
    path = tmp_path / "incortex.toml"
    path.write_text(text)
    return path


class TestCortexConfig:
    def test_defaults_are_complete_and_sane(self):
        config = CortexConfig()
        assert config.memory.db_path == ":memory:"
        assert config.memory.half_life_days == 7.0
        assert config.memory.short_term_capacity == 100
        assert config.learning.log_path is None
        assert config.safety.max_auto_level == 2
        assert config.tools.enabled is False
        assert config.api.host == "127.0.0.1"
        assert config.api.port == 8000

    def test_sections_are_immutable(self):
        config = CortexConfig()
        with pytest.raises(Exception):
            config.safety.max_auto_level = 5

    def test_validation_rejects_bad_values(self):
        from incortex.core.config import (
            ApiConfig,
            LearningConfig,
            MemoryConfig,
            SafetyConfig,
            ToolsConfig,
        )
        with pytest.raises(ValueError):
            MemoryConfig(db_path="   ")
        with pytest.raises(ValueError):
            MemoryConfig(half_life_days=0)
        with pytest.raises(ValueError):
            MemoryConfig(short_term_capacity=0)
        with pytest.raises(ValueError):
            LearningConfig(log_path="   ")
        with pytest.raises(ValueError):
            SafetyConfig(max_auto_level=7)
        with pytest.raises(ValueError):
            ToolsConfig(enabled="yes")
        with pytest.raises(ValueError):
            ToolsConfig(enabled=True, sandbox_dir="  ")
        with pytest.raises(ValueError):
            ApiConfig(host="  ")
        with pytest.raises(ValueError):
            ApiConfig(port=0)

    def test_from_dict_guards_shapes(self):
        with pytest.raises(ValueError):
            CortexConfig.from_dict("not a dict")
        with pytest.raises(ValueError):
            CortexConfig.from_dict({"memory": "not a table"})

    def test_to_dict_roundtrip(self):
        config = CortexConfig.from_dict({"api": {"port": 9001}})
        data = config.to_dict()
        assert data["api"]["port"] == 9001
        assert CortexConfig.from_dict(data) == config


class TestLoadConfig:
    def test_missing_file_is_a_loud_error(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "nope.toml")

    def test_empty_file_gives_defaults(self, tmp_path):
        config = load_config(write_toml(tmp_path, ""))
        assert config == CortexConfig()

    def test_values_override_defaults(self, tmp_path):
        config = load_config(write_toml(tmp_path, """
[memory]
db_path = "data/brain.db"
half_life_days = 14.0

[safety]
max_auto_level = 3

[tools]
enabled = true
sandbox_dir = "data/box"

[api]
port = 9001
"""))
        assert config.memory.db_path == "data/brain.db"
        assert config.memory.half_life_days == 14.0
        assert config.memory.short_term_capacity == 100  # untouched default
        assert config.safety.max_auto_level == 3
        assert config.tools.enabled is True
        assert config.api.port == 9001

    def test_unknown_sections_and_keys_fail_fast(self, tmp_path):
        with pytest.raises(ValueError, match="unknown"):
            load_config(write_toml(tmp_path, "[telepathy]\nenabled = true\n"))
        with pytest.raises(ValueError, match="unknown"):
            load_config(write_toml(tmp_path, "[memory]\ndb_pathh = 'x'\n"))

    def test_bad_values_fail_fast(self, tmp_path):
        with pytest.raises(ValueError):
            load_config(write_toml(tmp_path, "[safety]\nmax_auto_level = 9\n"))


class TestBuildCortex:
    def test_default_build_works_end_to_end(self):
        core = build_cortex(CortexConfig())
        context = core.handle("Teach yourself what gravity is.")
        assert context.accepted is True
        assert core.tools is None  # tools disabled by default

    def test_database_path_is_honored(self, tmp_path):
        db_path = str(tmp_path / "brain.db")
        config = CortexConfig.from_dict({"memory": {"db_path": db_path}})
        first = build_cortex(config)
        first.handle("Teach yourself what gravity is.")
        first.memory.manager.close()
        second = build_cortex(config)
        results = second.memory.manager.recall("gravity")
        assert len(results) == 1

    def test_learning_log_path_is_honored(self, tmp_path):
        log_path = tmp_path / "log.jsonl"
        config = CortexConfig.from_dict(
            {"learning": {"log_path": str(log_path)}})
        core = build_cortex(config)
        core.handle("hello there")
        core.feedback(success=True)
        assert log_path.exists()

    def test_safety_ceiling_is_honored(self, tmp_path):
        config = CortexConfig.from_dict({
            "safety": {"max_auto_level": 3},
            "tools": {"enabled": True,
                      "sandbox_dir": str(tmp_path / "box")},
        })
        core = build_cortex(config)
        # search_memory is level 1 and executes; the ceiling test:
        gate = core.tools.safety.check("some_action", permission_level=3,
                                       harm_probability=0.0, impact=0.0)
        assert gate.content["decision"] == "execute"

    def test_tools_enabled_builds_the_muscle_system(self, tmp_path):
        config = CortexConfig.from_dict({
            "tools": {"enabled": True, "sandbox_dir": str(tmp_path / "box")}})
        core = build_cortex(config)
        names = {entry["name"] for entry in core.tools.registry.list_tools()}
        assert {"read_file", "write_file", "search_memory",
                "run_python"} <= names
        # Fail-closed: no approver was configured, so level 4 is denied
        out = core.tools.invoke("run_python", {"code": "print(1)"})
        assert out.content["decision"] == "denied"
