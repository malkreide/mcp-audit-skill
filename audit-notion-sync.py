#!/usr/bin/env python3
"""
audit-notion-sync.py — Bridge between the MCP Audit Tracker (Notion) and
the local /audit-mcp + audit-portfolio.sh workflow.

Three subcommands:

  health          Verify NOTION_TOKEN and database access.
  pull            Read tracker entries → emit portfolio.yaml.
                  Default filter: only servers with Audit-Status in
                  {Triagiert, In Audit}. Use --all to ignore status.
                  Refuses to overwrite an existing portfolio.yaml unless
                  --force is given.
  push            Update a single tracker entry after an audit run:
                  set Findings (number), Audit-Status (select), append
                  to Notizen with the report URL/path.

Stdlib only (urllib.request, json). No pip install required.

Environment:
  NOTION_TOKEN              required. Notion internal-integration secret.
  NOTION_AUDIT_DB_ID        optional. Defaults to the Stadt Zürich
                            Schulamt MCP Audit Tracker
                            (a2736a65-677d-4cf3-9f94-e874f74a1975).

Usage:
  python3 audit-notion-sync.py health
  python3 audit-notion-sync.py pull [--all] [--force] [-o portfolio.yaml]
  python3 audit-notion-sync.py push <server-name> --findings N \\
                                                  --status "Findings dokumentiert" \\
                                                  --report path/or/url
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
DEFAULT_DB_ID = "a2736a65-677d-4cf3-9f94-e874f74a1975"

# Map Cluster (data-domain select values) → no organisational context.
# Org-context flags come from the multi_select property "Org-Kontext".
ORG_CONTEXT_OPTIONS = {
    "Stadt Zürich": "stadt_zuerich_context",
    "Schulamt": "schulamt_context",
    "Volksschule": "volksschule_context",
    "Enterprise": "enterprise_context",
}

# Conservative defaults for technical capability flags that the tracker
# does not model. Override per-server by editing portfolio.yaml after pull.
DEFAULT_TECH_FLAGS: dict[str, bool] = {
    "uses_sampling": False,
    "uses_sequential_thinking": False,
    "tools_include_filesystem": False,
    "tools_make_external_requests": True,
}

# Pull filter: by default only fetch entries where Audit-Status is in this set.
DEFAULT_STATUS_FILTER = {"Triagiert", "In Audit"}


def fail(msg: str, code: int = 1) -> None:
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(code)


def notion_request(
    method: str,
    path: str,
    token: str,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = f"{NOTION_API}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Notion-Version", NOTION_VERSION)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        try:
            err_body = json.loads(e.read().decode("utf-8"))
            err_msg = err_body.get("message", str(e))
            err_code = err_body.get("code", "")
        except Exception:
            err_msg = str(e)
            err_code = ""
        fail(f"Notion API {e.code}: {err_msg} ({err_code}) [{method} {path}]")
    except URLError as e:
        fail(f"Network error contacting Notion: {e.reason}")


def get_token() -> str:
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        fail("NOTION_TOKEN env var not set. See README for setup.")
    return token


def get_db_id() -> str:
    return os.environ.get("NOTION_AUDIT_DB_ID", DEFAULT_DB_ID)


# ---------------------------------------------------------------------------
# Property extractors — the Notion API encodes each property type differently.
# ---------------------------------------------------------------------------

def prop_title(prop: dict[str, Any]) -> str:
    parts = prop.get("title", [])
    return "".join(p.get("plain_text", "") for p in parts).strip()


def prop_url(prop: dict[str, Any]) -> str | None:
    return prop.get("url")


def prop_select(prop: dict[str, Any]) -> str | None:
    sel = prop.get("select")
    return sel.get("name") if sel else None


def prop_multi_select(prop: dict[str, Any]) -> list[str]:
    return [opt["name"] for opt in prop.get("multi_select", [])]


def prop_number(prop: dict[str, Any]) -> int | float | None:
    return prop.get("number")


def prop_checkbox(prop: dict[str, Any]) -> bool:
    return bool(prop.get("checkbox"))


def prop_rich_text(prop: dict[str, Any]) -> str:
    parts = prop.get("rich_text", [])
    return "".join(p.get("plain_text", "") for p in parts).strip()


# ---------------------------------------------------------------------------
# Profile builder
# ---------------------------------------------------------------------------

def build_profile(props: dict[str, Any]) -> dict[str, Any]:
    transport = prop_select(props.get("Transport", {})) or "dual"
    auth_model = prop_select(props.get("Auth-Modell", {})) or "none"
    data_class = prop_select(props.get("Datenklasse", {})) or "Public Open Data"
    write_access = prop_select(props.get("Schreibzugriff", {})) or "read-only"
    deployment = prop_multi_select(props.get("Deployment", {})) or ["local-stdio"]

    org_kontext = prop_multi_select(props.get("Org-Kontext", {}))

    profile: dict[str, Any] = {
        "transport": transport,
        "auth_model": auth_model,
        "data_class": data_class,
        "write_capable": write_access == "write-capable",
        "deployment": deployment,
    }
    profile.update(DEFAULT_TECH_FLAGS)
    for option_name, flag_name in ORG_CONTEXT_OPTIONS.items():
        profile[flag_name] = option_name in org_kontext
    profile["data_source"] = {
        "is_swiss_open_data": data_class == "Public Open Data"
        and ("Stadt Zürich" in org_kontext or not org_kontext)
    }
    return profile


def build_server_entry(page: dict[str, Any]) -> dict[str, Any] | None:
    props = page.get("properties", {})
    name = prop_title(props.get("Server Name", {}))
    if not name:
        return None
    repo = prop_url(props.get("Repo URL", {})) or ""
    if not repo:
        # No repo URL → cannot audit. Skip.
        return None
    return {
        "name": name,
        "repo": repo,
        "_page_id": page.get("id"),  # for push-back; stripped from YAML output
        "_status": prop_select(props.get("Audit-Status", {})),
        "profile": build_profile(props),
    }


# ---------------------------------------------------------------------------
# Database query (pagination-aware)
# ---------------------------------------------------------------------------

def query_database(
    token: str,
    db_id: str,
    status_filter: set[str] | None,
) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        body: dict[str, Any] = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        resp = notion_request("POST", f"/databases/{db_id}/query", token, body)
        pages.extend(resp.get("results", []))
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")

    if status_filter is None:
        return pages

    filtered = []
    for page in pages:
        status = prop_select(page.get("properties", {}).get("Audit-Status", {}))
        if status in status_filter:
            filtered.append(page)
    return filtered


# ---------------------------------------------------------------------------
# YAML emitter (custom — stdlib has no yaml)
# ---------------------------------------------------------------------------

def yaml_scalar(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "null"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    # Quote if contains special chars or could be misread.
    if any(c in s for c in ":#'\"\n[]{}|>") or s.strip() != s:
        return json.dumps(s, ensure_ascii=False)
    return s


def yaml_list(values: list[Any]) -> str:
    return "[" + ", ".join(yaml_scalar(v) for v in values) + "]"


def emit_portfolio_yaml(servers: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append("# Generated by audit-notion-sync.py — do NOT commit.")
    lines.append("# Edit freely; subsequent `pull --force` will overwrite.")
    lines.append("servers:")
    for s in servers:
        lines.append(f"  - name: {yaml_scalar(s['name'])}")
        lines.append(f"    repo: {yaml_scalar(s['repo'])}")
        lines.append(f"    notion_page_id: {yaml_scalar(s['_page_id'])}")
        lines.append("    profile:")
        prof = s["profile"]
        for k, v in prof.items():
            if isinstance(v, list):
                lines.append(f"      {k}: {yaml_list(v)}")
            elif isinstance(v, dict):
                lines.append(f"      {k}:")
                for kk, vv in v.items():
                    lines.append(f"        {kk}: {yaml_scalar(vv)}")
            else:
                lines.append(f"      {k}: {yaml_scalar(v)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_health(_args: argparse.Namespace) -> None:
    token = get_token()
    db_id = get_db_id()
    me = notion_request("GET", "/users/me", token)
    db = notion_request("GET", f"/databases/{db_id}", token)
    bot_name = me.get("name", "<unknown>")
    db_title = "".join(t.get("plain_text", "") for t in db.get("title", []))
    prop_count = len(db.get("properties", {}))
    print(f"Bot:         {bot_name}")
    print(f"Database:    {db_title} ({db_id})")
    print(f"Properties:  {prop_count}")
    if "Org-Kontext" not in db.get("properties", {}):
        print(
            "\nWarning: 'Org-Kontext' multi_select column not found.\n"
            "  Without it, all org-context flags default to False, which\n"
            "  disables most CH-Compliance checks. Add the column with\n"
            "  options: Stadt Zürich, Schulamt, Volksschule, Enterprise."
        )
    else:
        print("Org-Kontext: present ✓")


def cmd_pull(args: argparse.Namespace) -> None:
    token = get_token()
    db_id = get_db_id()
    out_path = Path(args.output)

    if out_path.exists() and not args.force:
        fail(
            f"{out_path} exists. Refusing to overwrite without --force.\n"
            "  Tip: copy your manual overrides elsewhere first; pull regenerates the file."
        )

    status_filter = None if args.all else DEFAULT_STATUS_FILTER
    pages = query_database(token, db_id, status_filter)
    servers = [s for s in (build_server_entry(p) for p in pages) if s]

    if not servers:
        filt = "all" if args.all else ", ".join(sorted(DEFAULT_STATUS_FILTER))
        print(f"No servers matched filter: {filt}", file=sys.stderr)
        sys.exit(2)

    yaml_text = emit_portfolio_yaml(servers)
    out_path.write_text(yaml_text, encoding="utf-8")

    print(f"Wrote {out_path} with {len(servers)} server(s).")
    if not args.all:
        print(f"Filter: Audit-Status ∈ {{{', '.join(sorted(DEFAULT_STATUS_FILTER))}}}")


def find_page_by_name(token: str, db_id: str, server_name: str) -> str | None:
    body = {
        "filter": {
            "property": "Server Name",
            "title": {"equals": server_name},
        },
        "page_size": 2,
    }
    resp = notion_request("POST", f"/databases/{db_id}/query", token, body)
    results = resp.get("results", [])
    if not results:
        return None
    if len(results) > 1:
        fail(f"Multiple Notion pages match Server Name='{server_name}'. Ambiguous.")
    return results[0]["id"]


def cmd_push(args: argparse.Namespace) -> None:
    token = get_token()
    db_id = get_db_id()

    page_id = args.page_id or find_page_by_name(token, db_id, args.server)
    if not page_id:
        fail(f"No tracker page found for Server Name='{args.server}'.")

    properties: dict[str, Any] = {}
    if args.findings is not None:
        properties["Findings"] = {"number": args.findings}
    if args.status:
        properties["Audit-Status"] = {"select": {"name": args.status}}
    if args.report:
        notiz = f"Audit-Report ({args.report}) — pushed by audit-notion-sync."
        properties["Notizen"] = {
            "rich_text": [{"type": "text", "text": {"content": notiz}}]
        }

    if not properties:
        fail("Nothing to push. Specify at least one of --findings/--status/--report.")

    if args.dry_run:
        print(f"DRY-RUN: would PATCH page {page_id} with:")
        print(json.dumps(properties, indent=2, ensure_ascii=False))
        return

    notion_request("PATCH", f"/pages/{page_id}", token, {"properties": properties})
    print(f"Updated tracker entry for '{args.server}' (page {page_id}).")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="audit-notion-sync",
        description="Sync MCP Audit Tracker (Notion) with portfolio.yaml.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("health", help="Verify token + DB access.")
    sp.set_defaults(func=cmd_health)

    sp = sub.add_parser("pull", help="Tracker → portfolio.yaml.")
    sp.add_argument("-o", "--output", default="portfolio.yaml", help="Target file.")
    sp.add_argument("--all", action="store_true", help="Ignore Audit-Status filter.")
    sp.add_argument("--force", action="store_true", help="Overwrite existing file.")
    sp.set_defaults(func=cmd_pull)

    sp = sub.add_parser("push", help="Update one tracker entry after an audit.")
    sp.add_argument("server", help="Server Name (must match tracker title).")
    sp.add_argument("--findings", type=int, help="Number of findings.")
    sp.add_argument(
        "--status",
        help="New Audit-Status (e.g. 'Findings dokumentiert').",
    )
    sp.add_argument("--report", help="Audit-report path or URL.")
    sp.add_argument("--page-id", help="Skip name lookup; use this Notion page ID.")
    sp.add_argument("--dry-run", action="store_true", help="Print payload, do not PATCH.")
    sp.set_defaults(func=cmd_push)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
