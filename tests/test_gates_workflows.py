"""Das generische Workflow-Gate unter `tools/gates/workflows.py` (G15).

Die einzige der sechzehn Familien, die nicht bloss zusammengelegt, sondern
ERWEITERT wurde. Die Herkunftsfassung durchsuchte den ganzen Baum und nahm
an, jede Erwaehnung einer `.yml` sei ein Verweis auf einen eigenen Workflow.
In einem Monorepo mit Katalog stimmt das nicht — gemessen waren vier von
sieben «Befunden» Beispiele aus dem Katalog, die fremde Repositories
beschreiben.

Gegenstand hier ist deshalb vor allem der SCOPE, dazu die drei Waechter ueber
die Ausnahmetabelle: Eine Ausnahmeliste veraltet genauso still wie das, wovor
sie ausnimmt.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.gates.workflows import (  # noqa: E402
    Retired,
    assert_mentions_resolve,
    collect_mentions,
    existing_workflows,
    in_scope,
    referenced_workflows_exist,
)
from tools.harness import CheckFailed  # noqa: E402

LINT = ".github/workflows/lint.yml"
ALT = ".github/workflows/catalogue-drift.yml"
NEU = ".github/workflows/weekly-drift.yml"


@pytest.fixture
def baum(tmp_path):
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / LINT).write_text("name: lint\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "Die CI steht in `.github/workflows/lint.yml`.\n", encoding="utf-8"
    )
    (tmp_path / "checks").mkdir()
    (tmp_path / "checks" / "OPS-001.md").write_text(
        "Der gepruefte Server soll `.github/workflows/live-test.yml` haben.\n",
        encoding="utf-8",
    )
    return tmp_path


# --------------------------------------------------------------------------
# Der Scope — die Erweiterung fuer das Monorepo
# --------------------------------------------------------------------------


def test_ANKER_der_katalog_bleibt_draussen_und_erzeugt_keinen_befund(baum):
    """Der gemessene Anlass fuer diese Erweiterung.

    `checks/OPS-001.md` nennt einen Workflow, den ein GEPRUEFTER SERVER haben
    soll. Ihn gegen den eigenen Baum zu halten ergaebe einen Befund, wo null
    Evidenz vorliegt.
    """
    assert referenced_workflows_exist(baum, scope=("README.md", ".github"))


def test_ANKER_derselbe_baum_mit_dem_katalog_im_scope_wird_rot(baum):
    """Die Gegenprobe — sonst waere nicht belegt, dass der Scope wirkt."""
    with pytest.raises(CheckFailed) as befund:
        referenced_workflows_exist(baum, scope=("README.md", ".github", "checks"))
    assert "live-test.yml" in str(befund.value)


def test_ANKER_ein_scope_eintrag_ohne_treffer_ist_ein_befund(baum):
    """Wer ein Verzeichnis umbenennt und den Scope nicht nachzieht, nimmt es
    stillschweigend aus der Pruefung."""
    with pytest.raises(CheckFailed) as befund:
        in_scope(baum, ("README.md", "gibtsnicht"))
    assert "gibtsnicht" in str(befund.value)


def test_ANKER_ein_leerer_scope_ist_ein_befund(baum):
    with pytest.raises(CheckFailed) as befund:
        in_scope(baum, ())
    assert "Kein Scope" in str(befund.value)


def test_ein_toter_verweis_im_scope_wird_gefangen(baum):
    (baum / "README.md").write_text(
        "Siehe `.github/workflows/weg.yml`.\n", encoding="utf-8"
    )
    with pytest.raises(CheckFailed) as befund:
        referenced_workflows_exist(baum, scope=("README.md", ".github"))
    assert "weg.yml" in str(befund.value)
    assert "README.md" in str(befund.value)


def test_die_erklaerende_datei_nennt_sich_nicht_selbst(baum):
    """Sonst erzeugte jeder RETIRED-Eintrag sofort seinen eigenen Befund."""
    (baum / "erklaerung.md").write_text(
        "hier steht `.github/workflows/weg.yml`\n", encoding="utf-8"
    )
    mentions = collect_mentions(
        baum,
        scope=("erklaerung.md",),
        vocabulary=existing_workflows(baum),
        declaring="erklaerung.md",
    )
    assert mentions == {}


def test_ein_blosser_dateiname_zaehlt_nur_aus_dem_vokabular(baum):
    """Sonst schluege jede `.pre-commit-config.yaml` in der Prosa an."""
    (baum / "README.md").write_text(
        "lint.yml faehrt die Gates, .pre-commit-config.yaml der Hook.\n",
        encoding="utf-8",
    )
    mentions = collect_mentions(
        baum,
        scope=("README.md",),
        vocabulary=existing_workflows(baum),
        declaring="x",
    )
    assert set(mentions) == {LINT}


# --------------------------------------------------------------------------
# Die drei Waechter ueber die Ausnahmetabelle
# --------------------------------------------------------------------------


def test_ein_historischer_verweis_ist_erlaubt():
    retired = {
        ALT: Retired(successor=NEU, since="1.8.0", historical_in=("CHANGELOG.md",))
    }
    assert assert_mentions_resolve({ALT: {"CHANGELOG.md"}}, {NEU}, retired=retired)


def test_ANKER_derselbe_verweis_woanders_ist_ein_toter_zeiger():
    """Die Ausnahme ist PRO DATEI und nicht pauschal.

    Eine pauschale haette den Anlassfall nicht gefangen — dort nannte ein
    Pruefmodul die alte Datei als LEBENDEN Zeiger.
    """
    retired = {
        ALT: Retired(successor=NEU, since="1.8.0", historical_in=("CHANGELOG.md",))
    }
    with pytest.raises(CheckFailed) as befund:
        assert_mentions_resolve({ALT: {"tools/x.py"}}, {NEU}, retired=retired)
    assert "LEBENDER Zeiger" in str(befund.value)
    assert NEU in str(befund.value)


def test_ANKER_ein_zurueckgezogener_pfad_der_wieder_existiert_ist_ein_fehler():
    """Der Eintrag naehme sonst einen LEBENDEN Workflow von der Pruefung aus."""
    retired = {ALT: Retired(successor=NEU, since="1.8.0", historical_in=())}
    with pytest.raises(CheckFailed) as befund:
        assert_mentions_resolve({ALT: {"CHANGELOG.md"}}, {ALT, NEU}, retired=retired)
    assert "gibt es im Baum aber wieder" in str(befund.value)


def test_ANKER_eine_ausnahme_ohne_gegenstand_ist_ein_befund():
    """Eine Ausnahme, die niemand braucht, verdeckt beim naechsten Mal eine,
    die jemand braucht."""
    retired = {
        ALT: Retired(
            successor=NEU, since="1.8.0", historical_in=("weg.md", "CHANGELOG.md")
        )
    }
    with pytest.raises(CheckFailed) as befund:
        assert_mentions_resolve({ALT: {"CHANGELOG.md"}}, {NEU}, retired=retired)
    assert "weg.md" in str(befund.value)


def test_ANKER_gar_keine_erwaehnung_ist_ein_befund():
    """Dann hat diese Pruefung nichts geprueft und meldete es als Erfolg."""
    with pytest.raises(CheckFailed) as befund:
        assert_mentions_resolve({}, {LINT}, retired={})
    assert "nichts geprueft" in str(befund.value)


def test_ein_fehlendes_workflow_verzeichnis_ist_ein_befund(tmp_path):
    with pytest.raises(CheckFailed) as befund:
        existing_workflows(tmp_path)
    assert ".github/workflows" in str(befund.value)


def test_die_gegenrichtung_ist_kein_befund(baum):
    """Ein Workflow, den niemand erwaehnt, ist in Ordnung.

    Ein Workflow muss nicht dokumentiert sein, um zu laufen — eine Pruefung,
    die das verlangt, erzwingt Prosa statt Korrektheit.
    """
    (baum / ".github/workflows/still.yml").write_text("name: still\n", encoding="utf-8")
    assert referenced_workflows_exist(baum, scope=("README.md", ".github"))
