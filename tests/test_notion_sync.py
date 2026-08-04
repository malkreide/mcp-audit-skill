"""Tests for audit-notion-sync.py — only the pure profile-builder logic.

Network-dependent code paths (Notion HTTP) are out of scope for this
suite; they're integration-tested manually via the `health` subcommand.

The build_profile derivation got more complex in issue #16 (added
is_cloud_deployed), so a small unit test guards against drift.
"""

from __future__ import annotations

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

    def test_an_empty_cell_falls_back_to_the_conservative_revision(self, sync_mod):
        # Conservative on purpose: a migrated server gets too FEW checks and
        # trips over the first migration finding. The opposite default would
        # run the old checks past a protocol that no longer has them, and
        # nothing would say so.
        profile = sync_mod.build_profile(_props(spec_version=None))
        assert profile["mcp_spec_version"] == "2025-11-25"

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
