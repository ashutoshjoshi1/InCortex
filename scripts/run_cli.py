"""InCortex CLI (Phase 5 — a brain that remembers between runs).

Memory now persists: facts go to SQLite, the learning history to JSONL.
Teach it something, quit, run it again — it still knows. Pass a database
path to keep separate brains, or ':memory:' for an ephemeral one.

Run:  python scripts/run_cli.py [db_path]     (default: data/incortex.db)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from incortex.core import CortexCore
from incortex.learning import LearningLog
from incortex.memory import IN_MEMORY, MemoryManager
from incortex.organs import LearningOrgan, MemoryOrgan

DEFAULT_DB_PATH = "data/incortex.db"
PROMPT = "you> "
COMMANDS = ("Commands: 'health' shows brain health, 'log' shows brain activity, "
            "'good'/'bad' gives feedback, 'quit' exits.")
LOG_PAYLOAD_WIDTH = 60


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
    """A persistent brain: SQLite memories + JSONL learning history."""
    memory = MemoryOrgan(manager=MemoryManager(db_path=db_path))
    if db_path != IN_MEMORY:
        log_path = Path(db_path).with_name("learning_log.jsonl")
        learning = LearningOrgan(log=LearningLog(log_path))
    else:
        learning = LearningOrgan()
    return CortexCore(memory=memory, learning=learning)


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB_PATH
    core = build_core(db_path)
    stats = core.memory.manager.stats()
    print("InCortex v0.1 - Cell Genesis (Phase 5: Memory and Learning)")
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
