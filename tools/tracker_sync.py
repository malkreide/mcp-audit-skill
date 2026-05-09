#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tracker_sync.py — Pluggable audit-tracker backend.

The Notion-only `audit-notion-sync.py` worked for the original Stadt-Zürich
setup but blocks anyone who tracks their MCP-server portfolio elsewhere.
This module replaces that with a backend abstraction so the same skill
can drive Notion, a local CSV file, or future backends (Airtable, Google
Sheets) — same `update`/`get` interface, same field semantics.

Field schema (canonical, backend-agnostic):

    server_name      str   primary key
    audit_status     str   one of: Triagiert / In Audit /
                            Findings dokumentiert / In Remediation /
                            Abgeschlossen / Released
    findings         int   total findings count from summary.json
    last_audit_run   str   run-id (ISO timestamp + offset + slug)
    last_audit_at    str   ISO date of the audit run
    production_ready bool  pulled from summary.json
    released_version str   set after `propose_release apply` succeeds
    notes            str   free-form, append-only

Backends implement these via a small adapter class; the CLI dispatches
on `--backend` (or env var `MCP_AUDIT_TRACKER_BACKEND`).

Stdlib only — no extra deps for the CSV backend; Notion uses the same
urllib pattern as `audit-notion-sync.py`.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.path_utils import force_utf8_stdio  # noqa: E402

CANONICAL_FIELDS = (
    "server_name",
    "audit_status",
    "findings",
    "last_audit_run",
    "last_audit_at",
    "production_ready",
    "released_version",
    "notes",
)


class TrackerError(Exception):
    """Raised on backend connectivity, auth, or schema errors."""


@dataclass
class TrackerRecord:
    server_name: str
    audit_status: str | None = None
    findings: int | None = None
    last_audit_run: str | None = None
    last_audit_at: str | None = None
    production_ready: bool | None = None
    released_version: str | None = None
    notes: str | None = None

    def to_dict_nonnull(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


# ---------------------------------------------------------------------------
# Backend interface
# ---------------------------------------------------------------------------

class TrackerBackend:
    name: str = "abstract"

    def get(self, server_name: str) -> TrackerRecord | None:
        raise NotImplementedError

    def update(self, server_name: str, fields: dict[str, Any]) -> TrackerRecord:
        raise NotImplementedError

    def list_all(self) -> list[TrackerRecord]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# CSV backend — zero-deps, perfect for users without any cloud DB.
# ---------------------------------------------------------------------------

class CsvBackend(TrackerBackend):
    name = "csv"

    def __init__(self, path: Path):
        self.path = Path(path)

    def _ensure_file(self) -> None:
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=CANONICAL_FIELDS)
                w.writeheader()

    def _read_rows(self) -> list[dict[str, str]]:
        self._ensure_file()
        with self.path.open("r", encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    def _write_rows(self, rows: Iterable[dict[str, str]]) -> None:
        with self.path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CANONICAL_FIELDS)
            w.writeheader()
            for row in rows:
                # Coerce all values to strings so CSV stays valid.
                w.writerow({k: ("" if row.get(k) is None else str(row.get(k)))
                            for k in CANONICAL_FIELDS})

    @staticmethod
    def _row_to_record(row: dict[str, str]) -> TrackerRecord:
        def _opt(v: str) -> str | None:
            return v if v != "" else None

        findings = row.get("findings", "") or ""
        prod_ready = row.get("production_ready", "") or ""
        return TrackerRecord(
            server_name=row.get("server_name", ""),
            audit_status=_opt(row.get("audit_status", "")),
            findings=int(findings) if findings.strip().isdigit() else None,
            last_audit_run=_opt(row.get("last_audit_run", "")),
            last_audit_at=_opt(row.get("last_audit_at", "")),
            production_ready=(
                None if prod_ready == "" else prod_ready.lower() == "true"
            ),
            released_version=_opt(row.get("released_version", "")),
            notes=_opt(row.get("notes", "")),
        )

    def get(self, server_name: str) -> TrackerRecord | None:
        for row in self._read_rows():
            if row.get("server_name") == server_name:
                return self._row_to_record(row)
        return None

    def update(self, server_name: str, fields: dict[str, Any]) -> TrackerRecord:
        rows = self._read_rows()
        merged: dict[str, Any] = {"server_name": server_name}
        found_index: int | None = None
        for i, row in enumerate(rows):
            if row.get("server_name") == server_name:
                merged = {**row, "server_name": server_name}
                found_index = i
                break

        for k, v in fields.items():
            if k not in CANONICAL_FIELDS:
                raise TrackerError(
                    f"Unknown field {k!r}; valid: {CANONICAL_FIELDS}"
                )
            merged[k] = v

        if found_index is None:
            rows.append(merged)
        else:
            rows[found_index] = merged

        self._write_rows(rows)
        return self._row_to_record(
            {k: ("" if merged.get(k) is None else str(merged.get(k)))
             for k in CANONICAL_FIELDS}
        )

    def list_all(self) -> list[TrackerRecord]:
        return [self._row_to_record(r) for r in self._read_rows()]


# ---------------------------------------------------------------------------
# Notion backend — wraps the same API the existing audit-notion-sync uses.
# ---------------------------------------------------------------------------

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
NOTION_DEFAULT_DB_ID = "a2736a65-677d-4cf3-9f94-e874f74a1975"


class NotionBackend(TrackerBackend):
    name = "notion"

    # Map canonical field → (notion property name, notion property type).
    # Properties not present in this map fall through to "Notizen" rich-text.
    FIELD_MAP: dict[str, tuple[str, str]] = {
        "audit_status": ("Audit-Status", "select"),
        "findings": ("Findings", "number"),
        "released_version": ("Released Version", "rich_text"),
        "last_audit_run": ("Last Audit Run", "rich_text"),
        "last_audit_at": ("Last Audit At", "rich_text"),
        "production_ready": ("Production Ready", "checkbox"),
    }

    def __init__(self, token: str, db_id: str):
        self.token = token
        self.db_id = db_id

    @classmethod
    def from_env(cls) -> "NotionBackend":
        token = os.environ.get("NOTION_TOKEN")
        if not token:
            raise TrackerError(
                "NOTION_TOKEN env var not set; required for the notion backend."
            )
        db_id = os.environ.get("NOTION_AUDIT_DB_ID", NOTION_DEFAULT_DB_ID)
        return cls(token=token, db_id=db_id)

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{NOTION_API}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Notion-Version", NOTION_VERSION)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urlopen(req) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            try:
                err = json.loads(e.read().decode("utf-8"))
                msg = err.get("message", str(e))
            except Exception:
                msg = str(e)
            raise TrackerError(f"Notion API {e.code}: {msg} [{method} {path}]")
        except URLError as e:
            raise TrackerError(f"Notion network error: {e.reason}")

    def _find_page_id(self, server_name: str) -> str | None:
        body = {
            "filter": {
                "property": "Server Name",
                "title": {"equals": server_name},
            },
            "page_size": 2,
        }
        resp = self._request("POST", f"/databases/{self.db_id}/query", body)
        results = resp.get("results", [])
        if not results:
            return None
        if len(results) > 1:
            raise TrackerError(
                f"Multiple Notion pages match Server Name={server_name!r}."
            )
        return results[0]["id"]

    @staticmethod
    def _build_property(notion_type: str, value: Any) -> dict[str, Any]:
        if notion_type == "select":
            return {"select": {"name": str(value)}}
        if notion_type == "number":
            return {"number": value}
        if notion_type == "checkbox":
            return {"checkbox": bool(value)}
        if notion_type == "rich_text":
            return {
                "rich_text": [{"type": "text", "text": {"content": str(value)}}]
            }
        raise TrackerError(f"Unsupported Notion property type {notion_type!r}")

    def update(self, server_name: str, fields: dict[str, Any]) -> TrackerRecord:
        page_id = self._find_page_id(server_name)
        if not page_id:
            raise TrackerError(
                f"No Notion page for Server Name={server_name!r}. "
                "Create the tracker entry first."
            )

        properties: dict[str, Any] = {}
        notes_extra: list[str] = []
        for k, v in fields.items():
            if k not in CANONICAL_FIELDS:
                raise TrackerError(f"Unknown field {k!r}")
            if k == "server_name":
                continue
            if k in self.FIELD_MAP:
                prop_name, prop_type = self.FIELD_MAP[k]
                properties[prop_name] = self._build_property(prop_type, v)
            elif k == "notes":
                notes_extra.append(str(v))

        if notes_extra:
            properties["Notizen"] = {
                "rich_text": [
                    {"type": "text", "text": {"content": "\n".join(notes_extra)}}
                ],
            }

        if not properties:
            raise TrackerError("Nothing to update — no mapped fields.")

        self._request("PATCH", f"/pages/{page_id}", {"properties": properties})
        # We don't round-trip the full record here; return what we wrote.
        record = TrackerRecord(server_name=server_name)
        for k, v in fields.items():
            setattr(record, k, v)
        return record

    def get(self, server_name: str) -> TrackerRecord | None:
        page_id = self._find_page_id(server_name)
        if not page_id:
            return None
        # Minimal projection: only re-derive the fields we know how to read
        # back. Reading back is rarely needed; existing portfolio.yaml flow
        # remains the authoritative pull path.
        return TrackerRecord(server_name=server_name)

    def list_all(self) -> list[TrackerRecord]:
        pages: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            body: dict[str, Any] = {"page_size": 100}
            if cursor:
                body["start_cursor"] = cursor
            resp = self._request("POST", f"/databases/{self.db_id}/query", body)
            pages.extend(resp.get("results", []))
            if not resp.get("has_more"):
                break
            cursor = resp.get("next_cursor")
        records: list[TrackerRecord] = []
        for p in pages:
            props = p.get("properties", {})
            title = props.get("Server Name", {}).get("title", [])
            name = "".join(t.get("plain_text", "") for t in title).strip()
            if name:
                records.append(TrackerRecord(server_name=name))
        return records


# ---------------------------------------------------------------------------
# Backend resolver
# ---------------------------------------------------------------------------

def get_backend(name: str | None, csv_path: str | None = None) -> TrackerBackend:
    backend = (name or os.environ.get("MCP_AUDIT_TRACKER_BACKEND") or "csv").lower()
    if backend == "csv":
        path = csv_path or os.environ.get("MCP_AUDIT_TRACKER_PATH") or "tracker.csv"
        return CsvBackend(Path(path))
    if backend == "notion":
        return NotionBackend.from_env()
    raise TrackerError(
        f"Unknown tracker backend {backend!r}; valid: csv, notion"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_kv(items: list[str]) -> dict[str, Any]:
    """Parse `key=value` flags into a typed dict."""
    out: dict[str, Any] = {}
    for item in items:
        if "=" not in item:
            raise TrackerError(f"Bad --set value {item!r}, expected key=value")
        k, v = item.split("=", 1)
        if k not in CANONICAL_FIELDS:
            raise TrackerError(f"Unknown field {k!r}")
        if k == "findings":
            out[k] = int(v)
        elif k == "production_ready":
            out[k] = v.lower() in ("true", "1", "yes")
        else:
            out[k] = v
    return out


def cmd_update(args: argparse.Namespace) -> int:
    backend = get_backend(args.backend, args.csv_path)
    fields = _parse_kv(args.set or [])

    # Convenience: if --from-summary is given, pull common fields from a
    # summary.json so callers don't have to duplicate them on the CLI.
    if args.from_summary:
        summary = json.loads(Path(args.from_summary).read_text(encoding="utf-8"))
        fields.setdefault(
            "findings",
            int(summary.get("findings", {}).get("expected_count", 0)),
        )
        fields.setdefault(
            "production_ready",
            bool(summary.get("production_ready", False)),
        )
        meta = summary.get("audit_meta", {}) or {}
        if meta.get("run_id"):
            fields.setdefault("last_audit_run", meta["run_id"])
        if meta.get("started_at"):
            fields.setdefault("last_audit_at", str(meta["started_at"])[:10])

    if not fields:
        raise TrackerError("Nothing to update; pass --set key=value or --from-summary.")

    record = backend.update(args.server, fields)
    print(json.dumps({
        "ok": True,
        "backend": backend.name,
        "server_name": record.server_name,
        "updated": record.to_dict_nonnull(),
    }, indent=2, ensure_ascii=False))
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    backend = get_backend(args.backend, args.csv_path)
    record = backend.get(args.server)
    if record is None:
        print(json.dumps({"ok": False, "reason": "not_found",
                          "backend": backend.name}, indent=2))
        return 2
    print(json.dumps({"ok": True, "backend": backend.name,
                      "record": record.to_dict_nonnull()},
                     indent=2, ensure_ascii=False))
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    backend = get_backend(args.backend, args.csv_path)
    records = backend.list_all()
    print(json.dumps({
        "ok": True,
        "backend": backend.name,
        "count": len(records),
        "records": [r.to_dict_nonnull() for r in records],
    }, indent=2, ensure_ascii=False))
    return 0


def main() -> None:
    force_utf8_stdio()
    parser = argparse.ArgumentParser(
        prog="tracker_sync",
        description="Update an audit-tracker record across pluggable backends.",
    )
    parser.add_argument(
        "--backend", choices=("csv", "notion"),
        help="Override $MCP_AUDIT_TRACKER_BACKEND. Default: csv.",
    )
    parser.add_argument(
        "--csv-path",
        help="CSV file path (csv backend). Override $MCP_AUDIT_TRACKER_PATH.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("update", help="Set fields on a server's row.")
    sp.add_argument("server", help="Server name (primary key).")
    sp.add_argument("--set", action="append", metavar="key=value",
                    help="Repeatable. Valid keys: " + ", ".join(CANONICAL_FIELDS))
    sp.add_argument("--from-summary", help="Pull defaults from a summary.json.")
    sp.set_defaults(func=cmd_update)

    sp = sub.add_parser("get", help="Read a single record.")
    sp.add_argument("server")
    sp.set_defaults(func=cmd_get)

    sp = sub.add_parser("list", help="List all records.")
    sp.set_defaults(func=cmd_list)

    args = parser.parse_args()
    try:
        sys.exit(args.func(args))
    except TrackerError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
