# -*- coding: utf-8 -*-
"""Tests für tools/verify_inventory.py — das Inventar-Gate.

Der tragende Test ist `test_nested_unlisted_server_is_a_hard_failure`: Er
bildet den realen Fall nach, aus dem das Gate entstanden ist —
`openparldata-mcp` lag verschachtelt im Repo `parlament-mcp`, mit eigener
`pyproject.toml`, und ist durch jede Aufzählung gefallen, die Top-Level-
Repos listet. Dadurch war er der letzte Server im Portfolio auf dem alten
SDK-Major.

Alle anderen Tests halten die Ränder fest, an denen ein Gate dieser Art
üblicherweise scheitert: entweder es meldet zu viel und wird abgeschaltet,
oder es meldet zu wenig und ist Dekoration.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.verify_inventory import (
    VENDOR_DIRS,
    find_manifests,
    main,
    verify_inventory,
)


REPO_URL = "https://github.com/malkreide/parlament-mcp"


def _manifest(path: Path, name: str = "pyproject.toml") -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / name).write_text('[project]\nname = "x"\n', encoding="utf-8")


@pytest.fixture
def portfolio() -> dict:
    """Eine Liste, die nur das Eltern-Repo kennt."""
    return {
        "servers": [
            {"name": "parlament-mcp", "repo": REPO_URL, "profile": {}},
        ]
    }


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    """Ein Checkout mit Wurzel-Manifest — der unauffällige Normalfall."""
    root = tmp_path / "work"
    _manifest(root / "parlament-mcp")
    return root


# ---------------------------------------------------------------------------
# Der Fall, für den das Gate existiert
# ---------------------------------------------------------------------------


class TestNestedServer:
    def test_nested_unlisted_server_is_a_hard_failure(self, portfolio, checkout):
        """openparldata-mcp, nachgebaut.

        Ein zweites Manifest in einem Unterverzeichnis, das in keinem
        Listeneintrag vorkommt. Genau das ist über Monate niemandem
        aufgefallen.
        """
        _manifest(checkout / "parlament-mcp" / "openparldata-mcp")

        report = verify_inventory(portfolio, checkout)

        assert report["consistent"] is False
        assert report["unlisted"] == [
            {
                "server": "parlament-mcp",
                "path": "openparldata-mcp",
                "manifest": "openparldata-mcp/pyproject.toml",
            }
        ]

    def test_listing_it_with_a_path_resolves_the_finding(self, portfolio, checkout):
        """Der vorgesehene Weg: eigener Eintrag mit `path:`.

        Beide Einträge teilen sich die Repo-URL — der verschachtelte Server
        liegt im selben Checkout, nur woanders.
        """
        _manifest(checkout / "parlament-mcp" / "openparldata-mcp")
        portfolio["servers"].append(
            {
                "name": "openparldata-mcp",
                "repo": REPO_URL,
                "path": "openparldata-mcp",
                "profile": {},
            }
        )

        report = verify_inventory(portfolio, checkout, skip_missing=True)

        assert report["unlisted"] == []
        parent = next(s for s in report["servers"] if s["name"] == "parlament-mcp")
        assert sorted(parent["known"]) == [
            "openparldata-mcp/pyproject.toml",
            "pyproject.toml",
        ]

    def test_a_second_entry_without_path_does_not_cover_it(self, portfolio, checkout):
        """Ein Eintrag allein genügt nicht — der Pfad muss stimmen.

        Sonst würde jeder zusätzliche Eintrag auf dasselbe Repo beliebige
        verschachtelte Manifeste stillschweigend legitimieren.
        """
        _manifest(checkout / "parlament-mcp" / "openparldata-mcp")
        portfolio["servers"].append(
            {
                "name": "openparldata-mcp",
                "repo": REPO_URL,
                "path": "something-else",
                "profile": {},
            }
        )

        assert verify_inventory(portfolio, checkout, skip_missing=True)["unlisted"]


# ---------------------------------------------------------------------------
# Falsch-Positive: was ohne Deklaration übersprungen wird — und was nicht
# ---------------------------------------------------------------------------


class TestFalsePositives:
    @pytest.mark.parametrize("vendor", ["node_modules", ".venv", "__pycache__", ".tox"])
    def test_vendor_directories_need_no_declaration(self, portfolio, checkout, vendor):
        """Dort liegt kein von Hand geschriebener, versionierter Server."""
        _manifest(checkout / "parlament-mcp" / vendor / "somepkg")
        assert verify_inventory(portfolio, checkout)["consistent"] is True

    def test_egg_info_is_treated_as_vendor(self, portfolio, checkout):
        _manifest(checkout / "parlament-mcp" / "src" / "thing.egg-info")
        assert verify_inventory(portfolio, checkout)["consistent"] is True

    def test_fixtures_and_examples_are_NOT_guessed(self, portfolio, checkout):
        """Bewusst kein Heuristik-Freifahrtschein.

        Eine Regel, die «examples/» pauschal für harmlos hält, hätte
        `openparldata-mcp` genauso übersehen wie die Handliste. Wer weiss,
        dass es kein Server ist, schreibt es hin.
        """
        _manifest(checkout / "parlament-mcp" / "examples" / "demo")
        _manifest(checkout / "parlament-mcp" / "tests" / "fixtures" / "sample")

        report = verify_inventory(portfolio, checkout)

        assert report["consistent"] is False
        assert {u["path"] for u in report["unlisted"]} == {
            "examples/demo",
            "tests/fixtures/sample",
        }

    def test_declared_ignore_silences_them(self, portfolio, checkout):
        _manifest(checkout / "parlament-mcp" / "examples" / "demo")
        _manifest(checkout / "parlament-mcp" / "tests" / "fixtures" / "sample")
        portfolio["servers"][0]["ignore"] = ["examples", "tests/fixtures/*"]

        report = verify_inventory(portfolio, checkout)

        assert report["consistent"] is True
        assert len(report["servers"][0]["ignored"]) == 2

    def test_global_ignore_applies_to_every_server(self, portfolio, checkout):
        _manifest(checkout / "parlament-mcp" / "examples" / "demo")
        portfolio["ignore"] = ["examples"]
        assert verify_inventory(portfolio, checkout)["consistent"] is True

    def test_ignored_paths_are_reported_not_swallowed(self, portfolio, checkout):
        """Still Übersprungenes wäre dieselbe Fehlerklasse in neuer Verpackung.

        Wer den Report liest, muss sehen können, was das Gate nicht
        angeschaut hat — sonst sieht «nicht geprüft» aus wie «bestanden»
        (`OPS-005`).
        """
        _manifest(checkout / "parlament-mcp" / "examples" / "demo")
        portfolio["servers"][0]["ignore"] = ["examples"]

        entry = verify_inventory(portfolio, checkout)["servers"][0]

        assert entry["ignored"] == [
            {"path": "examples/demo/pyproject.toml", "pattern": "examples"}
        ]


# ---------------------------------------------------------------------------
# Nicht geprüft ist nicht bestanden
# ---------------------------------------------------------------------------


class TestMissingCheckout:
    def test_missing_checkout_fails_by_default(self, portfolio, tmp_path):
        report = verify_inventory(portfolio, tmp_path / "empty")
        assert report["consistent"] is False
        assert report["unverified"] == ["parlament-mcp"]
        assert report["servers"][0]["status"] == "unverified"

    def test_skip_missing_downgrades_it(self, portfolio, tmp_path):
        report = verify_inventory(portfolio, tmp_path / "empty", skip_missing=True)
        assert report["consistent"] is True
        assert report["unverified"] == ["parlament-mcp"]

    def test_skip_missing_does_not_hide_real_drift(self, portfolio, checkout):
        """Die Abkürzung darf nur fehlende Checkouts betreffen."""
        _manifest(checkout / "parlament-mcp" / "openparldata-mcp")
        portfolio["servers"].append(
            {"name": "not-cloned", "repo": "https://example.com/x", "profile": {}}
        )
        assert (
            verify_inventory(portfolio, checkout, skip_missing=True)["consistent"]
            is False
        )


# ---------------------------------------------------------------------------
# Manifest-Suche
# ---------------------------------------------------------------------------


class TestFindManifests:
    def test_finds_both_manifest_kinds(self, tmp_path):
        _manifest(tmp_path, "pyproject.toml")
        _manifest(tmp_path / "node-server", "package.json")
        assert [str(p).replace("\\", "/") for p in find_manifests(tmp_path)] == [
            "pyproject.toml",
            "node-server/package.json",
        ]

    def test_vendor_set_is_not_empty(self):
        """Gegenprobe gegen eine leergeräumte Liste.

        Wäre VENDOR_DIRS leer, meldete das Gate jedes `node_modules`-Paket
        und würde binnen einer Woche abgeschaltet.
        """
        assert "node_modules" in VENDOR_DIRS and ".venv" in VENDOR_DIRS


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestCli:
    def _write(self, tmp_path: Path, portfolio: dict) -> Path:
        import yaml

        path = tmp_path / "portfolio.yaml"
        path.write_text(yaml.safe_dump(portfolio), encoding="utf-8")
        return path

    def test_clean_returns_zero(self, tmp_path, portfolio, checkout, capsys):
        path = self._write(tmp_path, portfolio)
        rc = main(["--portfolio", str(path), "--work-dir", str(checkout)])
        assert rc == 0
        assert "✓" in capsys.readouterr().out

    def test_drift_returns_one_and_names_the_file(
        self, tmp_path, portfolio, checkout, capsys
    ):
        _manifest(checkout / "parlament-mcp" / "openparldata-mcp")
        path = self._write(tmp_path, portfolio)
        rc = main(["--portfolio", str(path), "--work-dir", str(checkout)])
        assert rc == 1
        out = capsys.readouterr().out
        assert "openparldata-mcp/pyproject.toml" in out
        # Die Begründung muss im Output stehen, nicht nur im Quelltext —
        # sonst liest sich der Fehlschlag wie Schikane und das Gate fliegt raus.
        assert "openparldata-mcp lag" in out

    def test_json_format(self, tmp_path, portfolio, checkout, capsys):
        _manifest(checkout / "parlament-mcp" / "openparldata-mcp")
        path = self._write(tmp_path, portfolio)
        rc = main(
            [
                "--portfolio",
                str(path),
                "--work-dir",
                str(checkout),
                "--format",
                "json",
            ]
        )
        assert rc == 1
        data = json.loads(capsys.readouterr().out)
        assert data["consistent"] is False
        assert data["unlisted"][0]["server"] == "parlament-mcp"

    def test_missing_portfolio_returns_two(self, tmp_path):
        assert main(["--portfolio", str(tmp_path / "nope.yaml")]) == 2

    def test_writes_out_file(self, tmp_path, portfolio, checkout):
        path = self._write(tmp_path, portfolio)
        out = tmp_path / "report.json"
        rc = main(
            [
                "--portfolio",
                str(path),
                "--work-dir",
                str(checkout),
                "--format",
                "json",
                "--out",
                str(out),
            ]
        )
        assert rc == 0
        assert json.loads(out.read_text(encoding="utf-8"))["consistent"] is True


# ---------------------------------------------------------------------------
# Das mitgelieferte Beispielprofil muss durchlaufen
# ---------------------------------------------------------------------------


def test_example_portfolio_has_no_checkouts_and_says_so(tmp_path):
    """`portfolio.example.yaml` ohne Checkouts ist «nicht geprüft», nicht «ok».

    Hält fest, dass das Gate den Unterschied macht, statt eine leere
    Umgebung als sauberes Portfolio zu melden.
    """
    import yaml

    repo_root = Path(__file__).resolve().parent.parent
    example = yaml.safe_load(
        (repo_root / "portfolio.example.yaml").read_text(encoding="utf-8")
    )

    report = verify_inventory(example, tmp_path / "nothing-here")

    assert report["consistent"] is False
    assert len(report["unverified"]) == len(example["servers"])


def test_real_run_shape_two_checkouts_same_repo(tmp_path):
    """Wie es nach einem echten `audit-portfolio.sh`-Lauf aussieht.

    Das Skript klont pro `name`, ein verschachtelter Server bekommt also
    einen eigenen Vollklon desselben Repos. Beide Checkouts enthalten dann
    beide Manifeste — und beide müssen sauber durchlaufen, weil die
    deklarierten Pfade pro Repo-URL gruppiert werden.

    Ohne diese Gruppierung meldete das Gate den Eltern-Checkout als Drift,
    obwohl der verschachtelte Server ordentlich gelistet ist — und wäre
    binnen einer Woche abgeschaltet.
    """
    work = tmp_path / "work"
    for name in ("parlament-mcp", "openparldata-mcp"):
        _manifest(work / name)
        _manifest(work / name / "openparldata-mcp")

    portfolio = {
        "servers": [
            {"name": "parlament-mcp", "repo": REPO_URL, "profile": {}},
            {
                "name": "openparldata-mcp",
                "repo": REPO_URL,
                "path": "openparldata-mcp",
                "profile": {},
            },
        ]
    }

    report = verify_inventory(portfolio, work)

    assert report["consistent"] is True
    assert [s["status"] for s in report["servers"]] == ["ok", "ok"]
