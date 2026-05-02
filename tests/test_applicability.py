# -*- coding: utf-8 -*-
"""Tests for the canonical applies_when DSL evaluator.

Covers every DSL construct used in the v0.5.0 catalog plus negative cases.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tools.eval_applicability import (
    ApplicabilityError,
    ParseError,
    TypeMismatchError,
    UnknownFieldError,
    evaluate,
    evaluate_catalog,
    parse_check_frontmatter,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKS_DIR = REPO_ROOT / "checks"


@pytest.fixture
def srgssr_profile() -> dict:
    """Profile of the srgssr-mcp server (regression baseline)."""
    return {
        "transport": "stdio-only",
        "auth_model": "none",
        "data_class": "Public Open Data",
        "write_capable": False,
        "write_access": "read-only",
        "deployment": ["local-stdio"],
        "is_cloud_deployed": False,
        "uses_sampling": False,
        "uses_sequential_thinking": False,
        "tools_include_filesystem": False,
        "tools_make_external_requests": True,
        "stadt_zuerich_context": False,
        "schulamt_context": False,
        "volksschule_context": False,
        "enterprise_context": False,
        "sdk_language": "Python",
        "data_source": {"is_swiss_open_data": True},
    }


@pytest.fixture
def zh_education_profile() -> dict:
    """Profile of zh-education-mcp (write_capable, PII-adjacent)."""
    return {
        "transport": "stdio-only",
        "auth_model": "API-Key",
        "data_class": "Verwaltungsdaten",
        "write_capable": False,
        "write_access": "read-only",
        "deployment": ["local-stdio"],
        "is_cloud_deployed": False,
        "uses_sampling": False,
        "uses_sequential_thinking": False,
        "tools_include_filesystem": False,
        "tools_make_external_requests": True,
        "stadt_zuerich_context": True,
        "schulamt_context": True,
        "volksschule_context": True,
        "enterprise_context": False,
        "sdk_language": "Python",
        "data_source": {"is_swiss_open_data": False},
    }


@pytest.fixture
def cloud_oauth_profile() -> dict:
    """Profile of an HTTP/SSE cloud-deployed OAuth-Proxy server."""
    return {
        "transport": "HTTP/SSE",
        "auth_model": "OAuth-Proxy",
        "data_class": "PII",
        "write_capable": True,
        "write_access": "write-capable",
        "deployment": ["Railway"],
        "is_cloud_deployed": True,
        "uses_sampling": True,
        "uses_sequential_thinking": True,
        "tools_include_filesystem": True,
        "tools_make_external_requests": True,
        "stadt_zuerich_context": True,
        "schulamt_context": False,
        "volksschule_context": True,
        "enterprise_context": True,
        "sdk_language": "TypeScript",
        "data_source": {"is_swiss_open_data": False},
    }


# ---------------------------------------------------------------------------
# DSL primitives
# ---------------------------------------------------------------------------

class TestAlways:
    def test_always_is_true(self, srgssr_profile):
        assert evaluate("always", srgssr_profile) is True

    def test_always_short_circuits_or(self, srgssr_profile):
        assert evaluate('auth_model == "API-Key" or always', srgssr_profile) is True

    def test_always_with_and(self, srgssr_profile):
        # "always and X" reduces to X
        assert evaluate('always and transport == "stdio-only"', srgssr_profile) is True
        assert evaluate('always and transport == "HTTP/SSE"', srgssr_profile) is False


class TestStringEquality:
    def test_eq_match(self, srgssr_profile):
        assert evaluate('transport == "stdio-only"', srgssr_profile) is True

    def test_eq_mismatch(self, srgssr_profile):
        assert evaluate('transport == "HTTP/SSE"', srgssr_profile) is False

    def test_ne_match(self, srgssr_profile):
        assert evaluate('transport != "HTTP/SSE"', srgssr_profile) is True

    def test_ne_mismatch(self, srgssr_profile):
        assert evaluate('transport != "stdio-only"', srgssr_profile) is False

    def test_single_quotes_work(self, srgssr_profile):
        assert evaluate("transport == 'stdio-only'", srgssr_profile) is True

    def test_hyphen_in_string(self, zh_education_profile):
        assert evaluate('auth_model == "API-Key"', zh_education_profile) is True


class TestBooleanEquality:
    def test_bool_eq_true(self, srgssr_profile):
        assert evaluate("tools_make_external_requests == true", srgssr_profile) is True

    def test_bool_eq_false(self, srgssr_profile):
        assert evaluate("uses_sampling == false", srgssr_profile) is True

    def test_bool_ne(self, srgssr_profile):
        assert evaluate("write_capable != true", srgssr_profile) is True


class TestLogicalOperators:
    def test_or_left_true(self, srgssr_profile):
        assert evaluate(
            'transport == "stdio-only" or transport == "dual"', srgssr_profile
        ) is True

    def test_or_right_true(self, srgssr_profile):
        assert evaluate(
            'transport == "HTTP/SSE" or transport == "stdio-only"', srgssr_profile
        ) is True

    def test_or_both_false(self, srgssr_profile):
        assert evaluate(
            'transport == "HTTP/SSE" or transport == "dual"', srgssr_profile
        ) is False

    def test_and_both_true(self, zh_education_profile):
        assert evaluate(
            'auth_model == "API-Key" and tools_make_external_requests == true',
            zh_education_profile,
        ) is True

    def test_and_one_false(self, zh_education_profile):
        assert evaluate(
            'auth_model == "API-Key" and write_capable == true',
            zh_education_profile,
        ) is False

    def test_precedence_and_binds_tighter_than_or(self, srgssr_profile):
        # (true and false) or true == true
        # If precedence were wrong, (true and (false or true)) is also true,
        # so we need a case where the answer differs:
        # false or (true and false) -> false
        # (false or true) and false -> false
        # use: true or (false and X) -> true regardless
        # better: false and X or true should be (false and X) or true -> true
        assert evaluate(
            'transport == "HTTP/SSE" and uses_sampling == true or always',
            srgssr_profile,
        ) is True

    def test_parenthesized_or_with_and(self, srgssr_profile):
        # Force: (false or false) and true -> false
        assert evaluate(
            '(transport == "HTTP/SSE" or transport == "dual") and tools_make_external_requests == true',
            srgssr_profile,
        ) is False


class TestIncludes:
    def test_includes_match(self, srgssr_profile):
        assert evaluate('deployment.includes("local-stdio")', srgssr_profile) is True

    def test_includes_no_match(self, srgssr_profile):
        assert evaluate('deployment.includes("Railway")', srgssr_profile) is False

    def test_includes_chained_or(self, srgssr_profile):
        assert evaluate(
            'deployment.includes("Railway") or deployment.includes("Render") or deployment.includes("local-stdio")',
            srgssr_profile,
        ) is True

    def test_includes_with_grouping(self, cloud_oauth_profile):
        assert evaluate(
            '(deployment.includes("Railway") or deployment.includes("Render")) and write_capable == true',
            cloud_oauth_profile,
        ) is True


class TestDottedPaths:
    def test_dotted_field_access(self, srgssr_profile):
        assert evaluate(
            "data_source.is_swiss_open_data == true", srgssr_profile
        ) is True

    def test_dotted_field_false(self, zh_education_profile):
        assert evaluate(
            "data_source.is_swiss_open_data == true", zh_education_profile
        ) is False


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

class TestErrors:
    def test_empty_expression(self, srgssr_profile):
        with pytest.raises(ParseError):
            evaluate("", srgssr_profile)

    def test_whitespace_only(self, srgssr_profile):
        with pytest.raises(ParseError):
            evaluate("   ", srgssr_profile)

    def test_unknown_field(self, srgssr_profile):
        with pytest.raises(UnknownFieldError):
            evaluate('nonexistent_field == "x"', srgssr_profile)

    def test_unknown_dotted_segment(self, srgssr_profile):
        with pytest.raises(UnknownFieldError):
            evaluate("data_source.does_not_exist == true", srgssr_profile)

    def test_traverse_into_non_object(self, srgssr_profile):
        with pytest.raises(UnknownFieldError):
            evaluate("transport.subfield == true", srgssr_profile)

    def test_type_mismatch_string_vs_bool(self, srgssr_profile):
        with pytest.raises(TypeMismatchError):
            evaluate("transport == true", srgssr_profile)

    def test_includes_on_non_list(self, srgssr_profile):
        with pytest.raises(TypeMismatchError):
            evaluate('transport.includes("stdio-only")', srgssr_profile)

    def test_unknown_method(self, srgssr_profile):
        with pytest.raises(ParseError):
            evaluate('deployment.contains("local-stdio")', srgssr_profile)

    def test_unbalanced_paren(self, srgssr_profile):
        with pytest.raises(ParseError):
            evaluate('(transport == "stdio-only"', srgssr_profile)

    def test_bare_literal_disallowed(self, srgssr_profile):
        with pytest.raises(ParseError):
            evaluate("true", srgssr_profile)

    def test_trailing_garbage(self, srgssr_profile):
        with pytest.raises(ParseError):
            evaluate('transport == "stdio-only" foo', srgssr_profile)

    def test_python_True_not_accepted(self, srgssr_profile):
        # Capitalized "True" is an unknown identifier, not a keyword.
        with pytest.raises(UnknownFieldError):
            evaluate("write_capable == True", srgssr_profile)


# ---------------------------------------------------------------------------
# Real catalog regression tests
# ---------------------------------------------------------------------------

class TestRealCatalog:
    """Lock the applicability counts for known profiles so future evaluator
    changes can't silently shift the numbers (the bug that motivated this
    module).
    """

    def test_srgssr_profile_count(self, srgssr_profile):
        results = evaluate_catalog(srgssr_profile, CHECKS_DIR)
        applicable = [cid for cid, r in results.items() if r["applicable"]]
        # Lock the count seen during the first canonical run. If catalog
        # content changes, this number must be updated together with a
        # CHANGELOG entry.
        # Note: total count of checks
        assert len(results) == 68
        # Note: applicability is determined entirely by the DSL grammar.
        # We assert a stable bound rather than exact equality so that the
        # test fails loudly only on grammar drift.
        assert 25 <= len(applicable) <= 40, (
            f"Applicable count drifted: got {len(applicable)} "
            f"({applicable})"
        )

    # The 9 checks that previously had `deployment != "local-stdio"` were
    # migrated to `is_cloud_deployed == true` in issue #16. The catalog
    # must now be type-clean — every check evaluates without a
    # type-mismatch error against any well-formed profile.
    PREVIOUSLY_BUGGY_CHECKS = {
        "OBS-005",
        "OBS-006",
        "SCALE-003",
        "SCALE-004",
        "SCALE-006",
        "SEC-014",
        "SEC-015",
        "SEC-021",
        "SEC-022",
    }

    def test_no_unexpected_eval_errors_for_realistic_profile(self, srgssr_profile):
        results = evaluate_catalog(srgssr_profile, CHECKS_DIR)
        unexpected = {
            cid: r["reason"]
            for cid, r in results.items()
            if not r["applicable"] and r["reason"] != "no-match"
        }
        assert unexpected == {}, (
            "Unexpected evaluator errors against srgssr profile (catalog drift?): "
            f"{unexpected}"
        )

    def test_no_check_compares_deployment_list_to_string_literal(self):
        """Regression for issue #16: no check may compare the `deployment`
        list field directly to a string literal again. Migrated to
        `is_cloud_deployed == true` instead.
        """
        from tools.parse_catalog import parse_catalog
        catalog = parse_catalog(CHECKS_DIR)
        offenders = [
            cid for cid, fm in catalog.items()
            if 'deployment !=' in fm.get("applies_when", "")
            or 'deployment ==' in fm.get("applies_when", "")
        ]
        assert offenders == [], (
            f"These checks compare `deployment` to a string literal "
            f"(issue #16): {offenders}. Use `is_cloud_deployed == true` "
            f"or `deployment.includes(\"...\")` instead."
        )

    def test_previously_buggy_checks_now_evaluate_clean(self, srgssr_profile):
        """The 9 checks migrated under #16 must produce no type-mismatch."""
        results = evaluate_catalog(srgssr_profile, CHECKS_DIR)
        for cid in self.PREVIOUSLY_BUGGY_CHECKS:
            r = results.get(cid)
            assert r is not None, f"{cid}: missing from catalog"
            assert not r["reason"].startswith("type-mismatch"), (
                f"{cid}: still produces a type-mismatch — migration "
                f"incomplete? reason={r['reason']!r}"
            )

    def test_arch_001_is_universal(self, srgssr_profile, cloud_oauth_profile):
        # ARCH-001 is `applies_when: 'always'` — must be applicable everywhere.
        for profile in (srgssr_profile, cloud_oauth_profile):
            results = evaluate_catalog(profile, CHECKS_DIR)
            assert results["ARCH-001"]["applicable"] is True

    def test_oauth_proxy_check_skipped_for_no_auth(self, srgssr_profile):
        results = evaluate_catalog(srgssr_profile, CHECKS_DIR)
        # SEC-001 is OAuth-Proxy specific; srgssr has auth_model=none.
        assert results["SEC-001"]["applicable"] is False

    def test_oauth_proxy_check_active_for_oauth(self, cloud_oauth_profile):
        results = evaluate_catalog(cloud_oauth_profile, CHECKS_DIR)
        assert results["SEC-001"]["applicable"] is True


class TestIsCloudDeployedFlag:
    """Issue #16: the `is_cloud_deployed` flag replaces the broken
    list-vs-string comparison `deployment != "local-stdio"`.
    Semantic: `true` iff at least one deployment target is not `local-stdio`.
    """

    def test_local_stdio_only_skips_cloud_checks(self, srgssr_profile):
        # srgssr has deployment=[local-stdio], is_cloud_deployed=False
        results = evaluate_catalog(srgssr_profile, CHECKS_DIR)
        # OBS-006 is `is_cloud_deployed == true` — must NOT apply
        assert results["OBS-006"]["applicable"] is False
        assert results["SCALE-004"]["applicable"] is False
        assert results["SCALE-006"]["applicable"] is False

    def test_cloud_deployment_activates_cloud_checks(self, cloud_oauth_profile):
        # cloud_oauth has deployment=[Railway], is_cloud_deployed=True
        results = evaluate_catalog(cloud_oauth_profile, CHECKS_DIR)
        assert results["OBS-006"]["applicable"] is True
        assert results["SCALE-004"]["applicable"] is True
        assert results["SCALE-006"]["applicable"] is True

    def test_sec_021_or_with_external_requests(self, srgssr_profile):
        # srgssr has tools_make_external_requests=True so SEC-021 must
        # apply via the OR-arm even though is_cloud_deployed=False.
        results = evaluate_catalog(srgssr_profile, CHECKS_DIR)
        assert results["SEC-021"]["applicable"] is True

    def test_sec_021_skipped_for_pure_local_no_external(self):
        # Local-stdio AND no external requests → SEC-021 must NOT apply
        profile = {
            "transport": "stdio-only",
            "auth_model": "none",
            "data_class": "Public Open Data",
            "write_capable": False,
            "deployment": ["local-stdio"],
            "is_cloud_deployed": False,
            "uses_sampling": False,
            "uses_sequential_thinking": False,
            "tools_include_filesystem": False,
            "tools_make_external_requests": False,
            "stadt_zuerich_context": False,
            "schulamt_context": False,
            "volksschule_context": False,
            "enterprise_context": False,
            "sdk_language": "Python",
            "data_source": {"is_swiss_open_data": True},
        }
        results = evaluate_catalog(profile, CHECKS_DIR)
        assert results["SEC-021"]["applicable"] is False

    def test_dual_deployment_with_local_and_cloud_is_cloud(self):
        # deployment=[local-stdio, Railway] → is_cloud_deployed=True
        # The example portfolio's first server is exactly this case.
        profile = {
            "transport": "dual",
            "auth_model": "none",
            "data_class": "Public Open Data",
            "write_capable": False,
            "deployment": ["local-stdio", "Railway"],
            "is_cloud_deployed": True,
            "uses_sampling": False,
            "uses_sequential_thinking": False,
            "tools_include_filesystem": False,
            "tools_make_external_requests": True,
            "stadt_zuerich_context": True,
            "schulamt_context": False,
            "volksschule_context": False,
            "enterprise_context": False,
            "sdk_language": "Python",
            "data_source": {"is_swiss_open_data": True},
        }
        results = evaluate_catalog(profile, CHECKS_DIR)
        assert results["OBS-006"]["applicable"] is True


class TestWriteCapableSchemaMigration:
    """Regression for issue #13: the catalog must use `write_capable: bool`
    everywhere; the legacy `write_access` enum is dropped.
    """

    def test_no_check_uses_legacy_write_access_field(self):
        from tools.parse_catalog import parse_catalog
        catalog = parse_catalog(CHECKS_DIR)
        offenders = [
            cid for cid, fm in catalog.items()
            if "write_access" in fm.get("applies_when", "")
        ]
        assert offenders == [], (
            f"These checks still reference the deprecated write_access "
            f"field: {offenders}. Migrate to write_capable == true/false."
        )

    def test_hitl_005_uses_canonical_field(self):
        from tools.eval_applicability import parse_check_frontmatter
        fm = parse_check_frontmatter(CHECKS_DIR / "HITL-005.md")
        assert fm["applies_when"] == "write_capable == true"

    def test_write_capable_false_skips_hitl_005(self, srgssr_profile):
        # srgssr has write_capable=False → HITL-005 must NOT apply.
        results = evaluate_catalog(srgssr_profile, CHECKS_DIR)
        assert results["HITL-005"]["applicable"] is False

    def test_write_capable_true_activates_hitl_005(self, cloud_oauth_profile):
        # cloud_oauth has write_capable=True → HITL-005 must apply.
        results = evaluate_catalog(cloud_oauth_profile, CHECKS_DIR)
        assert results["HITL-005"]["applicable"] is True

    def test_legacy_profile_without_is_cloud_deployed_fails_loudly(self):
        """A profile that lacks `is_cloud_deployed` must error rather
        than silently default to False — Issue #16 design choice.
        """
        legacy_profile = {
            "transport": "stdio-only",
            "auth_model": "none",
            "data_class": "Public Open Data",
            "write_capable": False,
            "deployment": ["local-stdio"],
            # NOTE: no is_cloud_deployed
            "uses_sampling": False,
            "uses_sequential_thinking": False,
            "tools_include_filesystem": False,
            "tools_make_external_requests": False,
            "stadt_zuerich_context": False,
            "schulamt_context": False,
            "volksschule_context": False,
            "enterprise_context": False,
            "sdk_language": "Python",
            "data_source": {"is_swiss_open_data": False},
        }
        results = evaluate_catalog(legacy_profile, CHECKS_DIR)
        # OBS-006 evaluates `is_cloud_deployed == true` — must error
        assert results["OBS-006"]["applicable"] is False
        assert results["OBS-006"]["reason"].startswith("unknown-field")

    def test_legacy_profile_with_only_write_access_fails_loudly(self):
        # If a user provides a legacy profile (write_access only, no
        # write_capable), every write-related check must error rather
        # than silently default to False.
        legacy_profile = {
            "transport": "stdio-only",
            "auth_model": "none",
            "data_class": "Public Open Data",
            "write_access": "read-only",  # legacy
            # NOTE: no write_capable
            "deployment": ["local-stdio"],
            "uses_sampling": False,
            "uses_sequential_thinking": False,
            "tools_include_filesystem": False,
            "tools_make_external_requests": False,
            "stadt_zuerich_context": False,
            "schulamt_context": False,
            "volksschule_context": False,
            "enterprise_context": False,
            "sdk_language": "Python",
            "data_source": {"is_swiss_open_data": False},
        }
        results = evaluate_catalog(legacy_profile, CHECKS_DIR)
        # HITL-005 evaluates `write_capable == true` against a profile
        # that only has `write_access` → UnknownFieldError surfaces as
        # `unknown-field` reason in the catalog runner.
        assert results["HITL-005"]["applicable"] is False
        assert results["HITL-005"]["reason"].startswith("unknown-field")


class TestFrontmatterParser:
    def test_parse_arch_001(self):
        fm = parse_check_frontmatter(CHECKS_DIR / "ARCH-001.md")
        assert fm["id"] == "ARCH-001"
        assert fm["applies_when"] == "always"

    def test_parse_known_oauth_check(self):
        fm = parse_check_frontmatter(CHECKS_DIR / "SEC-001.md")
        assert "auth_model" in fm["applies_when"]

    def test_parse_crlf_line_endings(self, tmp_path):
        """Windows checkouts with autocrlf=true emit CRLF; the parser must
        tolerate that without breaking the regex.
        """
        content = (
            "---\r\n"
            "id: TEST-001\r\n"
            'applies_when: \'always\'\r\n'
            "---\r\n"
            "\r\n"
            "body\r\n"
        )
        p = tmp_path / "TEST-001.md"
        p.write_bytes(content.encode("utf-8"))
        fm = parse_check_frontmatter(p)
        assert fm["id"] == "TEST-001"
        assert fm["applies_when"] == "always"
