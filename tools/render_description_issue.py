#!/usr/bin/env python3
"""Turn a `check_repo_description.py` result into an issue body and a state word.

The description guard already worked. What was missing was an addressee: it ran
on `main`, went red across six consecutive merges, and nobody saw it, because a
red push run appears in no pull request. This script renders the escalation that
gives the finding somewhere to land.

**Why three states and not two.** The obvious shape is «body written -> open an
issue, no body -> close it». That shape is wrong, and measurement is what showed
it: `result.json` can be missing, empty, unparseable, or hold `description:
null` when the fetch failed. All four produce no body — and would have been read
as «description is fine», closing an open issue on the strength of a comparison
that never happened. A check that did not run is not a pass (SKILL.md §2.6), so
`unchecked` is its own outcome and touches nothing.

**Why the body asks the human to re-run the workflow.** The guard closes its
own issue as soon as a run finds the description correct — but nothing makes
that run happen. Editing repo metadata produces no push, and the workflow's
`push` trigger only watches `checks/**` and two files. Observed: the description
was corrected, the issue stayed open, and the next event that would have closed
it was the Monday cron. The guard does not notice a repair; it notices the next
occasion. So the body names the one action that turns a repair into an event —
Actions tab, `repo-description`, «Run workflow» — and says what happens without
it. The trigger already exists (`workflow_dispatch`); what was missing was
anyone telling the reader to press it.

State word on stdout, for the workflow to branch on:
  drift     — description and catalogue disagree; body written, open or update
  ok        — they agree; close any open issue
  unchecked — no comparison happened; leave everything alone
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Bootstrap so tools.* imports work when invoked as a script.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.path_utils import force_utf8_stdio  # noqa: E402

DRIFT = "drift"
OK = "ok"
UNCHECKED = "unchecked"


def load_result(path: Path) -> dict | None:
    """The guard's JSON result, or None if there is nothing usable to read.

    Every unreadable shape collapses to None on purpose: a missing file and a
    corrupt one mean the same thing here — no comparison was made.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    if not text.strip():
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def classify(result: dict | None) -> str:
    """Which of the three outcomes this result represents."""
    if result is None:
        return UNCHECKED
    if result.get("description") is None:
        # The guard reports the description it compared against. Without one it
        # did not compare, whatever `ok` happens to say.
        return UNCHECKED
    return OK if result.get("ok") else DRIFT


def render_body(result: dict) -> str:
    """The issue body for a drift result."""
    lines = [
        "Die Repo-Description nennt andere Zahlen als der Katalog.",
        "",
    ]
    for problem in result.get("problems", []):
        lines.append(f"- {problem}")
    lines += [
        "",
        "**Fertiger Text** — Formulierung unverändert, nur die Zahlen:",
        "",
        "```",
        str(result.get("suggestion", "")),
        "```",
        "",
        "Eintragen auf der Repo-Startseite, rechte Spalte **About**, "
        "Zahnrad-Symbol. *Nicht* in den Settings — dort steht die Description "
        "nicht.",
        "",
        "**Danach den Workflow von Hand anstossen:** Tab **Actions**, links "
        "den Workflow `repo-description` wählen, dann **Run workflow**. Eine "
        "geänderte Description erzeugt keinen Push und damit kein Ereignis — "
        "der Guard merkt die Reparatur nicht, er merkt erst den nächsten "
        "Anlass. Ohne diesen Anstoss bleibt das Issue hier bis zum "
        "wöchentlichen Lauf am Montag offen, obwohl die Sache erledigt ist.",
        "",
        "Der Guard schreibt bewusst nicht: Repo-Metadaten zu ändern gehört "
        "einem Menschen. Dieses Issue schliesst sich selbst, sobald der "
        "nächste Lauf die Description korrekt findet.",
        "",
        "---",
        "_Automatisch erzeugt vom `repo-description`-Workflow._",
    ]
    return "\n".join(lines) + "\n"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="render_description_issue",
        description="Render the description-drift issue body; print the state word.",
    )
    parser.add_argument(
        "--result",
        default="result.json",
        help="JSON output of check_repo_description.py (default: result.json)",
    )
    parser.add_argument(
        "--out",
        default="issue-body.md",
        help="Where to write the issue body (default: issue-body.md)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdio()
    args = _build_parser().parse_args(argv)

    result = load_result(Path(args.result))
    state = classify(result)

    out = Path(args.out)
    # Always write, so a stale body from an earlier step can never be picked up
    # as if it described this run.
    out.write_text(render_body(result) if state == DRIFT else "", encoding="utf-8")

    print(state)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
