"""Fixture-Bäume für die Mutationstests.

Der Fixture-Baum ist eine **Kopie dieses Repositories**, keine
handgeschriebene Attrappe. Das ist der entscheidende Punkt: Ein selbstgebautes
Mini-Repo enthält die Anker per Konstruktion — man schreibt ja hinein, was die
Prüfung sucht. Eine Testsuite auf so einem Baum prüft am Ende nur sich selbst
und bliebe grün, während im echten Baum der Anker längst weg ist. Genau der
Fehler, gegen den die Prüfungen gerichtet sind, eine Ebene höher.

Deshalb: Der Baum kommt aus `git ls-files`, jede Mutation ist ein Delta
darauf, und `test_check_passes_on_the_pristine_fixture` belegt, dass die
Kopie den echten Baum nicht verloren hat.
"""

from __future__ import annotations

import json
import shutil
import string
import subprocess
from pathlib import Path

import pytest

from tools.checks.catalogue import (
    ADOPTION_CLAIM,
    CHECK_ID,
    CHECKS_DIR_ENV,
    COMMIT_ENV,
    GERMAN_NUMBERS,
    LINKED,
    MANIFEST_ENV,
    STATE,
    table_section,
)
from tools.checks.readmes import top_release
from tools.checks.release import TAG_ENV
from tools.checks.repo_metadata import METADATA_ENV
from tools.checks.skill_doc import ENGLISH_NUMBERS, read_skill, rule_count

REPO_ROOT = Path(__file__).resolve().parents[1]


def synthetic_manifest(skill: str) -> list[str]:
    """Ein Katalog, der zu dem passt, was SKILL.md über ihn behauptet.

    **Was das beweist und was nicht.** Es beweist, dass Prüfung 14 einen
    stimmigen Katalog akzeptiert — und liefert damit den grünen Ausgangspunkt,
    von dem die Mutationen wegführen. Es beweist NICHT, dass SKILL.md zum
    echten Katalog passt; genau das ist der Job, den der Wochenplan gegen die
    live abgerufene MANIFEST.txt erledigt, und er lässt sich hier nicht
    nachbauen, ohne ins Netz zu greifen.

    Ein eingefrorener Schnappschuss der echten MANIFEST.txt wäre die
    Alternative gewesen. Dagegen spricht, dass er beim nächsten Katalog-Release
    veraltet und die Suite dann aus einem Grund rot wird, der mit dem Commit
    nichts zu tun hat — der Fehlalarm aus Regel 5, und zwar in der Testsuite
    statt in der CI.
    """
    section = table_section(skill)
    state = STATE.search(section)
    if state is None:  # pragma: no cover — Prüfung 14 fängt das zuerst
        raise AssertionError("SKILL.md nennt keinen Katalogstand mehr")
    total = int(state.group("total"))
    want_cats = GERMAN_NUMBERS[state.group("cats")]
    want_fid = GERMAN_NUMBERS[state.group("fid")]

    ids = sorted(set(LINKED.findall(section)))
    linked_cats = sorted({i.split("-")[0] for i in ids})

    # Zusätzliche Kategorien aus einem Vorrat, der mit keiner echten kollidiert.
    pool = [f"Z{letter}" for letter in string.ascii_uppercase]
    extra = [c for c in pool if c not in linked_cats][: want_cats - len(linked_cats)]
    categories = linked_cats + extra

    # Auffüllen bis zur behaupteten Grösse — nie mit FID, sonst entstünde ein
    # Check, den die Tabelle nicht verlinkt, und der gute Fall wäre keiner.
    fillable = [c for c in categories if c != "FID"]
    counter = dict.fromkeys(fillable, 900)
    while len(ids) < total:
        for category in fillable:
            if len(ids) >= total:
                break
            counter[category] -= 1
            ids.append(f"{category}-{counter[category]:03d}")
    ids = sorted(set(ids))

    got_cats = {i.split("-")[0] for i in ids}
    got_fid = {i for i in ids if i.startswith("FID-")}
    assert len(ids) == total, f"{len(ids)} statt {total} — Generator defekt"
    assert len(got_cats) == want_cats, f"{sorted(got_cats)} statt {want_cats}"
    assert len(got_fid) == want_fid, f"{sorted(got_fid)} statt {want_fid}"
    return ids


def synthetic_checks(skill: str, into: Path) -> int:
    """Check-Dateien, deren Einstufung zu dem passt, was SKILL.md behauptet.

    Dieselbe Grenze wie bei `synthetic_manifest`: Das beweist, dass Prüfung 14
    eine stimmige Einstufung durchlässt — **nicht**, dass die echte stimmt.
    Genau dafür läuft der Wochenplan gegen den live abgerufenen Baum.

    Die beiden Zweige bilden die Vorgabe drüben ab, und der zweite ist der
    interessante: Ein `enforced` Check trägt **kein** `adoption`-Feld. Wäre er
    hier mit `adoption: enforced` geschrieben, bliebe genau der Fall
    ungetestet, an dem die Behauptung in SKILL.md zerbrochen ist — vier Checks
    ohne Feld, die deshalb übersehen wurden.
    """
    section = table_section(skill)
    claim = ADOPTION_CLAIM.search(section)
    if claim is None:  # pragma: no cover — Prüfung 14 fängt das zuerst
        raise AssertionError("SKILL.md nennt keine Einstufung mehr")
    advisory = set(CHECK_ID.findall(claim.group("advisory")))

    into.mkdir(parents=True, exist_ok=True)
    linked = sorted(set(LINKED.findall(section)))
    for check_id in linked:
        field = "adoption: advisory\n" if check_id in advisory else ""
        (into / f"{check_id}.md").write_text(
            f"---\nid: {check_id}\nseverity: high\n{field}---\n\n# {check_id}\n",
            encoding="utf-8",
        )
    return len(linked)


def synthetic_metadata(skill: str) -> str:
    """Eine Repo-Description, die zu dem passt, was SKILL.md behauptet.

    Dieselbe Grenze wie bei `synthetic_manifest`, und sie ist hier noch
    schärfer: Es beweist, dass Prüfung 15 eine stimmige Description
    durchlässt — **nicht**, dass die echte stimmt. Die echte liegt in den
    GitHub-Metadaten und lässt sich von hier aus prinzipiell nicht lesen, ohne
    ins Netz zu greifen; genau dafür gibt es den Wochenplan.

    Ein eingefrorener Schnappschuss der echten Description wäre die Alternative
    gewesen. Dagegen spricht dasselbe wie drüben: Er veraltete beim nächsten
    Umformulieren, und die Suite würde aus einem Grund rot, der mit dem Commit
    nichts zu tun hat.
    """
    words = {value: key for key, value in ENGLISH_NUMBERS.items()}
    count = rule_count(skill)
    if count not in words:  # pragma: no cover — Prüfung 5 fängt das zuerst
        raise AssertionError(
            f"SKILL.md definiert {count} Regeln, und ENGLISH_NUMBERS kennt kein "
            "Zahlwort dafür — tools/checks/skill_doc.py ergänzen"
        )
    return json.dumps(
        {
            "description": (
                f"Claude Skill with {words[count]} data-fidelity rules for MCP "
                "tools that query an external data source"
            )
        }
    )


def _working_tree_files(root: Path) -> list[str]:
    """Alles, was ein Commit von hier aus mitnähme.

    `--others --exclude-standard` neben `--cached`: Auch noch nicht
    hinzugefügte Dateien gehören dazu, sonst prüfte die Suite während der
    Arbeit an einer neuen Datei einen Baum ohne sie.
    """
    done = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in done.stdout.splitlines() if line]


@pytest.fixture(scope="session")
def pristine_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Eine Kopie des Arbeitsbaums, einmal pro Sitzung gebaut."""
    root = tmp_path_factory.mktemp("pristine") / "repo"
    root.mkdir()
    for name in _working_tree_files(REPO_ROOT):
        source = REPO_ROOT / name
        if not source.is_file():
            continue
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    # Prüfung 3 liest den Git-Index. Ohne Repository hätte sie nichts zu lesen
    # und würde in jedem Test aus dem falschen Grund rot.
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)

    # Prüfung 14 liest das abgelegte Manifest.
    (root / "manifest.txt").write_text(
        "\n".join(synthetic_manifest(read_skill(root))) + "\n", encoding="utf-8"
    )
    # ... und die Check-Dateien, aus denen sie die Einstufung liest.
    synthetic_checks(read_skill(root), root / "catalogue-checks")
    # Prüfung 15 die abgelegte Antwort der Repo-API.
    (root / "repo-metadata.json").write_text(
        synthetic_metadata(read_skill(root)) + "\n", encoding="utf-8"
    )
    return root


@pytest.fixture
def fixture_repo(
    pristine_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """Ein frischer Baum pro Test — Mutationen dürfen ihn ruinieren."""
    root = tmp_path / "repo"
    shutil.copytree(pristine_repo, root)
    monkeypatch.setenv(MANIFEST_ENV, str(root / "manifest.txt"))
    monkeypatch.setenv(CHECKS_DIR_ENV, str(root / "catalogue-checks"))
    # Der Commit, an dem der Katalog hing. Im Fixture-Baum gibt es keinen
    # echten — ein Platzhalter genügt, weil die Prüfung ihn nur mitführt.
    monkeypatch.setenv(COMMIT_ENV, "0" * 40)
    monkeypatch.setenv(METADATA_ENV, str(root / "repo-metadata.json"))
    # Prüfung 13 braucht einen Tag-Kontext. Der gute Fall ist der Tag, den ein
    # Release dieses Standes tragen müsste.
    monkeypatch.setenv(TAG_ENV, f"v{top_release(root)[2]}")
    return root
