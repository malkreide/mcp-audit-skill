"""Tests for audit-notion-sync.py — only the pure profile-builder logic.

Network-dependent code paths (Notion HTTP) are out of scope for this
suite; they're integration-tested manually via the `health` subcommand.

The build_profile derivation got more complex in issue #16 (added
is_cloud_deployed), so a small unit test guards against drift.
"""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_sync_module():
    """audit-notion-sync.py uses a hyphen in its filename, so we load it
    via importlib instead of `import audit_notion_sync`.
    """
    spec = importlib.util.spec_from_file_location(
        "audit_notion_sync",
        REPO_ROOT / "audit-notion-sync.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def sync_mod():
    return _load_sync_module()


def _props(
    transport="dual",
    auth="none",
    data_class="Public Open Data",
    write="read-only",
    deployment=("local-stdio",),
    org=(),
    spec_version="2025-11-25",
    sdk_language="Python",
):
    """Build a minimal Notion-shape props dict the builder expects."""

    def select(value):
        return {"select": {"name": value}} if value else {"select": None}

    def multi_select(values):
        return {"multi_select": [{"name": v} for v in values]}

    return {
        "Transport": select(transport),
        "Auth-Modell": select(auth),
        "Datenklasse": select(data_class),
        "Schreibzugriff": select(write),
        "Deployment": multi_select(deployment),
        "Org-Kontext": multi_select(org),
        "MCP-Spec-Version": select(spec_version),
        "SDK-Sprache": select(sdk_language),
    }


def _page(name="srgssr-mcp", repo="https://github.com/malkreide/srgssr-mcp", **kw):
    props = _props(**kw)
    props["Server Name"] = {"title": [{"plain_text": name}]}
    props["Repo URL"] = {"url": repo}
    props["Audit-Status"] = {"select": {"name": "Triagiert"}}
    return {"id": "page-1", "properties": props}


class TestIsCloudDeployedDerivation:
    """Issue #16: the sync derives `is_cloud_deployed` from the
    `deployment` multi_select.
    """

    def test_local_stdio_only_is_false(self, sync_mod):
        profile = sync_mod.build_profile(_props(deployment=("local-stdio",)))
        assert profile["is_cloud_deployed"] is False

    def test_railway_only_is_true(self, sync_mod):
        profile = sync_mod.build_profile(_props(deployment=("Railway",)))
        assert profile["is_cloud_deployed"] is True

    def test_local_plus_cloud_is_true(self, sync_mod):
        profile = sync_mod.build_profile(
            _props(deployment=("local-stdio", "Railway")),
        )
        assert profile["is_cloud_deployed"] is True

    def test_docker_counts_as_cloud(self, sync_mod):
        # Docker is non-local for the purposes of the cloud-deploy gate.
        profile = sync_mod.build_profile(_props(deployment=("Docker",)))
        assert profile["is_cloud_deployed"] is True

    def test_empty_deployment_defaults_to_local(self, sync_mod):
        # Empty multi_select → defaults to ["local-stdio"] in build_profile.
        profile = sync_mod.build_profile(_props(deployment=()))
        assert profile["deployment"] == ["local-stdio"]
        assert profile["is_cloud_deployed"] is False


class TestProfileShape:
    def test_required_fields_present(self, sync_mod):
        profile = sync_mod.build_profile(_props())
        for field in (
            "transport",
            "auth_model",
            "data_class",
            "write_capable",
            "deployment",
            "is_cloud_deployed",
            "uses_sampling",
            "tools_make_external_requests",
            "data_source",
        ):
            assert field in profile, f"missing field {field}"

    def test_write_capable_derived_from_schreibzugriff(self, sync_mod):
        ro = sync_mod.build_profile(_props(write="read-only"))
        wr = sync_mod.build_profile(_props(write="write-capable"))
        assert ro["write_capable"] is False
        assert wr["write_capable"] is True


class TestSpecVersionIsCarriedAndItsAbsenceIsRecorded:
    """`mcp_spec_version` decides which half of the catalogue runs.

    Two failure modes, both silent, and the second is the one that bit
    `sdk_language` before v1.3.1: the column exists in the schema, so
    `cmd_health` reports it present — and the individual cell is empty, so
    every read falls back to the default anyway. A schema check cannot see
    that; only the row can.
    """

    def test_the_value_reaches_the_profile(self, sync_mod):
        profile = sync_mod.build_profile(_props(spec_version="2026-07-28"))
        assert profile["mcp_spec_version"] == "2026-07-28"

    def test_an_empty_cell_leaves_the_key_out(self, sync_mod):
        # SKILL.md §1.1: das Feld «hat bewusst keinen Default». Hier stand
        # trotzdem `2025-11-25` — begruendet als die konservative Richtung.
        # Konservativ ist sie nur, solange niemand migriert ist; danach misst
        # sie einen migrierten Server gegen die Haelfte, die sein Protokoll
        # nicht mehr hat. Kein Wert heisst deshalb kein Schluessel.
        profile = sync_mod.build_profile(_props(spec_version=None))
        assert "mcp_spec_version" not in profile

    def test_the_missing_key_is_loud_downstream(self, sync_mod):
        # Die Gegenprobe zum Weglassen: Ein fehlender Schluessel darf nicht
        # bequemer sein als ein falscher. `validate_profile` muss ihn melden.
        from tools.validate_profile import validate_profile

        report = validate_profile(sync_mod.build_profile(_props(spec_version=None)))
        assert report["consistent"] is False
        assert "mcp_spec_version" in report["missing"]

    def test_baseline_applies_calls_it_unresolved_not_mismatched(self, sync_mod):
        # Und die zweite Haelfte derselben Zusage: «nicht gefragt» darf nicht
        # wie «passt nicht» aussehen — §2.6, eine Ebene hoeher.
        from tools.eval_applicability import (
            REASON_BASELINE_UNRESOLVED,
            baseline_applies,
        )

        profile = sync_mod.build_profile(_props(spec_version=None))
        applies, reason = baseline_applies(
            "2026-07-28", profile.get("mcp_spec_version")
        )
        assert applies is False
        assert reason.startswith(REASON_BASELINE_UNRESOLVED)

    def test_the_fallback_is_recorded_not_swallowed(self, sync_mod):
        entry = sync_mod.build_server_entry(_page(spec_version=None))
        assert "MCP-Spec-Version" in entry["_defaulted"]

    def test_a_filled_cell_records_nothing(self, sync_mod):
        entry = sync_mod.build_server_entry(_page(spec_version="2026-07-28"))
        assert "MCP-Spec-Version" not in entry["_defaulted"]

    def test_sdk_language_is_tracked_the_same_way(self, sync_mod):
        assert (
            "SDK-Sprache"
            in sync_mod.build_server_entry(_page(sdk_language=None))["_defaulted"]
        )

    def test_the_marker_never_reaches_the_yaml(self, sync_mod):
        # `_defaulted` is bookkeeping for the operator, not profile data. A
        # leak would put an unknown key into every profile and `applies_when`
        # would raise UnknownFieldError on the next audit.
        text = sync_mod.emit_portfolio_yaml([sync_mod.build_server_entry(_page())])
        assert "_defaulted" not in text
        assert "mcp_spec_version: 2025-11-25" in text

    def test_the_written_profile_passes_the_validator(self, sync_mod):
        # The end-to-end claim: what `pull` writes is what `validate_profile`
        # accepts. Without this the two schemas drift apart and the failure
        # only shows up mid-audit.
        from tools.validate_profile import validate_profile

        profile = sync_mod.build_profile(_props(spec_version="2026-07-28"))
        report = validate_profile(profile)
        assert report["consistent"] is True, report


class TestPullStopsInsteadOfGuessing:
    """Der Abbruch muss VOR dem Schreiben liegen, sonst ist er folgenlos.

    Die alte Fassung warnte — korrekt formuliert, und zu spaet: Die Datei war
    geschrieben, sie validiert sauber, und das Audit danach lief ueber die
    geratene Katalog-Haelfte. In einem Batch-Pull ueber vierzig Zeilen ist eine
    stderr-Zeile das, was man scrollt. Deshalb pruefen diese Tests nicht den
    Text der Meldung, sondern ob die Datei existiert.
    """

    @staticmethod
    def _harness(monkeypatch, sync_mod, tmp_path, pages):
        monkeypatch.setattr(sync_mod, "get_token", lambda: "t")
        monkeypatch.setattr(sync_mod, "get_db_id", lambda: "db")
        monkeypatch.setattr(sync_mod, "query_database", lambda *a, **k: pages)
        out = tmp_path / "portfolio.yaml"
        args = argparse.Namespace(output=str(out), force=True, all=True)
        return out, args

    def test_a_row_without_the_column_stops_the_run(
        self, sync_mod, monkeypatch, tmp_path
    ):
        out, args = self._harness(
            monkeypatch, sync_mod, tmp_path, [_page(spec_version=None)]
        )
        with pytest.raises(SystemExit) as exc:
            sync_mod.cmd_pull(args)
        assert exc.value.code == 1
        assert not out.exists(), "portfolio.yaml wurde trotz Abbruch geschrieben"

    def test_the_stop_names_the_offending_server(
        self, sync_mod, monkeypatch, tmp_path, capsys
    ):
        # Eine Zahl ohne Namen zwingt zum Suchen. Der alte Code hat das richtig
        # gemacht; die Zusage darf beim Umbau nicht verloren gehen.
        _, args = self._harness(
            monkeypatch,
            sync_mod,
            tmp_path,
            [_page(name="lindas-mcp", spec_version=None)],
        )
        with pytest.raises(SystemExit):
            sync_mod.cmd_pull(args)
        assert "lindas-mcp" in capsys.readouterr().err

    def test_a_filled_column_still_writes(self, sync_mod, monkeypatch, tmp_path):
        # Gegenprobe: Ohne sie wuerde ein Abbruch, der IMMER feuert, alle drei
        # Zusagen oben gruen halten und `pull` waere tot.
        out, args = self._harness(
            monkeypatch,
            sync_mod,
            tmp_path,
            [_page(spec_version="2026-07-28")],
        )
        sync_mod.cmd_pull(args)
        assert out.exists()
        assert "mcp_spec_version: 2026-07-28" in out.read_text(encoding="utf-8")
