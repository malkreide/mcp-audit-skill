"""Die zweite Anwendbarkeits-Achse: `spec_baseline` gegen `mcp_spec_version`.

Während der Migrationswellen A–D stehen im Portfolio zwei Protokollstände
gleichzeitig. Ein Check, der gegen den falschen misst, ist nicht bloss
nutzlos — er ist ein Befund über eine Eigenschaft, die es beim geprüften
Server nicht gibt, und er verdrängt den Check, der die richtige Frage
gestellt hätte.

Drei Fehlerklassen werden hier festgehalten, und alle drei sind still:

1. **Ein Tippfehler in `spec_baseline`.** `2026-07-27` ist ein gewöhnlicher
   String. Ohne harten Fehler beim Parsen fällt der Check aus jedem Audit
   heraus und meldet das niemandem — dieselbe Klasse wie eine stille
   Demotion nach `advisory`.

2. **Ein Profil ohne `mcp_spec_version`.** Dann ist für jeden
   baseline-tragenden Check unbekannt, ob er gilt. Das darf nicht als
   «nicht anwendbar» durchgehen: nicht anwendbar heisst «geprüft und
   ausgeschlossen», hier wurde nichts geprüft. §2.6.

3. **Eine stille Reduktion der Katalogmenge.** Eine Migration bewegt
   vierzehn Checks hinein und fünf hinaus. Ohne Bericht sieht das aus wie
   ein sauberer Lauf über einen kleineren Katalog — der Fehler aus
   `OPS-005`.

Jede Prüfung hier hat eine Gegenprobe: Sie muss bei entferntem Mechanismus
fallen. Ein Test, der nur die grüne Richtung kennt, belegt nichts (§4.1).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tools.eval_applicability import (
    DEFAULT_SPEC_BASELINE,
    REASON_BASELINE_MISMATCH,
    REASON_BASELINE_UNRESOLVED,
    VALID_SPEC_BASELINES,
    baseline_applies,
    baseline_summary,
    evaluate_catalog,
)
from tools.parse_catalog import ids_for_baseline, parse_catalog, spec_baseline_counts
from tools.validate_profile import ALLOWED_VALUES, REQUIRED_FIELDS, validate_profile

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKS_DIR = REPO_ROOT / "checks"


def _profile(version: str | None = "2025-11-25") -> dict[str, Any]:
    p: dict[str, Any] = {
        "transport": "dual",
        "sdk_language": "Python",
        "auth_model": "none",
        "data_class": "Public Open Data",
        "write_capable": False,
        "deployment": ["local-stdio", "Railway"],
        "is_cloud_deployed": True,
        "uses_sampling": False,
        "uses_sequential_thinking": False,
        "tools_include_filesystem": False,
        "tools_make_external_requests": True,
        "stadt_zuerich_context": True,
        "schulamt_context": False,
        "volksschule_context": False,
        "enterprise_context": False,
        "data_source": {"is_swiss_open_data": True},
    }
    if version is not None:
        p["mcp_spec_version"] = version
    return p


# ---------------------------------------------------------------------------
# baseline_applies — die Entscheidung selbst
# ---------------------------------------------------------------------------


class TestBaselineApplies:
    @pytest.mark.parametrize("version", ["2025-11-25", "2026-07-28"])
    def test_beide_applies_to_every_revision(self, version: str):
        applies, reason = baseline_applies("beide", version)
        assert applies is True
        assert reason == ""

    def test_beide_applies_even_without_a_profile_version(self):
        # Nichts an einem `beide`-Check hängt an der Antwort, also ist ein
        # fehlender Wert hier kein offener Punkt. Andernfalls stünde jeder
        # Bestandscheck des Katalogs unter Vorbehalt.
        applies, reason = baseline_applies("beide", None)
        assert applies is True
        assert reason == ""

    def test_matching_revision_applies(self):
        assert baseline_applies("2026-07-28", "2026-07-28") == (True, "")

    def test_other_revision_is_a_mismatch_not_an_error(self):
        applies, reason = baseline_applies("2026-07-28", "2025-11-25")
        assert applies is False
        assert reason.startswith(REASON_BASELINE_MISMATCH)
        # Die Meldung muss beide Seiten nennen, sonst ist im Report nicht zu
        # sehen, welcher Stand welchen verdrängt hat.
        assert "2026-07-28" in reason and "2025-11-25" in reason

    @pytest.mark.parametrize("missing", [None, "", "   "])
    def test_missing_profile_version_is_unresolved_not_mismatch(self, missing):
        applies, reason = baseline_applies("2026-07-28", missing)
        assert applies is False
        assert reason.startswith(REASON_BASELINE_UNRESOLVED)
        # Und ausdrücklich NICHT der andere Ausgang: «nicht anwendbar» wäre
        # eine Aussage, «nicht gefragt» ist keine.
        assert not reason.startswith(REASON_BASELINE_MISMATCH)

    def test_an_invalid_check_baseline_is_unresolved(self):
        applies, reason = baseline_applies("2026-07-27", "2026-07-28")
        assert applies is False
        assert reason.startswith(REASON_BASELINE_UNRESOLVED)


# ---------------------------------------------------------------------------
# Katalog-Parsing — der Tippfehler darf nicht durchkommen
# ---------------------------------------------------------------------------


class TestCatalogParsing:
    def test_typo_in_spec_baseline_is_a_hard_error(self, tmp_path: Path):
        (tmp_path / "X-001.md").write_text(
            '---\nid: X-001\ntitle: "t"\ncategory: X\nseverity: high\n'
            "applies_when: 'always'\nspec_baseline: 2026-07-27\n---\n# X-001\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="invalid spec_baseline"):
            parse_catalog(tmp_path)

    def test_a_missing_field_defaults_to_beide(self, tmp_path: Path):
        # Die sichere Richtung: ein Check ohne Angabe feuert weiter für jedes
        # Profil. Verengung ist eine ausdrückliche Handlung.
        (tmp_path / "X-001.md").write_text(
            '---\nid: X-001\ntitle: "t"\ncategory: X\nseverity: high\n'
            "applies_when: 'always'\n---\n# X-001\n",
            encoding="utf-8",
        )
        assert (
            parse_catalog(tmp_path)["X-001"]["spec_baseline"] == DEFAULT_SPEC_BASELINE
        )

    def test_every_real_check_carries_a_valid_baseline(self):
        for cid, fm in parse_catalog(CHECKS_DIR).items():
            assert fm["spec_baseline"] in VALID_SPEC_BASELINES, cid

    def test_counts_cover_the_whole_catalogue(self):
        catalog = parse_catalog(CHECKS_DIR)
        counts = spec_baseline_counts(catalog)
        assert set(counts) == set(VALID_SPEC_BASELINES), "alle Schlüssel immer da"
        assert sum(counts.values()) == len(catalog)

    def test_both_revisions_are_actually_represented(self):
        # Ein Katalog, in dem eine Seite leer ist, macht jede
        # Baseline-Prüfung darunter zur Tautologie.
        catalog = parse_catalog(CHECKS_DIR)
        assert ids_for_baseline(catalog, "2025-11-25"), "keine Alt-Baseline-Checks"
        assert ids_for_baseline(catalog, "2026-07-28"), "keine Neu-Baseline-Checks"

    def test_narrowed_checks_are_exactly_the_documented_five(self):
        # Diese fünf messen einen Prüfgegenstand, den `2026-07-28` entfernt
        # hat. Wächst die Menge, ist das eine Katalogentscheidung mit
        # CHANGELOG-Eintrag und kein Diff nebenbei.
        assert ids_for_baseline(parse_catalog(CHECKS_DIR), "2025-11-25") == [
            "SCALE-002",
            "SCALE-003",
            "SCALE-007",
            "SDK-004",
            "SEC-009",
        ]

    def test_every_narrowed_check_names_its_successor(self):
        # Ein Check, der für einen migrierten Server ausfällt, muss sagen, wo
        # die Frage jetzt gestellt wird. Sonst verschwindet sie mit ihm.
        catalog = parse_catalog(CHECKS_DIR)
        for cid in ids_for_baseline(catalog, "2025-11-25"):
            text = (CHECKS_DIR / f"{cid}.md").read_text(encoding="utf-8")
            assert "Nachfolger:" in text, f"{cid} nennt keinen Nachfolger"


# ---------------------------------------------------------------------------
# Profil-Schema
# ---------------------------------------------------------------------------


class TestProfileSchema:
    def test_mcp_spec_version_is_required(self):
        assert REQUIRED_FIELDS.get("mcp_spec_version") is str

    def test_a_profile_without_it_fails_validation(self):
        report = validate_profile(_profile(version=None))
        assert report["consistent"] is False
        assert "mcp_spec_version" in report["missing"]

    def test_the_vocabulary_is_closed(self):
        assert ALLOWED_VALUES["mcp_spec_version"] == ("2025-11-25", "2026-07-28")

    @pytest.mark.parametrize("version", ["2025-11-25", "2026-07-28"])
    def test_both_revisions_validate(self, version: str):
        assert validate_profile(_profile(version))["consistent"] is True

    @pytest.mark.parametrize("bad", ["2026-07", "latest", "2026-07-28-draft", "beide"])
    def test_a_spelling_nobody_compares_against_is_rejected(self, bad: str):
        """Die Lehre aus `transport: HTTP`, eine Achse weiter.

        Ein unbekannter *Wert* ist ein gewöhnlicher String — der Evaluator
        wirft dafür nichts. Er lässt nur jeden baseline-tragenden Check als
        `baseline-mismatch` durchfallen, und der Report meldet einen sauberen
        Lauf über einen halbierten Katalog.

        `beide` steht bewusst mit auf dieser Liste: Es ist eine Antwort, die
        ein *Check* geben darf, nie ein Server.
        """
        report = validate_profile(_profile(bad))
        assert report["consistent"] is False
        assert any(m["field"] == "mcp_spec_version" for m in report["enum_mismatch"])


# ---------------------------------------------------------------------------
# Der Gate im Zusammenspiel mit dem echten Katalog
# ---------------------------------------------------------------------------


class TestAgainstTheRealCatalog:
    def test_migrated_profile_gains_the_new_checks(self):
        old = evaluate_catalog(_profile("2025-11-25"), CHECKS_DIR)
        new = evaluate_catalog(_profile("2026-07-28"), CHECKS_DIR)

        gained = {c for c, r in new.items() if r["applicable"]} - {
            c for c, r in old.items() if r["applicable"]
        }
        lost = {c for c, r in old.items() if r["applicable"]} - {
            c for c, r in new.items() if r["applicable"]
        }

        assert gained, "Migration bringt keine neuen Checks — Gate greift nicht"
        assert lost, "Migration entfernt keine Checks — Gate greift nicht"
        # Die verlorenen sind genau die verengten, soweit sie fürs Profil galten
        assert lost <= set(ids_for_baseline(parse_catalog(CHECKS_DIR), "2025-11-25"))

    def test_a_profile_without_the_field_leaves_checks_unresolved(self):
        """Der teuerste Ausgang, und der Grund für den eigenen Reason-Wert.

        Ohne `mcp_spec_version` ist für jeden baseline-tragenden Check offen,
        ob er gilt. Fiele das mit `no-match` zusammen, sähe ein Profil mit
        vergessenem Feld exakt aus wie ein sauberer Lauf.
        """
        results = evaluate_catalog(_profile(version=None), CHECKS_DIR)
        summary = baseline_summary(results)
        assert summary["unresolved"] > 0
        assert summary["dropped_by_baseline"] == 0, (
            "Ohne Profilangabe gibt es keinen Mismatch — nur Unklarheit. "
            "Beides zu vermischen wäre der Fehler, den dieser Test verhindert."
        )
        # Gegenprobe: mit gesetztem Feld verschwindet die Unklarheit
        assert (
            baseline_summary(evaluate_catalog(_profile(), CHECKS_DIR))["unresolved"]
            == 0
        )

    def test_summary_ids_and_counts_agree(self):
        summary = baseline_summary(evaluate_catalog(_profile(), CHECKS_DIR))
        assert summary["dropped_by_baseline"] == len(summary["dropped_ids"])
        assert summary["unresolved"] == len(summary["unresolved_ids"])

    def test_no_check_folds_the_baseline_into_applies_when(self):
        """Die zwei Achsen bleiben getrennt.

        `mcp_spec_version` in einer `applies_when`-Klausel würde funktionieren
        — und den Unterschied einebnen, den die getrennte Stufe herstellt: im
        Report läse sich ein Baseline-Ausfall dann als gewöhnliches
        `no-match`, ununterscheidbar von einem Profil-Ausfall.
        """
        offenders = [
            cid
            for cid, fm in parse_catalog(CHECKS_DIR).items()
            if "mcp_spec_version" in str(fm.get("applies_when", ""))
        ]
        assert offenders == [], (
            f"{offenders} prüfen die Baseline über `applies_when`. Dafür gibt "
            "es `spec_baseline` — sonst ist im Applicability-Report nicht mehr "
            "zu sehen, ob das Profil oder der Protokollstand den Check "
            "verdrängt hat."
        )
