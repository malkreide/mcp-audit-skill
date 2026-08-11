#!/usr/bin/env python3
"""Hält die Repos der Qualitätskette auf GitHub als Gruppe erkennbar.

Die Kette hat vier Mitglieder, und Mitglied ist ein SKILL: Probe vor dem Bau,
Datentreue und Transport-Härtung im Bau, Audit nach dem Bau. Getragen werden
sie seit Phase 3 der Zusammenführung von ZWEI Repositories — diesem hier und
`mcp-continuous-auditor`, der Laufzeit, die die Kette fährt. Dieser Guard
prüft die Repos, weil Topic und Homepage Eigenschaften eines Repositories
sind; welche Skills die Kette bilden, steht daneben in `members`.

Der Anlass ist älter als diese Aufteilung und gilt unverändert. Gemessen am
Tag, an dem dieser Guard entstand, war die Schnittmenge der Topics über die
damals fünf Repos **leer**: `mcp-continuous-auditor` trug überhaupt keine
Topics, die anderen vier benutzten zwei verschiedene Vokabulare
(`claude-skill` gegen `claude-skills`), und eine Homepage hatte nur eines von
fünf.

Damit war die Kette genau dort unsichtbar, wo jemand sie findet, der nicht
schon eines der Repos offen hat: in der Suche. Ein Topic ist die einzige
Gruppierung, die GitHub selbst auswertet — `github.com/topics/<topic>` listet
die Mitglieder ohne dass jemand eine Liste pflegt.

Dieselbe Bauart wie `check_repo_description.py`, und aus demselben Grund: Es
ist Metadaten **ausserhalb** des Repos, also erreicht sie kein Test der
Arbeitskopie, also driftet sie.

DREI ENTSCHEIDUNGEN, DIE NICHT VERHANDELBAR SIND
------------------------------------------------
1. **Eine nicht erreichbare API ist kein Bestehen.** Ohne Antwort hat der
   Vergleich nicht stattgefunden; dann meldet der Guard `UNKNOWN` und endet mit
   1. Aus dem lokalen Manifest allein «stimmt» zu drucken wäre der Fehler, den
   `DRIFT-003` beschreibt.

2. **Ein fehlendes Feld ist nicht ein leeres Feld.** Liefert die API zu einem
   Repo gar kein `topics`, dann ist das *unbekannt* und nicht *keine Topics*.
   Beides als «Topic fehlt» zu melden wäre bequem und einmal falsch — nämlich
   wenn die API das Feld nicht mehr mitschickt, und dann meldet der Guard je
   einen Befund pro Repo, wo null Evidenz vorliegt. Das ist die Trennung, die
   `FID-006` verlangt.

3. **Der Guard schreibt nicht.** Topics und Homepage zu setzen braucht ein
   Token mit Administrationsrechten, und Repo-Metadaten zu ändern gehört einem
   Menschen. Der Guard benennt die Abweichung und druckt das fertige
   `gh`-Kommando.

Der Vergleich ist eine reine Funktion: `compare()` nimmt das Metadaten-Dict
entgegen und ist ohne Netz testbar. Netz braucht nur `fetch()`, und das ist
absichtlich die dünnste Funktion der Datei.

DIE ANDERE RICHTUNG — ÜBERZÄHLIGE TRÄGER
----------------------------------------
Bis zur Archivierung der drei Herkunftsrepos war nur EINE Frage gestellt:
«Trägt jedes Repo aus dem Manifest das Topic?» Das ist die Hälfte, die auffällt,
wenn jemand ein Repo hinzufügt und die Metadaten vergisst.

Die andere Hälfte fällt nie auf: Ein Repo, das das Topic trägt und **nicht** im
Manifest steht. Genau das ist mit der Zusammenführung eingetreten — die drei
archivierten Skill-Repos tragen `mcp-quality-chain` weiterhin. Der Wächter war
grün, das Manifest war richtig, und die Topic-Seite zeigte fünf Einträge, wo
zwei gelten. Wer die Kette über GitHub sucht — also über den einen Weg, für den
dieser Guard überhaupt existiert — findet drei Gräber.

Deshalb fragt `compare_carriers()` den Bestand über die Suche ab und meldet
jeden Träger, den das Manifest nicht kennt. Zwei Eigenarten der Such-API sind
dabei berücksichtigt und stehen dort im Docstring: Ihr Index hinkt Änderungen
nach, und ein leeres Ergebnis ist hier ein BEFUND und kein Bestehen.

Geprüft wird pro Repo:
  * das gemeinsame Topic aus dem Manifest ist gesetzt,
  * die Homepage zeigt auf den gemeinsamen Einstiegspunkt,
  * die Description ist nicht leer (die erste Zeile, die jemand liest).

Und einmal über den ganzen Bestand:
  * kein Repo trägt das Topic, das nicht im Manifest steht.

Exit-Codes:
  0  alle Repos tragen Topic, Homepage und Description, und kein weiteres Repo
     trägt das Topic
  1  Abweichung, oder die Metadaten konnten nicht geholt werden
  2  Aufruffehler (Manifest nicht lesbar)

Aufruf:
    python tools/check_quality_chain.py
    python tools/check_quality_chain.py --format json
    python tools/check_quality_chain.py --manifest docs/quality-chain.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.path_utils import force_utf8_stdio  # noqa: E402

API = "https://api.github.com/repos/{repo}"
SEARCH = "https://api.github.com/search/repositories?q=topic:{topic}&per_page=100"

# Sentinel für «die API hat das Feld nicht mitgeschickt». `None` allein reicht
# nicht: die API liefert für eine leere Homepage sowohl `null` als auch `""`,
# und beides ist eine Aussage. Ein fehlender Schlüssel ist keine.
MISSING = object()


def _default_manifest() -> Path:
    return _REPO_ROOT / "docs" / "quality-chain.json"


def load_manifest(path: Path) -> dict[str, Any]:
    """Manifest lesen und auf die Felder prüfen, die compare() braucht.

    ZWEI LISTEN, WEIL ES ZWEI FRAGEN SIND. Seit Phase 3 der Zusammenführung
    ist Mitglied der Kette ein SKILL, nicht ein Repo — und die Skills liegen
    inzwischen fast alle im selben Repository. `members` trägt die Kette
    (welche Frage an welcher Stelle), `repos` sagt diesem Wächter, wessen
    GitHub-Metadaten er prüfen soll. Beides in einer Liste zu führen ginge nur,
    solange Skill und Repo dasselbe waren.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ("topic", "homepage", "members", "repos"):
        if not data.get(key):
            raise ValueError(f"{path}: Feld '{key}' fehlt oder ist leer")

    skills = [m.get("skill") for m in data["members"]]
    if not all(skills):
        raise ValueError(f"{path}: ein Mitglied ohne 'skill'")
    if len(set(skills)) != len(skills):
        raise ValueError(f"{path}: doppeltes Mitglied in 'members'")

    if len(set(data["repos"])) != len(data["repos"]):
        raise ValueError(f"{path}: doppeltes Repo in 'repos'")
    return data


def compare(meta: dict[str, Any], topic: str, homepage: str) -> list[str]:
    """Abweichungen eines Repos vom Manifest. Leer heisst: stimmt.

    Reine Funktion, absichtlich ohne Netz und ohne Dateizugriff — siehe
    Modul-Docstring. `meta` benutzt `MISSING` für Felder, die die API gar nicht
    mitgeschickt hat; die sind *ungeprüft* und werden als solche gemeldet.
    """
    problems: list[str] = []

    topics = meta.get("topics", MISSING)
    if topics is MISSING:
        problems.append(
            "UNVERIFIED: Antwort enthält kein Feld 'topics' — das Topic wurde "
            "NICHT geprüft. Das ist kein Bestehen."
        )
    elif topic not in (topics or []):
        have = ", ".join(sorted(topics or [])) or "keine"
        problems.append(f"Topic '{topic}' fehlt (gesetzt: {have})")

    home = meta.get("homepage", MISSING)
    if home is MISSING:
        problems.append(
            "UNVERIFIED: Antwort enthält kein Feld 'homepage' — die Homepage "
            "wurde NICHT geprüft. Das ist kein Bestehen."
        )
    elif (home or "").rstrip("/") != homepage.rstrip("/"):
        problems.append(f"Homepage ist {home!r}, erwartet {homepage!r}")

    description = meta.get("description", MISSING)
    if description is MISSING:
        problems.append(
            "UNVERIFIED: Antwort enthält kein Feld 'description' — die "
            "Description wurde NICHT geprüft. Das ist kein Bestehen."
        )
    elif not (description or "").strip():
        problems.append("Description ist leer — die erste Zeile, die jemand liest")

    return problems


def fix_commands(
    repo: str, meta: dict[str, Any], topic: str, homepage: str
) -> list[str]:
    """Die `gh`-Kommandos, die die Abweichungen dieses Repos beheben.

    Die REST-API kennt für Topics nur *ersetzen*, nicht ergänzen; `gh repo edit
    --add-topic` legt die Vereinigung selbst an. Ausgegeben wird trotzdem die
    Liste, die danach gesetzt sein muss — wer das Kommando von Hand in einen
    API-Aufruf übersetzt, räumt sonst die übrigen Topics ab.
    """
    commands: list[str] = []

    topics = meta.get("topics", MISSING)
    if topics is not MISSING and topic not in (topics or []):
        merged = sorted(set(topics or []) | {topic})
        commands.append(
            f"gh repo edit {repo} --add-topic {topic}"
            f"   # danach gesetzt: {', '.join(merged)}"
        )

    home = meta.get("homepage", MISSING)
    if home is not MISSING and (home or "").rstrip("/") != homepage.rstrip("/"):
        commands.append(f"gh repo edit {repo} --homepage {homepage}")

    description = meta.get("description", MISSING)
    if description is not MISSING and not (description or "").strip():
        commands.append(f'gh repo edit {repo} --description "…"')

    return commands


def compare_carriers(
    carriers: list[dict[str, Any]],
    declared: list[str],
    topic: str,
    total_count: int | None = None,
) -> list[str]:
    """Wer trägt das Topic, ohne im Manifest zu stehen. Leer heisst: niemand.

    Reine Funktion, ohne Netz und ohne Dateizugriff — dieselbe Bauart wie
    `compare()` und aus demselben Grund.

    `carriers` sind die Suchtreffer, je ein Dict mit `full_name` und
    `archived`. Repo-Namen vergleicht GitHub ohne Rücksicht auf Gross- und
    Kleinschreibung, also tut es diese Funktion auch.

    DREI EIGENARTEN, DIE HIER ENTSCHIEDEN SIND
    ------------------------------------------
    1. **Ein leeres Ergebnis ist ein Befund.** Die deklarierten Repos tragen
       das Topic — das prüft `compare()` direkt an der Repo-API und damit an
       der verlässlichen Quelle. Findet die Suche daraufhin *gar nichts*, ist
       nicht «keine Überzähligen» belegt, sondern der Index hat nicht
       geantwortet. Das als «sauber» zu drucken wäre genau der Fall, für den
       dieses Portfolio `UNVERIFIED` führt.

    2. **Eine gekappte Trefferliste sagt es.** Liefert die Suche mehr Treffer,
       als sie Einträge mitschickt, ist die Abdeckung unvollständig. Ein
       stummer Deckel liest sich hinterher wie Vollständigkeit.

    3. **Der Index hinkt nach.** Ein eben entferntes Topic kann noch Minuten
       bis Stunden in der Suche stehen. Ein Träger, der unmittelbar nach einer
       Aufräumaktion gemeldet wird, ist deshalb möglicherweise Nachhall — der
       zweite Lauf entscheidet. Umgekehrt gilt das Gleiche und ist der Grund,
       warum diese Funktion NICHT nach fehlenden Topics sucht: Dafür ist die
       Repo-API zuständig, die keinen Index dazwischen hat.
    """
    problems: list[str] = []

    if not carriers:
        return [
            f"UNVERIFIED: Die Suche liefert kein einziges Repo mit dem Topic "
            f"'{topic}' — auch die deklarierten nicht. Damit hat der Vergleich "
            "nicht stattgefunden; überzählige Träger wurden NICHT geprüft. "
            "Das ist kein Bestehen."
        ]

    if total_count is not None and total_count > len(carriers):
        problems.append(
            f"UNVERIFIED: Die Suche meldet {total_count} Treffer, mitgeschickt "
            f"wurden {len(carriers)}. Die übrigen sind ungeprüft — der Befund "
            "unten ist damit unvollständig und nicht 'alles gefunden'."
        )

    bekannt = {name.lower() for name in declared}
    for eintrag in carriers:
        name = eintrag.get("full_name") or ""
        if not name:
            problems.append(
                "UNVERIFIED: Ein Suchtreffer ohne 'full_name' — nicht "
                "zuzuordnen und deshalb nicht als sauber verbucht."
            )
            continue
        if name.lower() in bekannt:
            continue
        zusatz = " (archiviert)" if eintrag.get("archived") else ""
        problems.append(
            f"Überzählig: {name}{zusatz} trägt '{topic}', steht aber nicht im "
            "Manifest. Die Topic-Seite zeigt es damit als Mitglied der Kette."
        )

    return problems


def carrier_fix_commands(
    carriers: list[dict[str, Any]], declared: list[str], topic: str
) -> list[str]:
    """Die `gh`-Kommandos, die die überzähligen Träger entfernen.

    Ein archiviertes Repository ist schreibgeschützt; das Zahnrad neben
    «About» ist dort ausgegraut. Weist `gh` die Änderung ab, muss es für den
    Handgriff kurz aus dem Archiv — deshalb steht das Paar dabei, statt dass
    jemand erst an der Fehlermeldung merkt, dass ein Schritt fehlt.
    """
    bekannt = {name.lower() for name in declared}
    commands: list[str] = []
    for eintrag in carriers:
        name = eintrag.get("full_name") or ""
        if not name or name.lower() in bekannt:
            continue
        if eintrag.get("archived"):
            commands.append(
                f"gh repo unarchive {name} --yes && "
                f"gh repo edit {name} --remove-topic {topic} && "
                f"gh repo archive {name} --yes"
                "   # archiviert = schreibgeschuetzt, deshalb das Paar drumherum"
            )
        else:
            commands.append(f"gh repo edit {name} --remove-topic {topic}")
    return commands


def fetch_carriers(
    topic: str, timeout: float = 15.0
) -> tuple[list[dict[str, Any]] | None, int | None, str]:
    """(treffer, total_count, status). Wirft nie — der Aufrufer meldet den Status.

    Wie `fetch()` absichtlich dünn gehalten: Was hier passiert, ist für Tests
    unerreichbar, also soll hier so wenig wie möglich passieren. Reduziert wird
    auf die zwei Felder, die `compare_carriers()` braucht.
    """
    req = urllib.request.Request(SEARCH.format(topic=urllib.parse.quote(topic)))
    req.add_header("Accept", "application/vnd.github+json")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return None, None, f"GitHub antwortete HTTP {exc.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return None, None, f"GitHub nicht erreichbar: {exc}"
    except (ValueError, KeyError) as exc:
        return None, None, f"Antwort nicht lesbar: {exc}"

    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        return None, None, "Antwort enthält keine Trefferliste 'items'"

    treffer = [
        {"full_name": item.get("full_name"), "archived": bool(item.get("archived"))}
        for item in payload["items"]
        if isinstance(item, dict)
    ]
    gesamt = payload.get("total_count")
    return treffer, gesamt if isinstance(gesamt, int) else None, "ok"


def fetch(repo: str, timeout: float = 15.0) -> tuple[dict[str, Any] | None, str]:
    """(metadata, status). Wirft nie — der Aufrufer meldet den Status.

    Absichtlich die dünnste Funktion der Datei: alles, was hier passiert, ist
    für Tests unerreichbar, also soll hier so wenig wie möglich passieren.

    Fehlende Schlüssel werden zu `MISSING` und *nicht* zu einem Default —
    siehe Modul-Docstring, Punkt 2.
    """
    req = urllib.request.Request(API.format(repo=repo))
    req.add_header("Accept", "application/vnd.github+json")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return None, f"GitHub antwortete HTTP {exc.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return None, f"GitHub nicht erreichbar: {exc}"
    except (ValueError, KeyError) as exc:
        return None, f"Antwort nicht lesbar: {exc}"

    if not isinstance(payload, dict):
        return None, "Antwort ist kein Repo-Objekt"

    return {
        key: payload.get(key, MISSING) for key in ("topics", "homepage", "description")
    }, "ok"


def _jsonable(meta: dict[str, Any]) -> dict[str, Any]:
    """MISSING ist nicht JSON-serialisierbar — als `null` mit Marker ausgeben."""
    return {k: (None if v is MISSING else v) for k, v in meta.items()}


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdio()
    parser = argparse.ArgumentParser(
        prog="check_quality_chain",
        description=(
            "Prüft, ob die Repos der Qualitätskette auf GitHub als Gruppe "
            "erkennbar sind: gemeinsames Topic, gemeinsame Homepage, "
            "Description gesetzt."
        ),
    )
    parser.add_argument("--manifest", default=str(_default_manifest()))
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)
    try:
        manifest = load_manifest(manifest_path)
    except (OSError, ValueError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 2

    topic = manifest["topic"]
    homepage = manifest["homepage"]

    # Geprüft werden REPOS, nicht Mitglieder: Topic und Homepage sind
    # Eigenschaften eines Repositories, und seit Phase 3 tragen zwei Repos die
    # vier Skills der Kette.
    results: list[dict[str, Any]] = []
    for repo in manifest["repos"]:
        meta, status = fetch(repo, args.timeout)
        entry: dict[str, Any] = {
            "repo": repo,
            "status": status,
            "metadata": None if meta is None else _jsonable(meta),
            "problems": [],
            "fix": [],
            "ok": False,
        }
        if meta is None:
            # Der Vergleich hat nicht stattgefunden — das ist kein Bestehen.
            entry["problems"] = [f"UNKNOWN: {status} — NICHT geprüft."]
        else:
            entry["problems"] = compare(meta, topic, homepage)
            entry["fix"] = fix_commands(repo, meta, topic, homepage)
            entry["ok"] = not entry["problems"]
        results.append(entry)

    # Die andere Richtung: Wer traegt das Topic, ohne im Manifest zu stehen?
    # Eine einzige Anfrage ueber den ganzen Bestand statt eine pro Repo.
    treffer, gesamt, carrier_status = fetch_carriers(topic, args.timeout)
    carriers: dict[str, Any] = {
        "status": carrier_status,
        "found": treffer,
        "total_count": gesamt,
        "problems": [],
        "fix": [],
        "ok": False,
    }
    if treffer is None:
        carriers["problems"] = [
            f"UNKNOWN: {carrier_status} — überzählige Träger NICHT geprüft."
        ]
    else:
        carriers["problems"] = compare_carriers(
            treffer, manifest["repos"], topic, gesamt
        )
        carriers["fix"] = carrier_fix_commands(treffer, manifest["repos"], topic)
        carriers["ok"] = not carriers["problems"]

    ok = all(r["ok"] for r in results) and carriers["ok"]
    report = {
        "topic": topic,
        "homepage": homepage,
        "repos": results,
        "carriers": carriers,
        "ok": ok,
    }

    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if ok else 1

    for entry in results:
        if entry["ok"]:
            print(f"OK       {entry['repo']}")
            continue
        print(f"DRIFT    {entry['repo']}")
        for problem in entry["problems"]:
            print(f"         {problem}")

    if carriers["ok"]:
        print(f"OK       Topic '{topic}' — kein überzähliger Träger")
    else:
        print(f"DRIFT    Topic '{topic}' — Bestand")
        for problem in carriers["problems"]:
            print(f"         {problem}")

    if ok:
        print()
        print(
            f"Alle {len(results)} Repos tragen Topic '{topic}', die "
            f"Homepage und eine Description — und kein weiteres Repo trägt es."
        )
        return 0

    commands = [c for entry in results for c in entry["fix"]] + carriers["fix"]
    if commands:
        print()
        print("Zu setzen (der Guard schreibt bewusst nicht):")
        for command in commands:
            print(f"  {command}")
    print()
    print(
        "Topics und Homepage stehen auf der Repo-Startseite in der rechten "
        "Spalte «About», Zahnrad-Symbol — nicht in den Settings."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
