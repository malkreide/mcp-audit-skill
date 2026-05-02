# -*- coding: utf-8 -*-
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
    }


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
            "transport", "auth_model", "data_class", "write_capable",
            "deployment", "is_cloud_deployed", "uses_sampling",
            "tools_make_external_requests", "data_source",
        ):
            assert field in profile, f"missing field {field}"

    def test_write_capable_derived_from_schreibzugriff(self, sync_mod):
        ro = sync_mod.build_profile(_props(write="read-only"))
        wr = sync_mod.build_profile(_props(write="write-capable"))
        assert ro["write_capable"] is False
        assert wr["write_capable"] is True
