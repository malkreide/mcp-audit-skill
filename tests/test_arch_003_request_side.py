"""Hält `ARCH-003` an die Seite, die er bis v2.1.0 nicht gemessen hat.

Beide Modi des Checks lasen die **Antwort**: Empty-Result-Pattern im Quelltext,
`match_type`-Feld, handlungsfähiger Hinweis. Keiner mass, was **rausgegangen**
ist. Ein Server, der seine eigenen Vorschläge still selbst absucht und deren
Treffer unter `results` mischt, bestand den Check — und das Pass-Pattern des
Checks führte genau das vor.

Belegfall `amtsblatt-mcp` (Portfolio, 2026-08): 0.20.0 lehnte Kriterium 1 mit
Rubriken ab, die der Server ohnehin nicht ausliefert; gefunden hat das erst ein
Re-Audit, das die Rubrik-Listen las, nicht ein Modus dieses Checks. Bemerkens-
wert an 0.22.0 ist die Reihenfolge: Der Zähler-Test existierte lange vor dem
Vorschlagsmechanismus — der Server war nachweislich unschädlich und nachweislich
nutzlos. Deshalb hält diese Datei das **Paar** fest, nicht eine Hälfte.

**Jede Prüfung hier scheitert auch, wenn ihr Muster gar nichts findet.** Ein
Test, der nach einer Umformulierung ins Leere greift, prüft stillschweigend
nichts mehr — dieselbe Fehlerklasse, gegen die der Check selbst gerichtet ist.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKS_DIR = REPO_ROOT / "checks"
ARCH_003 = CHECKS_DIR / "ARCH-003.md"

# Eine Zuweisung, die heuristische Treffer in die primäre Ergebnisliste legt.
# Bewusst ohne die Diff-Minuszeile: Ein Remediation-Block *soll* das
# Anti-Pattern zeigen, solange er es entfernt.
MIXING = re.compile(r'^[+ ]?\s*"results"\s*:\s*fuzzy', re.M)

# Vorschläge aus einem Korpus statt aus der Eingabe — dieselbe Unterscheidung,
# eine Zeile früher: das ist eine zweite Abfrage, die niemand angefordert hat.
CORPUS_SUGGESTIONS = re.compile(r"^[+ ]?\s*\w+\s*=\s*await\s+db\.popular_", re.M)


@pytest.fixture(scope="module")
def text() -> str:
    return ARCH_003.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def criteria(text: str) -> list[str]:
    """Die Pass-Criteria-Zeilen. Leer heisst: Anker weg, nichts geprüft."""
    section = text.split("## Pass Criteria")[1].split("\n## ")[0]
    lines = [ln for ln in section.splitlines() if ln.startswith("- [ ] ")]
    assert lines, "keine Pass-Criteria gefunden — Überschrift umbenannt?"
    return lines


def _one(criteria: list[str], *needles: str) -> str:
    """Genau ein Kriterium, das alle Nadeln trägt."""
    hits = [ln for ln in criteria if all(n in ln for n in needles)]
    assert len(hits) == 1, (
        f"erwartet: genau ein Kriterium mit {needles}, gefunden: {len(hits)}"
    )
    return hits[0]


class TestDerDritteModusStehtUndMisstDenRequest:
    def test_der_modus_existiert(self, text: str):
        assert "### Modus 3: runtime_test" in text, (
            "Modus 3 fehlt. Ohne ihn liest ARCH-003 wieder nur die Antwort — "
            "und ein Server, der seine Vorschläge selbst absucht, besteht."
        )

    def test_gezaehlt_wird_auf_der_route_nicht_am_rueckgabewert(self, text: str):
        section = text.split("### Modus 3: runtime_test")[1].split("\n## ")[0]
        assert "call_count" in section, (
            "Der Zähler auf der Route ist der Prüfgegenstand. Ohne ihn misst "
            "der Modus wieder die Antwort."
        )
        assert re.search(r"sent\s*==|url\.params", section), (
            "Der Modus muss auch prüfen, WELCHER Begriff rausging — ein "
            "einzelner Request mit einem ersetzten Begriff bestünde sonst."
        )

    def test_der_mock_ist_gegen_drift_004_begruendet(self, text: str):
        """`DRIFT-004` warnt vor Mocks. Ohne die Abgrenzung liest sich dieser
        Modus wie ein Verstoss dagegen und wird beim nächsten Aufräumen
        gestrichen."""
        section = text.split("### Modus 3: runtime_test")[1].split("\n## ")[0]
        assert "DRIFT-004" in section

    def test_unbeobachtbare_abfragen_enden_in_todo_nicht_in_pass(self, text: str):
        section = text.split("### Modus 3: runtime_test")[1].split("\n## ")[0]
        assert "§2.6" in section and "`todo`" in section, (
            "Ein Server, dessen Abfragen kein Zähler erreicht, hat den Modus "
            "verhindert, nicht bestanden."
        )


class TestDasTestpaarWirdAlsPaarVerlangt:
    """Eine Hälfte allein liest sich wie Disziplin und ist keine."""

    def test_beide_haelften_stehen_im_modus(self, text: str):
        section = text.split("### Modus 3: runtime_test")[1].split("\n## ")[0]
        assert "Hälfte 1" in section and "Hälfte 2" in section

    def test_ein_kriterium_verlangt_das_paar_vollstaendig(self, criteria):
        _one(criteria, "Testpaar", "vollständig")

    def test_die_gegenprobe_ist_ein_eigenes_kriterium(self, criteria):
        """§2.6: Ein Modus, der nur am korrigierten Server grün wird, prüft die
        Fixture — nicht den Server."""
        hit = _one(criteria, "Gegenprobe")
        assert "angeschlagen" in hit


class TestDieRequestSeiteHatEigeneKriterien:
    def test_genau_ein_request_mit_unveraendertem_begriff(self, criteria):
        hit = _one(criteria, "genau ein", "unverändert")
        assert "Modus 3" in hit, (
            "Das Kriterium muss sagen, wo es erhoben wird — sonst wird es am "
            "Rückgabewert abgehakt, also an der Seite ohne den Fehler."
        )

    def test_vorschlaege_stammen_aus_der_eingabe(self, criteria):
        _one(criteria, "abgeleitet", "Korpus-Vokabular")

    def test_heuristische_treffer_stehen_in_einem_eigenen_feld(self, criteria):
        hit = _one(criteria, "eigenen", "Feld")
        assert "erzeugt" in hit, (
            "Ein eigenes Feld ohne den erzeugenden Begriff sagt DASS geraten "
            "wurde, nicht WELCHE Zeile zu welchem Begriff gehört."
        )

    def test_die_antwort_sagt_dass_nicht_verbreitert_wurde(self, criteria):
        _one(criteria, "verbreitert")


class TestDerCheckLehrtDieVermischungNichtMehr:
    """Pass-Pattern und Remediation sind Kopiervorlage — was dort steht, wird
    gebaut. Genau darüber ist der Belegfall entstanden."""

    @pytest.mark.parametrize(
        "path", sorted(CHECKS_DIR.glob("*.md")), ids=lambda p: p.stem
    )
    def test_kein_check_legt_fuzzy_treffer_in_die_ergebnisliste(self, path: Path):
        body = path.read_text(encoding="utf-8")
        assert not MIXING.search(body), (
            f"{path.name} zeigt heuristische Treffer unter `results`. Für das "
            "Modell ist eine so entstandene Zeile von einer echten nicht zu "
            "unterscheiden; `match_type` daneben liefert die Zuordnung nicht "
            "nach. Als entfernte Diff-Zeile (`-`) ist das Muster erlaubt."
        )

    @pytest.mark.parametrize(
        "path", sorted(CHECKS_DIR.glob("*.md")), ids=lambda p: p.stem
    )
    def test_kein_check_holt_vorschlaege_aus_einem_korpus(self, path: Path):
        body = path.read_text(encoding="utf-8")
        assert not CORPUS_SUGGESTIONS.search(body), (
            f"{path.name} holt Vorschläge über eine zweite Abfrage aus der "
            "Quelle. Vorschläge werden aus der Eingabe abgeleitet — sonst "
            "sind sie ein zweiter Treffertyp mit eigenem Recall-Risiko."
        )

    def test_die_mustersuche_greift_ueberhaupt(self):
        """Negative Kontrolle: Ohne sie bestünde die Prüfung oben auch dann,
        wenn das Muster nach einer Umformulierung nichts mehr trifft."""
        assert MIXING.search('        "results": fuzzy[:10],')
        assert MIXING.search('+     "results": fuzzy[:5],')
        assert not MIXING.search('-     "results": fuzzy[:5],')
        assert CORPUS_SUGGESTIONS.search(
            "    suggestions = await db.popular_terms_starting_with(q)"
        )


class TestDasEvidenzmassZiehtMit:
    def test_evidence_required_ist_auf_drei(self, text: str):
        """Mit 2 bliebe ein `pass` möglich, das die Request-Seite nie gesehen
        hat: Vorschlag da, `match_type` da, fertig. Der dritte Punkt ist der
        Zähler."""
        match = re.search(r"^evidence_required:\s*(\d+)$", text, re.M)
        assert match, "evidence_required fehlt in der Frontmatter"
        assert int(match.group(1)) == 3
