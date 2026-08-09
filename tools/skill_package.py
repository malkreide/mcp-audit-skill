#!/usr/bin/env python3
"""Was in `mcp-audit.skill` liegt — an EINER Stelle.

Dieses Modul enthält keine Ein-/Ausgabe außer dem Lesen des Manifests. Es
beantwortet genau zwei Fragen, beide als Wert:

  * Welche Dateien gehören ins Paket? (`package_files`)
  * Ist das Frontmatter von SKILL.md so, dass die Skill-Plattform den Upload
    annimmt? (`frontmatter_problems`)

Zwei Programme fragen: `tools/build_skill.py` baut daraus das Archiv,
`tools/checks/skill_archive.py` (Check 5) hält das eingecheckte Archiv
dagegen. **Getrennte Listen wären hier der teuerste Fehler**, den dieses Repo
kennt: Der Build packte, was er für richtig hält, die Prüfung vergliche gegen
das, was sie für richtig hält, und beide meldeten grün — während der Nutzer
ein Paket herunterlädt, dem der halbe Katalog fehlt. Ein Skill, das ohne
`checks/` ankommt, sagt beim Audit nichts Falsches; es sagt weniger und sieht
dabei vollständig aus. Genau die Klasse Fehler, gegen die `OPS-004` steht.

Die reinen Funktionen (`parse_manifest`, `frontmatter_problems`) nehmen Text
und geben Werte zurück — dieselbe Bauart wie `compare()` in
`tools/check_ruff_pin.py`, und aus demselben Grund: Der Teil, der schiefgehen
kann, soll ohne Dateisystem prüfbar sein.
"""

from __future__ import annotations

import re
from pathlib import Path

# Der Name aus dem Frontmatter von SKILL.md. Er bestimmt drei Dinge, die
# zusammenpassen müssen: das Wurzelverzeichnis im Archiv, den Dateinamen des
# Archivs und den Pfad, unter dem Claude das Skill installiert.
SKILL_NAME = "mcp-audit"
ARCHIVE_NAME = f"{SKILL_NAME}.skill"
MANIFEST_NAME = "skill-manifest.txt"

# Obergrenze der Skill-Plattform für das Frontmatter-Feld `description`.
# Darüber weist der Upload ab — und zwar erst beim Nutzer, nicht beim Bauen.
DESCRIPTION_MAX_CHARS = 1024

# Untergrenze ohne Plattform-Bezug: eine Beschreibung, die nicht sagt, wann
# der Skill greifen soll, löst ihn nicht zuverlässig aus. Der Wert ist eine
# Konvention der Kette, kein Limit von außen.
DESCRIPTION_MIN_CHARS = 40

_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)


class ManifestError(Exception):
    """Das Manifest ist unbrauchbar — als Text oder gegen den Baum."""


def parse_manifest(text: str) -> tuple[list[str], list[str]]:
    """Rein: Manifest-Text → `(Einschluss-Muster, Ausschluss-Muster)`.

    Eine Zeile mit führendem `!` schließt aus, was ein Einschluss-Muster
    zuvor eingesammelt hat. Der Ausschluss existiert, damit die
    Einschluss-Muster grob bleiben dürfen: `tools/*.py` und drei benannte
    Ausnahmen altern anders als eine Liste von zwanzig einzelnen Dateien —
    ein neues Werkzeug landet automatisch im Paket, und wer es NICHT dort
    haben will, muss das hinschreiben und begründen.

    Verworfen wird, was im Archiv nicht landen kann, ohne es zu verlassen:
    absolute Pfade, `..`-Segmente und Backslashes. Der letzte Punkt ist kein
    Purismus — die Testmatrix dieses Repos fährt `windows-latest`, und ein
    dort eingetragenes `docs\\*.md` passte unter Linux auf nichts und fiele
    damit unter die Regel «Muster ohne Treffer», also in einen Fehler mit der
    falschen Begründung.
    """
    patterns: list[str] = []
    excludes: list[str] = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        ausschluss = line.startswith("!")
        if ausschluss:
            line = line[1:].strip()
            if not line:
                raise ManifestError(
                    f"{MANIFEST_NAME}:{lineno}: '!' ohne Muster dahinter."
                )
        if "\\" in line:
            raise ManifestError(
                f"{MANIFEST_NAME}:{lineno}: Backslash in '{line}' — Muster "
                "werden mit '/' geschrieben, auch unter Windows."
            )
        if line.startswith("/") or re.match(r"^[A-Za-z]:", line):
            raise ManifestError(
                f"{MANIFEST_NAME}:{lineno}: absoluter Pfad '{line}' — Muster "
                "sind relativ zum Repository-Root."
            )
        if ".." in Path(line).parts:
            raise ManifestError(
                f"{MANIFEST_NAME}:{lineno}: '{line}' verlässt das Repository."
            )
        (excludes if ausschluss else patterns).append(line)
    if not patterns:
        raise ManifestError(f"{MANIFEST_NAME} nennt kein einziges Muster.")
    return patterns, excludes


def _treffer(root: Path, pattern: str) -> list[str]:
    """Repo-relative Pfade der Dateien, auf die ein Muster passt."""
    return sorted(
        p.relative_to(root).as_posix()
        for p in root.glob(pattern)
        if p.is_file() and not p.is_symlink()
    )


def expand(root: Path, patterns: list[str], excludes: list[str]) -> list[str]:
    """Muster → sortierte, doppelfreie Liste repo-relativer Dateipfade.

    EIN MUSTER OHNE WIRKUNG IST EIN FEHLER, kein leeres Ergebnis — und das
    gilt in beide Richtungen. Ein Einschluss ohne Treffer würde das Paket
    stillschweigend um ein ganzes Verzeichnis erleichtern (`checks/` einmal
    umbenannt, und der Skill kommt ohne Katalog beim Nutzer an). Ein
    Ausschluss ohne Wirkung ist harmloser, aber irreführend: Er behauptet,
    etwas herauszuhalten, das längst niemand mehr einsammelt, und beim
    nächsten Lesen begründet er eine Entscheidung, die es nicht gibt.

    Verzeichnisse, auf die ein Muster passt, werden übergangen: Ein ZIP
    braucht keine Verzeichniseinträge, und ein leeres Verzeichnis im Archiv
    wäre die Sorte Rest, die bei jedem Diff auffällt und nie etwas bedeutet.
    """
    seen: set[str] = set()
    for pattern in patterns:
        treffer = _treffer(root, pattern)
        if not treffer:
            raise ManifestError(
                f"{MANIFEST_NAME}: Muster '{pattern}' passt auf keine Datei. "
                "Entweder ist es veraltet, oder eine Datei fehlt — beides "
                "hieße, dass das Paket ohne sie ausgeliefert würde."
            )
        seen.update(treffer)

    for pattern in excludes:
        entfernt = seen & set(_treffer(root, pattern))
        if not entfernt:
            raise ManifestError(
                f"{MANIFEST_NAME}: Ausschluss '!{pattern}' nimmt nichts aus "
                "dem Paket. Entweder ist die Datei weg, oder kein "
                "Einschluss-Muster sammelt sie mehr ein — in beiden Fällen "
                "begründet die Zeile eine Entscheidung, die nicht mehr fällt."
            )
        seen -= entfernt
    return sorted(seen)


def package_files(root: Path) -> list[str]:
    """Die Paketliste dieses Baums: Manifest lesen, Muster auflösen."""
    manifest = root / MANIFEST_NAME
    if not manifest.is_file():
        raise ManifestError(f"{MANIFEST_NAME} fehlt in {root}.")
    patterns, excludes = parse_manifest(manifest.read_text(encoding="utf-8"))
    files = expand(root, patterns, excludes)
    if "SKILL.md" not in files:
        raise ManifestError(
            f"{MANIFEST_NAME}: SKILL.md ist nicht im Paket. Ohne den "
            "Einstiegspunkt ist das Archiv kein Skill."
        )
    return files


def member_name(relative_path: str) -> str:
    """Repo-relativer Pfad → Eintragsname im Archiv.

    Das Archiv trägt genau ein Wurzelverzeichnis, benannt nach dem Skill.
    Claude entpackt es unter diesem Namen; ein Archiv ohne diese Wurzel
    schüttete seinen Inhalt in das Skill-Verzeichnis der Plattform.
    """
    return f"{SKILL_NAME}/{relative_path}"


def frontmatter_problems(skill_md: str) -> list[str]:
    """Rein: SKILL.md-Text → Liste der Beanstandungen (leer = in Ordnung).

    Geprüft wird, woran der Upload scheitert, nicht der Inhalt. Diese Grenze
    ist Absicht: Was der Skill sagt, prüfen die Tests dieses Repos; was die
    Plattform annimmt, prüft diese Funktion — und zwar VOR dem Bauen, damit
    der Fehlschlag hier passiert und nicht im Browser des Nutzers.
    """
    problems: list[str] = []
    match = _FRONTMATTER.match(skill_md)
    if not match:
        return ["SKILL.md: kein YAML-Frontmatter am Dateianfang."]

    block = match.group(1)
    name = re.search(r"^name:\s*(\S.*)$", block, re.M)
    description = re.search(r"^description:\s*(\S.*)$", block, re.M)

    if name is None:
        problems.append("SKILL.md: Frontmatter-Feld 'name' fehlt.")
    elif name.group(1).strip() != SKILL_NAME:
        problems.append(
            f"SKILL.md: 'name' ist '{name.group(1).strip()}', erwartet "
            f"'{SKILL_NAME}' — der Name benennt zugleich das Wurzelverzeichnis "
            f"im Archiv und {ARCHIVE_NAME}."
        )

    if description is None:
        problems.append("SKILL.md: Frontmatter-Feld 'description' fehlt.")
    else:
        length = len(description.group(1).strip())
        if length < DESCRIPTION_MIN_CHARS:
            problems.append(
                f"SKILL.md: 'description' hat {length} Zeichen — zu wenig, um "
                "den Skill zuverlässig auszulösen."
            )
        elif length > DESCRIPTION_MAX_CHARS:
            problems.append(
                f"SKILL.md: 'description' hat {length} Zeichen, erlaubt sind "
                f"höchstens {DESCRIPTION_MAX_CHARS}. Claude weist den Upload "
                "sonst ab."
            )
    return problems
