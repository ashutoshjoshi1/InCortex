"""InCortex CLI starter (Phase 0 success criterion, powered by Phase 1 Cells).

A minimal loop wiring IntentCell -> MemoryCell -> FeedbackCell:
teach/remember stores memories, questions retrieve them, and
'good'/'bad' feedback updates every Cell's track record.

Run:  python scripts/run_cli.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from incortex.cells import CellFeedback, FeedbackCell, IntentCell, MemoryCell

PROMPT = "you> "
COMMANDS = "Commands: 'health' shows cell health, 'good'/'bad' gives feedback, 'quit' exits."


def respond(intent_cell, memory_cell, text):
    intent = intent_cell.process(text).content["intent"]
    if intent in ("teach", "remember"):
        memory_cell.process({"action": "store", "content": text})
        if intent == "teach":
            return f"I have learned: {text}"
        return "Got it. I will remember that."
    if intent == "explain":
        results = memory_cell.process({"action": "retrieve", "query": text}).content["results"]
        if results:
            best = results[0]
            return f"From memory (score {best['score']:.2f}): {best['content']}"
        return "I don't know that yet - teach me!"
    return "Hello! Teach me something, ask me a question, or tell me what to remember."


def give_feedback(cells, feedback_cell, success):
    for cell in cells:
        cell.learn(CellFeedback(success=success))
    score = feedback_cell.process({"success": success}).content
    return f"Feedback stored. Learning score {score['learning_score']:.2f} ({score['band']} band)."


def print_health(cells):
    for cell in cells:
        report = cell.health_check()
        print(f"  {report['name']:<15} status={report['status']:<9} "
              f"health={report['health']:.2f} confidence={report['confidence']:.2f} "
              f"processed={report['processed']} feedback={report['feedback_count']}")


def main():
    intent_cell = IntentCell()
    memory_cell = MemoryCell()
    feedback_cell = FeedbackCell()
    cells = [intent_cell, memory_cell]

    print("InCortex v0.1 - Cell Genesis (Phase 1 demo)")
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
            print_health(cells + [feedback_cell])
            continue
        if text.lower() in ("good", "bad"):
            print(give_feedback(cells, feedback_cell, text.lower() == "good"))
            continue
        print(f"incortex> {respond(intent_cell, memory_cell, text)}")


if __name__ == "__main__":
    main()
