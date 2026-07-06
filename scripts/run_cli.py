"""InCortex CLI (Phase 2 — running on Tissues).

The conversation loop now flows through whole Tissues:
LanguageTissue understands and replies, MemoryTissue stores and retrieves,
LearningTissue scores feedback and spreads it to every participating Cell.

Run:  python scripts/run_cli.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from incortex.tissues import LanguageTissue, LearningTissue, MemoryTissue

PROMPT = "you> "
COMMANDS = "Commands: 'health' shows tissue health, 'good'/'bad' gives feedback, 'quit' exits."


def respond(language, memory, text):
    """The Phase 2 chain: input → IntentCell → MemoryCell → ResponseCell."""
    understanding = language.process(text)
    intent = understanding.content["intent"]
    cleaned = understanding.content["text"]
    results = []
    if intent in ("teach", "remember"):
        memory.store(cleaned)
    elif intent == "explain":
        results = memory.retrieve(cleaned).content["results"]
    reply = language.respond(intent, cleaned, results)
    return reply.content["reply"]


def give_feedback(learning, tissues, success):
    """Score the event and teach every cell in the participating tissues."""
    cells = [cell for tissue in tissues for cell in tissue.cells]
    result = learning.distribute({"success": success}, cells)
    content = result.content
    return (
        f"Feedback stored. Learning score {content['learning_score']:.2f} "
        f"({content['band']} band), running average {content['running_score']:.2f}."
    )


def print_health(tissues):
    for tissue in tissues:
        report = tissue.health_check()
        print(f"  {report['name']:<16} status={report['status']:<9} health={report['health']:.2f}")
        for cell in report["cells"]:
            print(f"    - {cell['name']:<15} status={cell['status']:<9} "
                  f"health={cell['health']:.2f} confidence={cell['confidence']:.2f} "
                  f"processed={cell['processed']} feedback={cell['feedback_count']}")


def main():
    language = LanguageTissue()
    memory = MemoryTissue()
    learning = LearningTissue()

    print("InCortex v0.1 - Cell Genesis (Phase 2: Tissues)")
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
            print_health([language, memory, learning])
            continue
        if text.lower() in ("good", "bad"):
            print(give_feedback(learning, [language, memory], text.lower() == "good"))
            continue
        print(f"incortex> {respond(language, memory, text)}")


if __name__ == "__main__":
    main()
