"""Die Summary-Stufe von `quality-chain.yml` gegen den Bericht, den es gibt.

DER ANLASS IST GEMESSEN UND STEHT IM LAUFPROTOKOLL. Mit Phase 3 der
Zusammenführung wurde `docs/quality-chain.json` in zwei Listen geteilt —
`members` (die Skills) und `repos` (die Metadaten-Träger) — und
`tools/check_quality_chain.py` zog nach. Der Workflow zog nicht nach: Seine
Summary-Stufe las weiter `r["members"]` und `m["stage"]`.

Ergebnis: Der Wächter lief korrekt, schrieb sein JSON, und der Schritt danach
starb an `KeyError: 'members'`, bevor eine Zeile Bericht entstand. Der Job war
rot — aber aus einem Grund, der mit der Kette nichts zu tun hatte, und der
eigentliche Befund erschien nirgends. Lauf 31452485540 vom 11.8.2026.

WARUM DAS KEIN TEST FANG
------------------------
Der Workflow ist YAML. Sein Python steckt in einem Heredoc, das nur der Runner
je ausführt — also nirgends, wo `pytest` hinkommt. Genau die Sorte Code, die
zwischen zwei Änderungen auseinanderläuft, weil beide Seiten für sich stimmig
aussehen.

Dieser Test holt das Skript aus dem YAML und führt es gegen einen Bericht aus,
den `main()` WIRKLICH erzeugt hat. Damit ist die Verbindung geschlossen: Ändert
sich das Schema des Berichts, ohne dass der Workflow nachzieht, wird hier etwas
rot statt erst montags um 06:41 im Runner.

ZUM MOCK, DEN ES HIER GIBT
--------------------------
`tests/test_quality_chain.py` mockt `fetch()` bewusst NICHT: Ein Mock bildete
dort nur die eigene Annahme über GitHubs Antwort ab und könnte sie nie
widerlegen. Hier ist die Lage eine andere — geprüft wird nicht, was GitHub
sagt, sondern ob ZWEI EIGENE ARTEFAKTE dasselbe Schema meinen. Dafür muss der
Netzaufruf ersetzt werden, und die Ersetzung ist selbst nicht der Gegenstand.
"""

from __future__ import annotations

import io
import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from tools import check_quality_chain as guard

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "quality-chain.yml"

TOPIC = "mcp-quality-chain"
HOMEPAGE = "https://github.com/topics/mcp-quality-chain"


def summary_script() -> str:
    """Das Python aus dem Heredoc der Summary-Stufe.

    Der Anker ist das Heredoc-Wort `PY`. Verschwindet es — weil jemand den
    Schritt auf eine Datei umstellt —, ist das ein FEHLER und kein stilles
    Durchwinken: Dieser Test hätte dann nichts mehr, wogegen er prüft.
    """
    text = WORKFLOW.read_text(encoding="utf-8")
    # `<<'PY'` steht nicht am Zeilenende — dahinter folgt die Umleitung in
    # `$GITHUB_STEP_SUMMARY`. Der erste Anlauf hier las bis zum Zeilenumbruch
    # und fand nichts.
    match = re.search(r"python - <<'PY'[^\n]*\n(.*?)\n[ \t]*PY\n", text, re.S)
    if match is None:
        raise AssertionError(
            f"{WORKFLOW.name}: kein Heredoc `python - <<'PY' … PY` gefunden — "
            "der Anker ist weg, dieser Test prüfte sonst nichts mehr."
        )
    return textwrap.dedent(match.group(1))


def bericht(*, sauber: bool, monkeypatch: pytest.MonkeyPatch) -> str:
    """Ein echter Bericht aus `main()`, nicht einer von Hand nachgebaut.

    Von Hand nachgebaut hätte er genau den Wert null: Er trüge dann meine
    Annahme über das Schema, und die ist das, was hier zur Debatte steht.
    """
    meta = {
        "topics": [TOPIC] if sauber else ["mcp"],
        "homepage": HOMEPAGE,
        "description": "Ein Repo mit Beschreibung",
    }
    traeger = [{"full_name": name, "archived": False} for name in _manifest_repos()]
    if not sauber:
        traeger.append({"full_name": "malkreide/alt-skill", "archived": True})

    monkeypatch.setattr(guard, "fetch", lambda repo, timeout=15.0: (dict(meta), "ok"))
    monkeypatch.setattr(
        guard,
        "fetch_carriers",
        lambda topic, timeout=15.0: (traeger, len(traeger), "ok"),
    )

    puffer = io.StringIO()
    monkeypatch.setattr(sys, "stdout", puffer)
    code = guard.main(["--format", "json"])
    monkeypatch.undo()

    assert code == (0 if sauber else 1), f"unerwarteter Exit-Code {code}"
    return puffer.getvalue()


def _manifest_repos() -> list[str]:
    return guard.load_manifest(REPO_ROOT / "docs" / "quality-chain.json")["repos"]


def _lauf(tmp_path: Path, roh: str) -> str:
    """Das Summary-Skript in einem eigenen Prozess, wie im Runner."""
    (tmp_path / "result.json").write_text(roh, encoding="utf-8")
    done = subprocess.run(
        [sys.executable, "-c", summary_script()],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, (
        "Die Summary-Stufe ist gestorben — genau der Fall, der eine Woche lang "
        f"unbemerkt lief:\n{done.stderr}"
    )
    return done.stdout


def test_ANKER_der_gruene_bericht_erzeugt_eine_summary(tmp_path, monkeypatch):
    ausgabe = _lauf(tmp_path, bericht(sauber=True, monkeypatch=monkeypatch))
    assert "Qualitätskette OK" in ausgabe
    for repo in _manifest_repos():
        assert repo in ausgabe


def test_ANKER_der_rote_bericht_erzeugt_eine_summary(tmp_path, monkeypatch):
    ausgabe = _lauf(tmp_path, bericht(sauber=False, monkeypatch=monkeypatch))
    assert "Abweichungen" in ausgabe
    # Beide Richtungen müssen in der Tabelle stehen — die fehlende Zusage am
    # einzelnen Repo UND der überzählige Träger.
    assert f"Topic '{TOPIC}' fehlt" in ausgabe
    assert "Überzählig" in ausgabe
    assert "alt-skill" in ausgabe


def test_die_summary_nennt_die_kommandos_zum_beheben(tmp_path, monkeypatch):
    ausgabe = _lauf(tmp_path, bericht(sauber=False, monkeypatch=monkeypatch))
    assert "--add-topic" in ausgabe
    assert "--remove-topic" in ausgabe
    # Der archivierte Träger braucht das Paar drumherum, sonst läuft das
    # Kommando beim Ausführen ins Leere.
    assert "gh repo unarchive" in ausgabe


def test_ein_fehlendes_ergebnis_bricht_die_summary_nicht_ab(tmp_path):
    """Stirbt der Schritt davor, soll dieser sagen WARUM nichts dasteht —
    nicht mit einem zweiten Fehler darüberschreiben."""
    ausgabe = _lauf(tmp_path, "")
    assert "Kein Ergebnis" in ausgabe


def test_ANKER_der_bericht_fuehrt_die_felder_die_der_workflow_liest(monkeypatch):
    """Die Verbindung ausbuchstabiert, damit die Fehlermeldung sie nennt.

    Die Tests darüber laufen über das Skript und melden im Zweifel einen
    `KeyError` aus einem Subprozess. Dieser hier sagt, welches Feld fehlt.
    """
    report = json.loads(bericht(sauber=True, monkeypatch=monkeypatch))
    for feld in ("topic", "repos", "carriers", "ok"):
        assert feld in report, f"Der Bericht führt '{feld}' nicht (mehr)"
    assert all("repo" in e and "ok" in e for e in report["repos"])
    assert {"ok", "problems", "fix"} <= set(report["carriers"])
