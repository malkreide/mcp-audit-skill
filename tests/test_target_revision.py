"""Tests for the target-revision anchor: audit_init + the validate gate.

`catalog_hash` records what an audit was measured *with*. These tests cover
what it was measured *against* — the audited repo's HEAD — and the property
that matters is asymmetric: a target that moved must fail, but a run that
never recorded a target must not silently read as one that did. The second
half is the easier thing to get wrong, so it gets its own cases.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tools.aggregate_results import _validate_target
from tools.audit_init import (
    TargetRepoError,
    init_audit,
    main,
    target_revision,
    verify_target,
)


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    )
    return proc.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A real one-commit git repo — the thing being audited."""
    r = tmp_path / "target-mcp"
    r.mkdir()
    _git(r, "init", "-q", ".")
    _git(r, "config", "user.email", "audit@example.test")
    _git(r, "config", "user.name", "Audit")
    (r / "server.py").write_text("# v1\n", encoding="utf-8")
    _git(r, "add", "-A")
    _git(r, "commit", "-qm", "initial")
    return r


def _commit(repo: Path, text: str) -> None:
    (repo / "server.py").write_text(text, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "change")


class TestTargetRevision:
    def test_records_sha_branch_and_clean_worktree(self, repo: Path):
        rev = target_revision(repo)
        assert rev["target_sha"] == _git(repo, "rev-parse", "HEAD")
        assert rev["target_dirty"] is False
        assert rev["target_repo"] == str(repo)

    def test_uncommitted_changes_are_recorded_as_dirty(self, repo: Path):
        (repo / "server.py").write_text("# edited, uncommitted\n", encoding="utf-8")
        assert target_revision(repo)["target_dirty"] is True

    def test_non_repo_directory_is_an_error_not_an_empty_sha(self, tmp_path: Path):
        plain = tmp_path / "not-a-repo"
        plain.mkdir()
        with pytest.raises(TargetRepoError):
            target_revision(plain)

    def test_missing_directory_is_an_error(self, tmp_path: Path):
        with pytest.raises(TargetRepoError):
            target_revision(tmp_path / "nope")


class TestInitRecordsTarget:
    def test_meta_carries_the_target_sha(self, repo: Path, tmp_path: Path):
        result = init_audit(
            server="target-mcp",
            base_dir=tmp_path / "audits",
            target_repo=repo,
        )
        meta = json.loads(
            (Path(result["output_dir"]) / "audit-meta.json").read_text(encoding="utf-8")
        )
        assert meta["audit_meta"]["target_sha"] == _git(repo, "rev-parse", "HEAD")

    def test_without_target_repo_no_target_fields_are_invented(self, tmp_path: Path):
        result = init_audit(server="x-mcp", base_dir=tmp_path / "audits")
        assert "target_sha" not in result["audit_meta"]

    def test_a_bad_target_leaves_no_orphan_run_dir_behind(self, tmp_path: Path):
        base = tmp_path / "audits"
        with pytest.raises(TargetRepoError):
            init_audit(server="x-mcp", base_dir=base, target_repo=tmp_path / "nope")
        assert not base.exists() or list(base.iterdir()) == []


class TestVerifyTarget:
    def test_unchanged_target_verifies(self, repo: Path, tmp_path: Path):
        result = init_audit(server="t", base_dir=tmp_path / "a", target_repo=repo)
        report = verify_target({"audit_meta": result["audit_meta"]})
        assert report["unchanged"] is True

    def test_a_new_commit_fails_verification(self, repo: Path, tmp_path: Path):
        result = init_audit(server="t", base_dir=tmp_path / "a", target_repo=repo)
        _commit(repo, "# v2\n")
        report = verify_target({"audit_meta": result["audit_meta"]})
        assert report["unchanged"] is False
        assert "moved" in report["reason"]
        assert report["current_sha"] != report["recorded_sha"]

    def test_worktree_dirtied_after_init_fails(self, repo: Path, tmp_path: Path):
        result = init_audit(server="t", base_dir=tmp_path / "a", target_repo=repo)
        (repo / "server.py").write_text("# edited after init\n", encoding="utf-8")
        report = verify_target({"audit_meta": result["audit_meta"]})
        assert report["unchanged"] is False
        assert "dirty" in report["reason"]

    def test_dirty_at_init_and_still_dirty_is_not_a_change(
        self, repo: Path, tmp_path: Path
    ):
        (repo / "server.py").write_text("# dirty from the start\n", encoding="utf-8")
        result = init_audit(server="t", base_dir=tmp_path / "a", target_repo=repo)
        report = verify_target({"audit_meta": result["audit_meta"]})
        assert report["unchanged"] is True

    def test_unrecorded_target_never_reports_unchanged(self):
        """ "Never looked" must not render the same as "did not move"."""
        report = verify_target({"audit_meta": {"server_name": "x"}})
        assert report["recorded"] is False
        assert report["unchanged"] is False

    def test_recorded_without_repo_asks_where_to_look(self):
        report = verify_target({"audit_meta": {"target_sha": "a" * 40}})
        assert report["unchanged"] is False
        assert "target_repo" in report["reason"]

    def test_repo_override_is_used_when_the_checkout_moved(
        self, repo: Path, tmp_path: Path
    ):
        result = init_audit(server="t", base_dir=tmp_path / "a", target_repo=repo)
        meta = {"audit_meta": dict(result["audit_meta"])}
        meta["audit_meta"]["target_repo"] = str(tmp_path / "gone")
        report = verify_target(meta, repo_override=repo)
        assert report["unchanged"] is True


class TestVerifyTargetCli:
    def test_exit_0_when_unchanged(self, repo: Path, tmp_path: Path, capsys):
        result = init_audit(server="t", base_dir=tmp_path / "a", target_repo=repo)
        assert main(["verify-target", result["output_dir"]]) == 0

    def test_exit_1_when_head_moved(self, repo: Path, tmp_path: Path, capsys):
        result = init_audit(server="t", base_dir=tmp_path / "a", target_repo=repo)
        _commit(repo, "# v2\n")
        assert main(["verify-target", result["output_dir"]]) == 1

    def test_exit_1_when_unrecorded_by_default(self, tmp_path: Path, capsys):
        result = init_audit(server="t", base_dir=tmp_path / "a")
        assert main(["verify-target", result["output_dir"]]) == 1

    def test_allow_unrecorded_is_an_explicit_opt_in(self, tmp_path: Path, capsys):
        result = init_audit(server="t", base_dir=tmp_path / "a")
        assert main(["verify-target", result["output_dir"], "--allow-unrecorded"]) == 0

    def test_missing_meta_is_a_usage_error(self, tmp_path: Path, capsys):
        assert main(["verify-target", str(tmp_path)]) == 2


class TestValidateGateChecksTarget:
    """The gate in `aggregate_results.py validate` — the mandatory pre-finish step."""

    def _run_dir(self, repo: Path, tmp_path: Path) -> Path:
        result = init_audit(server="t", base_dir=tmp_path / "a", target_repo=repo)
        return Path(result["output_dir"])

    def test_moved_target_makes_the_gate_inconsistent(self, repo: Path, tmp_path: Path):
        run = self._run_dir(repo, tmp_path)
        _commit(repo, "# v2\n")
        report: dict = {"consistent": True}
        assert _validate_target(run, report) is False
        assert report["consistent"] is False
        assert report["target"]["status"] == "moved"

    def test_unchanged_target_leaves_the_gate_alone(self, repo: Path, tmp_path: Path):
        run = self._run_dir(repo, tmp_path)
        report: dict = {"consistent": True}
        assert _validate_target(run, report) is True
        assert report["target"]["status"] == "unchanged"

    def test_run_without_meta_warns_but_does_not_fail(self, tmp_path: Path):
        run = tmp_path / "legacy-run"
        run.mkdir()
        report: dict = {"consistent": True}
        assert _validate_target(run, report) is True
        assert report["target"]["status"] == "unrecorded"
        assert report["consistent"] is True

    def test_unreachable_repo_warns_and_says_where_it_looked(
        self, repo: Path, tmp_path: Path
    ):
        run = self._run_dir(repo, tmp_path)
        meta_path = run / "audit-meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["audit_meta"]["target_repo"] = str(tmp_path / "vanished")
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
        report: dict = {"consistent": True}
        assert _validate_target(run, report) is True
        assert report["target"]["status"] == "unreachable"
        assert "vanished" in report["target"]["reason"]

    def test_the_status_is_written_down_not_merely_printed(
        self, repo: Path, tmp_path: Path
    ):
        # A warning that only reaches stderr is gone by the time anyone reads
        # the run directory; every outcome has to land in the report object.
        run = self._run_dir(repo, tmp_path)
        report: dict = {"consistent": True}
        _validate_target(run, report)
        assert "target" in report and report["target"]["status"]
