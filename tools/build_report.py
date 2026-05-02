#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render the final audit-report.md from summary.json + findings/.

Replaces the inline Python heredocs that the original SKILL Step 6 used to
generate ad-hoc — the original audit run on Windows hit Bash quoting
crashes when the heredocs got too clever (issue #11).

Inputs:
    summary.json   — produced by tools/aggregate_results.py aggregate
    findings/      — directory of finding-doc files (one per check id)
    profile.yaml   — the server profile from Step 1 (optional but recommended)

Output:
    audit-report.md — final stakeholder-facing report

Usage:
    python tools/build_report.py audits/<run>/
    python tools/build_report.py audits/<run>/ --profile profile.yaml --out report.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Bootstrap so tools.* imports work when invoked as a script.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.path_utils import force_utf8_stdio  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SEVERITY_ORDER = ("critical", "high", "medium", "low")


def _load_summary(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_profile(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return json.loads(text)
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        return {}
    data = yaml.safe_load(text)
    if isinstance(data, dict) and "servers" in data and isinstance(data["servers"], list) and data["servers"]:
        first = data["servers"][0]
        return first.get("profile", first) if isinstance(first, dict) else {}
    if isinstance(data, dict) and "profile" in data:
        return data["profile"]
    return data if isinstance(data, dict) else {}


def _list_findings(findings_dir: Path) -> list[Path]:
    if not findings_dir.exists():
        return []
    return sorted(findings_dir.glob("*.md"))


def _ready_marker(production_ready: bool) -> str:
    return "ready" if production_ready else "not-ready"


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def render_executive_summary(summary: dict[str, Any]) -> str:
    server = summary.get("audit_meta", {}).get("server_name", "<server>")
    totals = summary.get("totals", {})
    by_status = totals.get("by_status", {})
    findings = summary.get("findings", {})
    by_sev = totals.get("by_severity_among_findings", {})
    blocking = summary.get("blocking_findings", [])

    sentence_1 = (
        f"Server `{server}` wurde gegen {totals.get('applicable', 0)} "
        f"anwendbare Best-Practice-Checks geprüft."
    )
    sentence_2 = (
        f"{by_status.get('pass', 0)} bestanden, "
        f"{findings.get('expected_count', 0)} Findings dokumentiert "
        f"({by_sev.get('critical', 0)} critical, "
        f"{by_sev.get('high', 0)} high, "
        f"{by_sev.get('medium', 0)} medium, "
        f"{by_sev.get('low', 0)} low)."
    )
    if summary.get("production_ready"):
        sentence_3 = "Production-Readiness: erreicht."
    else:
        if blocking:
            ids = ", ".join(blocking)
            sentence_3 = (
                f"Production-Readiness: NICHT erreicht — blockierend: {ids}."
            )
        else:
            sentence_3 = (
                "Production-Readiness: NICHT erreicht — siehe Findings-Tabelle."
            )

    return (
        "## 1. Executive Summary\n\n"
        f"{sentence_1} {sentence_2} {sentence_3}\n\n"
        f"**Production-Readiness:** "
        f"{'YES' if summary.get('production_ready') else 'NO'}\n"
    )


def render_profile_snapshot(
    summary: dict[str, Any],
    profile: dict[str, Any],
) -> str:
    out = ["## 2. Profil-Snapshot\n"]
    meta = summary.get("audit_meta", {})
    out.append("| Feld | Wert |")
    out.append("|---|---|")
    out.append(f"| Server-Name | `{meta.get('server_name', '?')}` |")
    out.append(f"| Audit-Datum | {meta.get('audit_date', '?')} |")
    out.append(f"| Skill-Version | {meta.get('skill_version', '?')} |")
    out.append(f"| Catalog-Version | {meta.get('catalog_version', '?')} |")
    if profile:
        for key in (
            "transport", "auth_model", "data_class", "write_capable",
            "deployment", "uses_sampling", "tools_make_external_requests",
            "stadt_zuerich_context", "schulamt_context",
        ):
            if key in profile:
                out.append(f"| {key} | `{profile[key]}` |")
        ds = profile.get("data_source")
        if isinstance(ds, dict) and "is_swiss_open_data" in ds:
            out.append(
                f"| data_source.is_swiss_open_data | "
                f"`{ds['is_swiss_open_data']}` |"
            )
    out.append("")
    return "\n".join(out)


def render_applicability(summary: dict[str, Any]) -> str:
    totals = summary.get("totals", {})
    by_cat = totals.get("by_category", {})
    out = ["## 3. Applicability\n"]
    out.append("### Status pro Kategorie\n")
    out.append("| Kategorie | Pass | Fail | Partial | Todo | N/A |")
    out.append("|---|---|---|---|---|---|")
    for cat in sorted(by_cat):
        c = by_cat[cat]
        out.append(
            f"| {cat} | {c.get('pass', 0)} | {c.get('fail', 0)} | "
            f"{c.get('partial', 0)} | {c.get('todo', 0)} | {c.get('n/a', 0)} |"
        )
    bs = totals.get("by_status", {})
    out.append(
        f"| **Total** | **{bs.get('pass', 0)}** | **{bs.get('fail', 0)}** | "
        f"**{bs.get('partial', 0)}** | **{bs.get('todo', 0)}** | "
        f"**{bs.get('n/a', 0)}** |"
    )
    out.append("")
    return "\n".join(out)


def render_findings_table(summary: dict[str, Any]) -> str:
    findings = summary.get("findings", {})
    details = findings.get("details", [])
    out = ["## 4. Findings-Übersicht\n"]
    out.append(f"_Policy: `{findings.get('policy', '?')}`_\n")
    if not details:
        out.append("_Keine Findings — alle anwendbaren Checks bestanden._\n")
        return "\n".join(out)
    out.append("| ID | Category | Severity | Status |")
    out.append("|---|---|---|---|")
    # Sort by severity then category then id
    sev_idx = {s: i for i, s in enumerate(SEVERITY_ORDER)}
    sorted_details = sorted(
        details,
        key=lambda d: (
            sev_idx.get(d.get("severity", "low"), 99),
            d.get("category", ""),
            d.get("check_id", ""),
        ),
    )
    for d in sorted_details:
        out.append(
            f"| {d.get('check_id')} | {d.get('category')} | "
            f"{d.get('severity')} | {d.get('status')} |"
        )
    out.append("")
    out.append(f"**Gesamt:** {findings.get('expected_count', 0)} Findings")
    out.append("")
    return "\n".join(out)


def render_detail_findings(
    summary: dict[str, Any],
    findings_dir: Path,
) -> str:
    out = ["## 5. Detail-Findings\n"]
    expected = summary.get("findings", {}).get("expected_ids", [])
    if not expected:
        out.append("_Keine Findings._\n")
        return "\n".join(out)
    files = _list_findings(findings_dir)
    by_id: dict[str, Path] = {}
    for f in files:
        # Filenames follow `<CHECK-ID>-<slug>.md`.
        parts = f.stem.split("-")
        if len(parts) >= 2 and parts[1].isdigit():
            by_id[f"{parts[0]}-{parts[1]}"] = f
    for cid in expected:
        path = by_id.get(cid)
        if path is None:
            out.append(f"### {cid} — _missing finding doc_\n")
            out.append(
                "_Validation gate failed: this finding was expected but no "
                "document was persisted. Run "
                "`python tools/aggregate_results.py validate <audit_dir>`._\n"
            )
            continue
        out.append(f"### {cid}\n")
        # Embed the finding doc verbatim, indented under the section.
        out.append(path.read_text(encoding="utf-8").strip())
        out.append("\n")
    return "\n".join(out)


def render_remediation_plan(summary: dict[str, Any]) -> str:
    findings = summary.get("findings", {})
    details = findings.get("details", [])
    out = ["## 6. Remediation-Plan\n"]
    if not details:
        out.append("_Keine Findings._\n")
        return "\n".join(out)
    sev_idx = {s: i for i, s in enumerate(SEVERITY_ORDER)}
    sorted_details = sorted(
        details,
        key=lambda d: (
            sev_idx.get(d.get("severity", "low"), 99),
            d.get("category", ""),
            d.get("check_id", ""),
        ),
    )
    out.append("### Empfohlene Reihenfolge\n")
    for i, d in enumerate(sorted_details, start=1):
        out.append(
            f"{i}. **{d.get('check_id')}** "
            f"({d.get('severity')}, {d.get('status')})"
        )
    out.append("")
    return "\n".join(out)


def render_metadata(summary: dict[str, Any]) -> str:
    meta = summary.get("audit_meta", {})
    out = ["## 7. Audit-Metadata\n"]
    out.append("| Feld | Wert |")
    out.append("|---|---|")
    for key in (
        "skill_version", "catalog_version", "applies_when_dsl_version",
        "policy", "audit_date",
    ):
        if key in meta:
            out.append(f"| {key} | `{meta[key]}` |")
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def build_report(
    summary: dict[str, Any],
    profile: dict[str, Any],
    findings_dir: Path,
) -> str:
    server = summary.get("audit_meta", {}).get("server_name", "<server>")
    audit_date = summary.get("audit_meta", {}).get("audit_date", "")
    parts = [
        f"# MCP-Server Audit-Report — `{server}`\n",
        f"**Audit-Datum:** {audit_date}",
        f"**Skill-Version:** {summary.get('audit_meta', {}).get('skill_version', '?')}",
        f"**Catalog-Version:** {summary.get('audit_meta', {}).get('catalog_version', '?')}",
        "",
        "---",
        "",
        render_executive_summary(summary),
        "---",
        "",
        render_profile_snapshot(summary, profile),
        "---",
        "",
        render_applicability(summary),
        "---",
        "",
        render_findings_table(summary),
        "---",
        "",
        render_detail_findings(summary, findings_dir),
        "---",
        "",
        render_remediation_plan(summary),
        "---",
        "",
        render_metadata(summary),
        "",
        "_Generated by tools/build_report.py — do not edit by hand._",
        "",
    ]
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdio()
    parser = argparse.ArgumentParser(
        prog="build_report",
        description=(
            "Render audit-report.md from summary.json and findings/. "
            "Replaces inline Python heredocs in SKILL Step 6."
        ),
    )
    parser.add_argument(
        "audit_dir",
        help="Path to the audit directory containing summary.json and findings/",
    )
    parser.add_argument(
        "--summary",
        default=None,
        help="Override summary.json path (default: <audit_dir>/summary.json)",
    )
    parser.add_argument(
        "--findings-dir",
        default=None,
        help="Override findings dir (default: <audit_dir>/findings)",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="Optional path to profile YAML/JSON for the snapshot section",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output path for report (default: <audit_dir>/audit-report.md)",
    )
    args = parser.parse_args(argv)

    audit_dir = Path(args.audit_dir)
    summary_path = Path(args.summary) if args.summary else audit_dir / "summary.json"
    findings_dir = (
        Path(args.findings_dir) if args.findings_dir else audit_dir / "findings"
    )
    out_path = Path(args.out) if args.out else audit_dir / "audit-report.md"
    profile_path = Path(args.profile) if args.profile else None

    if not summary_path.exists():
        print(f"Error: {summary_path} not found", file=sys.stderr)
        return 2

    summary = _load_summary(summary_path)
    profile = _load_profile(profile_path)
    report = build_report(summary, profile, findings_dir)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"Report written to {out_path} ({len(report)} chars)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
