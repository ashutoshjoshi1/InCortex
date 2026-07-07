"""InCortex CLI (Phase 3 — running on Organs).

The conversation now flows through whole Organs, and every reply shows its
pipeline confidence (Eq 3.1) — watch it degrade when memory is weak:
LanguageOrgan understands and replies, MemoryOrgan stores and retrieves,
ReasoningOrgan thinks over the evidence, LearningOrgan spreads feedback.

Run:  python scripts/run_cli.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from incortex.cells.cell_math import pipeline_confidence
from incortex.organs import LanguageOrgan, LearningOrgan, MemoryOrgan, ReasoningOrgan

PROMPT = "you> "
COMMANDS = "Commands: 'health' shows organ health, 'good'/'bad' gives feedback, 'quit' exits."


def respond(language, memory, reasoning, text):
    """Phase 3 chain: Language → Memory → Reasoning → Language, with Eq 3.1."""
    understanding = language.understand(text)
    intent = understanding.content["intent"]
    cleaned = understanding.content["text"]
    stages = [understanding.confidence]
    results = []
    if intent in ("teach", "remember"):
        stages.append(memory.store(cleaned).confidence)
    elif intent == "explain":
        retrieved = memory.retrieve(cleaned)
        results = retrieved.content["results"]
        stages.append(retrieved.confidence)
        stages.append(reasoning.reason(cleaned, results).confidence)
    reply = language.respond(intent, cleaned, results)
    stages.append(reply.confidence)
    return reply.content["reply"], pipeline_confidence(stages)


def give_feedback(learning, organs, success):
    """Score the event and teach every cell in the participating organs."""
    cells = [cell for organ in organs for cell in organ.cells]
    content = learning.distribute({"success": success}, cells).content
    return (
        f"Feedback stored. Learning score {content['learning_score']:.2f} "
        f"({content['band']} band), running average {content['running_score']:.2f}."
    )


def print_health(organs):
    for organ in organs:
        report = organ.health_check()
        print(f"  {report['name']:<17} status={report['status']:<9} health={report['health']:.2f}")
        for component in report["components"]:
            print(f"    {component['name']:<17} status={component['status']:<9} "
                  f"health={component['health']:.2f}")
            for cell in component.get("cells", []):
                print(f"      - {cell['name']:<15} status={cell['status']:<9} "
                      f"health={cell['health']:.2f} confidence={cell['confidence']:.2f} "
                      f"processed={cell['processed']} feedback={cell['feedback_count']}")


def main():
    language = LanguageOrgan()
    memory = MemoryOrgan()
    reasoning = ReasoningOrgan()
    learning = LearningOrgan()

    print("InCortex v0.1 - Cell Genesis (Phase 3: Organs)")
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
            print_health([language, memory, reasoning, learning])
            continue
        if text.lower() in ("good", "bad"):
            print(give_feedback(learning, [language, memory, reasoning],
                                text.lower() == "good"))
            continue
        reply, chain = respond(language, memory, reasoning, text)
        print(f"incortex> {reply}  [chain confidence {chain:.2f}]")


if __name__ == "__main__":
    main()
