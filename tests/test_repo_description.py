"""Tests für den Repo-Description-Guard.

Die Description ist der sechste Ort, an dem die Katalog-Zahlen stehen, und der
einzige ausserhalb des Repos. Genau deshalb ist er gedriftet: Während der
Katalog von 68 über 78 auf 85 Checks wuchs, stand dort unverändert
«68 Checks · 8 Kategorien».

Geprüft wird hier ausschliesslich die **reine** Seite — `compare()` und
`suggest()` bekommen den Description-String übergeben. Der Netzaufruf
(`fetch()`) wird bewusst *nicht* gemockt: Ein Mock bildete nur die eigene
Annahme über die GitHub-Antwort ab und könnte sie nie widerlegen — die Grenze,
an der `DRIFT-004` ansetzt. Was `fetch()` tut, prüft der Workflow im echten
Aufruf, nicht dieser Test.

Zwei Eigenschaften wiegen schwerer als die Einzelfälle und werden am härtesten
geprüft:

* eine **fehlende** Zahl ist ein Befund, nicht ein stilles Bestehen — sonst
  bestünde eine Description, die gar keine Zahlen nennt, immer;
* eine nicht erreichbare API endet mit Exit 1, nie mit «stimmt».
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tools.check_repo_description import compare, main, suggest

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKS_DIR = REPO_ROOT / "checks"

# Die reale Description zum Zeitpunkt, als der Guard entstand — mit exakt der
# Drift, die er fangen soll.
DRIFTED = (
    "Claude-Skill für systematische MCP-Server-Audits gegen einen kuratierten "
    "Best-Practice-Standards-Korpus · 68 Checks · 8 Kategorien · OAuth 2.1, OWASP, "
    "Lethal Trifecta, Schweiz-Compliance (DSG/ISDS) · MIT"
)


class TestCompare:
    def test_matching_description_has_no_problems(self):
        assert compare("… · 85 Checks · 11 Kategorien · …", 85, 11) == []

    def test_the_real_drift_is_caught(self):
        problems = compare(DRIFTED, 85, 11)
        assert len(problems) == 2
        assert any("68 Checks" in p for p in problems)
        assert any("8 Kategorien" in p for p in problems)

    def test_wrong_check_count_alone(self):
        problems = compare("· 80 Checks · 11 Kategorien ·", 85, 11)
        assert problems == ["Description nennt 80 Checks, Katalog hat 85"]

    def test_wrong_category_count_alone(self):
        problems = compare("· 85 Checks · 10 Kategorien ·", 85, 11)
        assert problems == ["Description nennt 10 Kategorien, Katalog hat 11"]

    def test_missing_numbers_are_a_finding_not_a_pass(self):
        """Sonst besteht jede Description, die die Zahlen einfach weglässt."""
        problems = compare("Ein Skill für MCP-Audits.", 85, 11)
        assert len(problems) == 2
        assert all("nennt keine" in p for p in problems)

    def test_repeated_numbers_are_all_checked(self):
        """Steht die Zahl zweimal drin, muss auch die zweite stimmen."""
        problems = compare("85 Checks … früher 68 Checks · 11 Kategorien", 85, 11)
        assert problems == ["Description nennt 68 Checks, Katalog hat 85"]


class TestSuggest:
    def test_only_the_numbers_change(self):
        fixed = suggest(DRIFTED, 85, 11)
        assert "85 Checks" in fixed
        assert "11 Kategorien" in fixed
        # Die Formulierung gehört der Autorin — sie darf nicht angefasst werden.
        assert "Lethal Trifecta, Schweiz-Compliance (DSG/ISDS) · MIT" in fixed
        assert fixed.startswith("Claude-Skill für systematische MCP-Server-Audits")

    def test_suggestion_satisfies_compare(self):
        assert compare(suggest(DRIFTED, 85, 11), 85, 11) == []


class TestCli:
    def _run(self, monkeypatch, argv):
        monkeypatch.setattr(sys, "argv", ["check_repo_description", *argv])
        return main()

    def test_matching_description_exits_zero(self, monkeypatch, capsys):
        from tools.parse_catalog import category_counts, parse_catalog

        catalog = parse_catalog(CHECKS_DIR)
        desc = f"· {len(catalog)} Checks · {len(category_counts(catalog))} Kategorien ·"
        code = self._run(monkeypatch, ["--description", desc])
        assert code == 0
        assert "Description OK" in capsys.readouterr().out

    def test_drifted_description_exits_one_and_suggests(self, monkeypatch, capsys):
        code = self._run(monkeypatch, ["--description", DRIFTED, "--repo", "o/r"])
        out = capsys.readouterr().out
        assert code == 1
        assert "DRIFT" in out
        assert "Vorschlag" in out

    def test_unreachable_api_is_not_a_pass(self, monkeypatch, capsys):
        """Ohne Antwort hat der Vergleich nicht stattgefunden."""
        import tools.check_repo_description as mod

        monkeypatch.setattr(mod, "fetch", lambda repo, timeout: (None, "simuliert"))
        code = self._run(monkeypatch, ["--repo", "o/r"])
        out = capsys.readouterr().out
        assert code == 1
        assert "UNKNOWN" in out
        assert "NICHT verglichen" in out
        assert "OK" not in out

    def test_neither_repo_nor_description_is_a_usage_error(self, monkeypatch):
        assert self._run(monkeypatch, []) == 2


class TestAgainstTheLiveCatalogue:
    """Der Guard muss die aktuell vorgeschlagene Description akzeptieren."""

    def test_current_recommended_description_passes(self):
        from tools.parse_catalog import category_counts, parse_catalog

        catalog = parse_catalog(CHECKS_DIR)
        recommended = suggest(DRIFTED, len(catalog), len(category_counts(catalog)))
        assert compare(recommended, len(catalog), len(category_counts(catalog))) == []


@pytest.mark.parametrize("n_checks,n_categories", [(85, 11), (90, 12), (7, 1)])
def test_compare_is_symmetric_in_its_inputs(n_checks, n_categories):
    """Der Guard hängt am übergebenen Katalog, nicht an fixen Zahlen."""
    good = f"{n_checks} Checks · {n_categories} Kategorien"
    assert compare(good, n_checks, n_categories) == []
    assert compare(good, n_checks + 1, n_categories) != []
