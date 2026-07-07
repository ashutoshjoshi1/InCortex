"""Development Organ demo — InCortex working on a miniature codebase.

Builds a tiny throwaway project, then: analyzes a bug report, reads the
code, runs the tests (approval is asked at your terminal — the human in
the loop is YOU), suggests a patch as a unified diff, and drafts a pull
request it cannot merge.

Run:  python examples/dev_demo.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from incortex.organs import DevelopmentOrgan, LearningOrgan
from incortex.safety import CallbackApprover


def terminal_approver(action, reason):
    answer = input(f"[approval] Allow '{action}'? ({reason}) [y/N] ")
    return answer.strip().lower() in ("y", "yes")


def main():
    workdir = Path(tempfile.mkdtemp(prefix="incortex_dev_demo_"))
    (workdir / "pkg").mkdir()
    (workdir / "pkg" / "math_utils.py").write_text(
        "def add(a, b):\n    return a + b\n")
    (workdir / "test_math.py").write_text(
        "from pkg.math_utils import add\n\n"
        "def test_add():\n    assert add(1, 2) == 3\n")

    organ = DevelopmentOrgan(project_root=workdir,
                             approver=CallbackApprover(terminal_approver),
                             learning=LearningOrgan())

    print("== 1. Analyze the issue ==")
    issue = organ.analyze_issue("Bug: add() crashes on float strings",
                                "pkg/math_utils.py should coerce its inputs")
    for key, value in issue.content.items():
        print(f"  {key}: {value}")

    print("\n== 2. Read the code (level 1: no ceremony) ==")
    read = organ.read_file("pkg/math_utils.py")
    print("  " + read.content["output"]["content"].replace("\n", "\n  "))

    print("== 3. Run the tests (level 4: YOUR approval is required) ==")
    tests = organ.run_tests("test_math.py")
    print(f"  decision: {tests.content['decision']}")
    if tests.content["executed"]:
        print(f"  result: {tests.content['output']}")

    print("\n== 4. Suggest a patch (a draft - the file is never touched) ==")
    patch = organ.suggest_patch(
        "pkg/math_utils.py", find="return a + b",
        replace="return float(a) + float(b)",
        description="Coerce operands to float")
    print("  " + patch.content["patch"]["diff"].replace("\n", "\n  "))

    print("\n== 5. Draft the pull request (a human must merge it) ==")
    pr = organ.draft_pull_request("Fix float handling in add()",
                                  "Coerces both operands before adding.")
    draft = pr.content["pull_request"]
    print(f"  branch: {draft['branch_name']}  status: {draft['status']}")
    print("  " + draft["body"].replace("\n", "\n  "))
    print(f"\n  merge method on the organ? {hasattr(organ, 'merge')}")


if __name__ == "__main__":
    main()
