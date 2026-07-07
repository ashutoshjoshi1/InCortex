"""InCortex CLI (Phase 7 — a brain with muscles).

Tools are live behind the safety gate: 'tools' lists the registry,
'tool <name> key=value ...' invokes one. Level-4 tools (run_python) ask
YOU for approval at the terminal before executing — the human in the loop.
Memory persists (SQLite); the learning history persists (JSONL).

Run:  python scripts/run_cli.py [db_path]     (default: data/incortex.db)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from incortex.core import CortexCore
from incortex.learning import LearningLog
from incortex.memory import IN_MEMORY, MemoryManager
from incortex.organs import LearningOrgan, MemoryOrgan, ToolOrgan
from incortex.safety import CallbackApprover
from incortex.tools import (
    ApiTool,
    ReadFileTool,
    RunPythonTool,
    SearchMemoryTool,
    ToolRegistry,
    WriteFileTool,
)

DEFAULT_DB_PATH = "data/incortex.db"
SANDBOX_DIR = "data/sandbox"
PROMPT = "you> "
COMMANDS = ("Commands: 'health', 'log', 'tools', 'tool <name> key=value ...', "
            "'good'/'bad' gives feedback, 'quit' exits.")
LOG_PAYLOAD_WIDTH = 60


def terminal_approver(action, reason):
    """The human in the loop: a real y/n question at the terminal."""
    answer = input(f"[approval] Allow '{action}'? ({reason}) [y/N] ")
    return answer.strip().lower() in ("y", "yes")


def build_tools(memory_manager):
    """The Phase 7 muscle system: sandboxed files, memory search, gated code."""
    registry = ToolRegistry()
    registry.register(ReadFileTool(SANDBOX_DIR))
    registry.register(WriteFileTool(SANDBOX_DIR))
    registry.register(SearchMemoryTool(memory_manager))
    registry.register(RunPythonTool())
    registry.register(ApiTool())
    return ToolOrgan(registry=registry,
                     approver=CallbackApprover(terminal_approver))


def parse_tool_command(text):
    """'tool run_python code=print(1)' -> ('run_python', {'code': 'print(1)'})."""
    parts = text.split(None, 2)
    if len(parts) < 2:
        raise ValueError("usage: tool <name> [key=value ...]")
    name = parts[1]
    request = {}
    if len(parts) == 3:
        for pair in parts[2].split("&"):
            if "=" not in pair:
                raise ValueError(f"bad argument '{pair}' - use key=value")
            key, value = pair.split("=", 1)
            request[key.strip()] = value
    return name, request


def run_tool_command(core, text):
    try:
        name, request = parse_tool_command(text)
        out = core.tools.invoke(name, request)
    except ValueError as error:
        return f"(tool error: {error})"
    content = out.content
    if content["executed"] and content["success"]:
        return f"[{content['decision']}] {content['output']}"
    return f"[{content['decision']}] {content['error']}"


def print_health(core):
    report = core.health_check()
    for organ in report["organs"]:
        print(f"  {organ['name']:<17} status={organ['status']:<9} "
              f"health={organ['health']:.2f}")
        for component in organ["components"]:
            print(f"    {component['name']:<17} status={component['status']:<9} "
                  f"health={component['health']:.2f}")
            for cell in component.get("cells", []):
                print(f"      - {cell['name']:<15} status={cell['status']:<9} "
                      f"health={cell['health']:.2f} confidence={cell['confidence']:.2f} "
                      f"processed={cell['processed']} feedback={cell['feedback_count']}")
    system = report["system"]
    acceptance = system["acceptance_rate"]
    confidence = system["confidence_ema"]
    learning = system["learning_ema"]
    print(f"  system: tasks={system['tasks_handled']} "
          f"acceptance={acceptance:.2f}" if acceptance is not None
          else "  system: no tasks yet", end="")
    if confidence is not None:
        print(f" confidence_ema={confidence:.2f}", end="")
    if learning is not None:
        print(f" learning_ema={learning:.2f}", end="")
    print()


def print_log(core, count=12):
    for message in core.bus.history(count):
        payload = str(message.payload).replace("\n", " ")
        if len(payload) > LOG_PAYLOAD_WIDTH:
            payload = payload[:LOG_PAYLOAD_WIDTH] + "..."
        confidence = (f" c={message.confidence:.2f}"
                      if message.confidence is not None else "")
        print(f"  {message.message_type:<17} {message.source} -> "
              f"{message.target}{confidence}  {payload}")


def build_core(db_path):
    """A persistent brain: SQLite memories + JSONL learning history + muscles."""
    memory = MemoryOrgan(manager=MemoryManager(db_path=db_path))
    if db_path != IN_MEMORY:
        log_path = Path(db_path).with_name("learning_log.jsonl")
        learning = LearningOrgan(log=LearningLog(log_path))
    else:
        learning = LearningOrgan()
    return CortexCore(memory=memory, learning=learning,
                      tools=build_tools(memory.manager))


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB_PATH
    core = build_core(db_path)
    stats = core.memory.manager.stats()
    print("InCortex v0.1 - Cell Genesis (Phase 7: Tools and Muscles)")
    print(f"Memory: {db_path} ({stats['active']} memories, "
          f"{stats['archived']} archived, {len(core.learning.log)} learning events)")
    print(COMMANDS)
    while True:
        try:
            text = input(PROMPT).strip()
        except EOFError:
            print("Goodbye.")
            return
        if not text:
            continue
        if text.lower() in ("quit", "exit"):
            print("Goodbye.")
            return
        if text.lower() == "health":
            print_health(core)
            continue
        if text.lower() == "log":
            print_log(core)
            continue
        if text.lower() == "tools":
            for entry in core.tools.registry.list_tools():
                flag = "on " if entry["enabled"] else "off"
                print(f"  [{flag}] {entry['name']:<15} L{entry['permission_level']}  "
                      f"{entry['description']}")
            continue
        if text.lower().startswith("tool "):
            print(run_tool_command(core, text))
            continue
        if text.lower() in ("good", "bad"):
            try:
                result = core.feedback(success=text.lower() == "good")
            except ValueError as error:
                print(f"({error})")
                continue
            content = result.content
            print(f"Feedback stored. Learning score {content['learning_score']:.2f} "
                  f"({content['band']} band), running average "
                  f"{content['running_score']:.2f}.")
            continue
        context = core.handle(text)
        print(f"incortex> {context.reply}  "
              f"[chain confidence {context.chain_confidence:.2f}]")


if __name__ == "__main__":
    main()
