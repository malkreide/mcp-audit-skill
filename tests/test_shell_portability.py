"""Dokumentierte Befehle laufen auf den Plattformen, die das Repo behauptet.

Das ist `OPS-007`, angewandt auf das Repo, das ihn geschrieben hat.

`OPS-007` entstand aus `mcp-audit-skill#70`: Die Setup-Anleitung trug
`pip install pre-commit && pre-commit install`, und in PowerShell 5.1 —
der Fassung, die auf Windows ohne Zutun installiert ist — ist `&&` ein
Syntaxfehler. Die Testmatrix fährt `windows-latest`, aber keine Pipeline
führt eine README-Zeile aus. Behoben in `#71`, **ohne Wächter**.

Die Klasse kam zurück. `export NOTION_TOKEN="ntn_..."` stand als einziger
dokumentierter Weg im Setup beider READMEs; `export` ist kein
PowerShell-Befehl. Aufgefallen ist es, als ein Benutzer den Schritt
ausführte und `NOTION_TOKEN env var not set` bekam — also genau dann,
wenn niemand da ist, der die Ursache erkennt.

Zwei Regeln aus dem eigenen Katalog treffen hier zusammen:

- `OPS-007`: Was das Repo an Befehlen dokumentiert, muss auf den
  behaupteten Plattformen laufen.
- `IDENT-003` / SKILL.md §4.1: Ein Wert, den nichts erzwingt, driftet.
  Ein Einmal-Fix ohne Wächter ist kein Fix, sondern eine Pause.

**Die Gegenprobe gehört zu diesem Test selbst.** Eine frühere Fassung des
Scanners verlangte die Code-Fence am Spaltenanfang. Die README-Blöcke
sind in eine nummerierte Liste eingerückt, also betrat der Scanner sie
nie und meldete **1 Fund statt 4** — und eine niedrige Zahl liest sich
wie eine gute Nachricht. `test_the_scanner_finds_a_planted_violation`
hält das fest: Der Detektor wird gegen eingerückte Fences, nicht
eingerückte Fences und Inline-Code geführt, und muss jeden Fall finden.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


# Nur Dateien, deren Befehle ein *Mensch oder Agent auf der Zielplattform*
# ausführt. `checks/` steht bewusst nicht drin: Dessen Snippets sind Beispiele
# für fremde Repos, nicht Anleitungen für dieses.
def _targets() -> list[Path]:
    files = sorted(REPO_ROOT.glob("README*.md"))
    files.append(REPO_ROOT / "SKILL.md")
    files += sorted((REPO_ROOT / ".claude" / "commands").glob("*.md"))
    files += sorted((REPO_ROOT / "docs").glob("*.md"))
    return [f for f in files if f.is_file()]


# Einrückung erlaubt — das war der Fehler der ersten Fassung.
FENCE = re.compile(r"^\s*```(\w*)")
INLINE_CODE = re.compile(r"`([^`\n]+)`")

# Was in PowerShell 5.1 bricht:
#   `export VAR=…`  — kein Befehl
#   ` && `          — kein Verkettungsoperator, Syntaxfehler beim Parsen
BASHISM = re.compile(r"(^\s*export\s+\w+=)|(\s&&\s)")

# Woran man erkennt, dass die PowerShell-Fassung danebensteht.
POWERSHELL = re.compile(
    r"\$env:|\[Environment\]::|```\s*powershell|pwsh", re.IGNORECASE
)

# Wie weit von einer bash-Zeile entfernt die PowerShell-Entsprechung stehen darf.
# Vier Zeilen decken «beide Zeilen im selben Block» und «zweiter Block direkt
# darunter» ab, ohne einen zufälligen Treffer aus einem fremden Abschnitt zu
# akzeptieren.
WINDOW = 4


def _violations(path: Path) -> list[tuple[int, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    in_block: str | None = None
    found: list[tuple[int, str]] = []

    for idx, line in enumerate(lines):
        fence = FENCE.match(line)
        if fence:
            in_block = None if in_block is not None else (fence.group(1) or "text")
            continue

        candidates: list[str] = []
        if in_block is not None:
            candidates.append(line)
        else:
            candidates.extend(INLINE_CODE.findall(line))

        for candidate in candidates:
            if not BASHISM.search(candidate):
                continue
            lo, hi = max(0, idx - WINDOW), min(len(lines), idx + WINDOW + 1)
            if POWERSHELL.search("\n".join(lines[lo:hi])):
                continue
            found.append((idx + 1, candidate.strip()[:100]))

    return found


class TestDocumentedCommandsRunOnWindows:
    @pytest.mark.parametrize("path", _targets(), ids=lambda p: p.name)
    def test_no_unpaired_bashism(self, path: Path):
        violations = _violations(path)
        assert not violations, (
            f"{path.relative_to(REPO_ROOT)} dokumentiert Befehle, die in "
            f"PowerShell 5.1 nicht laufen, ohne eine PowerShell-Entsprechung "
            f"in der Nähe:\n"
            + "\n".join(f"  Zeile {ln}: {src}" for ln, src in violations)
            + "\n\nEntweder eine `powershell`-Fassung danebenstellen oder den "
            "Befehl portabel schreiben. Das Repo führt `windows-latest` in "
            "der Testmatrix; die Anleitung muss dort auch laufen (OPS-007)."
        )

    def test_targets_is_not_empty(self):
        # Ein parametrisierter Test über eine leere Liste ist grün und prüft
        # nichts. Genau die Sorte Grün, gegen die dieser Modul geschrieben ist.
        assert _targets(), "Keine Doku-Dateien gefunden — Pfade geprüft?"

    def test_the_readmes_are_covered(self):
        names = {p.name for p in _targets()}
        assert {"README.md", "README.de.md"} <= names


class TestTheScannerActuallyDetects:
    """Gegenprobe: Der Detektor muss jeden der drei Fundorte finden.

    Ohne diese Klasse belegt ein grüner Lauf oben nur, dass der Scanner
    nichts gemeldet hat — nicht, dass er hingeschaut hat. Die erste Fassung
    hat aus genau diesem Grund drei von vier Fällen übersehen.
    """

    @pytest.mark.parametrize(
        "body,label",
        [
            ('```bash\nexport NOTION_TOKEN="x"\n```\n', "fence am Spaltenanfang"),
            (
                '1. Schritt:\n   ```bash\n   export NOTION_TOKEN="x"\n   ```\n',
                "eingerueckte fence — der uebersehene Fall",
            ),
            ("- `ls foo && wc -l foo`\n", "inline code"),
            ("```sh\ncd a && make\n```\n", "&& im block"),
        ],
    )
    def test_the_scanner_finds_a_planted_violation(
        self, tmp_path: Path, body: str, label: str
    ):
        f = tmp_path / "README.md"
        f.write_text(f"# Titel\n\n{body}", encoding="utf-8")
        assert _violations(f), f"Scanner uebersieht: {label}"

    @pytest.mark.parametrize(
        "body,label",
        [
            (
                "```bash\nexport PYTHONUTF8=1   # Bash\n"
                '$env:PYTHONUTF8 = "1"   # PowerShell\n```\n',
                "beide Zeilen im selben Block",
            ),
            (
                '```bash\nexport NOTION_TOKEN="x"\n```\n\n'
                '```powershell\n$env:NOTION_TOKEN = "x"\n```\n',
                "zweiter Block direkt darunter",
            ),
            ("Normaler Fliesstext ueber `export` als Wort.\n", "Prosa, kein Befehl"),
            ("```bash\npython3 tools/parse_catalog.py\n```\n", "portabler Befehl"),
        ],
    )
    def test_the_scanner_stays_quiet_when_it_should(
        self, tmp_path: Path, body: str, label: str
    ):
        # Die andere Richtung. Ein Detektor, der alles meldet, wird
        # abgeschaltet — und dann meldet er nichts mehr.
        f = tmp_path / "README.md"
        f.write_text(f"# Titel\n\n{body}", encoding="utf-8")
        assert not _violations(f), f"Fehlalarm bei: {label}"

    def test_a_far_away_powershell_block_does_not_excuse_it(self, tmp_path: Path):
        # Das Fenster muss eng sein. Sonst entschuldigt ein
        # PowerShell-Beispiel irgendwo in der Datei jede bash-Zeile darin.
        far = "\n".join(["Fuellzeile"] * (WINDOW + 6))
        f = tmp_path / "README.md"
        f.write_text(
            f'```powershell\n$env:FOO = "1"\n```\n\n{far}\n\n'
            '```bash\nexport NOTION_TOKEN="x"\n```\n',
            encoding="utf-8",
        )
        assert _violations(f)
