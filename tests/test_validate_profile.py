"""Tests for tools/validate_profile.py — placeholder + schema gate for Step 1."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.validate_profile import (
    _is_placeholder_value,
    main,
    validate_profile,
)


def _good_profile() -> dict:
    return {
        "transport": "stdio-only",
        "auth_model": "none",
        "data_class": "Public Open Data",
        "write_capable": False,
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


# ---------------------------------------------------------------------------
# Placeholder detection
# ---------------------------------------------------------------------------


class TestPlaceholderDetection:
    @pytest.mark.parametrize(
        "value",
        [
            "...",
            "  ...  ",
            "<placeholder>",
            "<TODO>",
            "<>",
            "TODO",
            "todo",
            "fixme",
            "FIXME",
            "XXX",
            "",
            "   ",
            None,
        ],
    )
    def test_recognises_placeholder(self, value):
        assert _is_placeholder_value(value) is True, f"value={value!r}"

    @pytest.mark.parametrize(
        "value",
        [
            "stdio-only",
            "Public Open Data",
            "API-Key",
            "0",
            0,
            False,
            True,
        ],
    )
    def test_real_values_pass(self, value):
        assert _is_placeholder_value(value) is False, f"value={value!r}"

    def test_empty_list_is_placeholder(self):
        assert _is_placeholder_value([]) is True

    def test_list_with_placeholder_member(self):
        assert _is_placeholder_value(["..."]) is True


# ---------------------------------------------------------------------------
# Whole-profile validation
# ---------------------------------------------------------------------------


class TestValidateProfile:
    def test_clean_profile_passes(self):
        report = validate_profile(_good_profile())
        assert report["consistent"] is True
        assert report["missing"] == []
        assert report["placeholder"] == []
        assert report["type_mismatch"] == []

    def test_template_paste_caught(self):
        # Replays the issue #14 scenario: user pastes the template with
        # `...` placeholders.
        bad = _good_profile()
        bad["transport"] = "..."
        bad["auth_model"] = "..."
        bad["data_class"] = "..."
        report = validate_profile(bad)
        assert report["consistent"] is False
        assert set(report["placeholder"]) >= {"transport", "auth_model", "data_class"}

    def test_missing_required_field(self):
        bad = _good_profile()
        del bad["transport"]
        report = validate_profile(bad)
        assert "transport" in report["missing"]

    def test_wrong_type_for_bool(self):
        bad = _good_profile()
        bad["write_capable"] = "yes"
        report = validate_profile(bad)
        mismatches = {m["field"] for m in report["type_mismatch"]}
        assert "write_capable" in mismatches

    def test_wrong_type_for_list(self):
        bad = _good_profile()
        bad["deployment"] = "local-stdio"
        report = validate_profile(bad)
        mismatches = {m["field"] for m in report["type_mismatch"]}
        assert "deployment" in mismatches

    def test_data_source_nested_field_checked(self):
        bad = _good_profile()
        bad["data_source"] = {}  # missing is_swiss_open_data
        report = validate_profile(bad)
        assert "data_source.is_swiss_open_data" in report["missing"]

    def test_data_source_placeholder_value(self):
        bad = _good_profile()
        bad["data_source"]["is_swiss_open_data"] = "..."
        report = validate_profile(bad)
        assert "data_source.is_swiss_open_data" in report["placeholder"]

    def test_data_source_wrong_type(self):
        bad = _good_profile()
        bad["data_source"]["is_swiss_open_data"] = "true"  # string, not bool
        report = validate_profile(bad)
        mismatches = {m["field"] for m in report["type_mismatch"]}
        assert "data_source.is_swiss_open_data" in mismatches

    def test_non_dict_profile_rejected(self):
        report = validate_profile([])  # type: ignore[arg-type]
        assert report["consistent"] is False
        assert "error" in report

    def test_empty_deployment_list_is_placeholder(self):
        bad = _good_profile()
        bad["deployment"] = []
        report = validate_profile(bad)
        assert "deployment" in report["placeholder"]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestCli:
    def _write_profile(self, tmp_path: Path, profile: dict) -> Path:
        path = tmp_path / "profile.json"
        path.write_text(json.dumps(profile), encoding="utf-8")
        return path

    def test_clean_returns_zero(self, tmp_path, capsys):
        path = self._write_profile(tmp_path, _good_profile())
        rc = main([str(path)])
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["consistent"] is True

    def test_placeholder_returns_one(self, tmp_path):
        bad = _good_profile()
        bad["transport"] = "..."
        path = self._write_profile(tmp_path, bad)
        rc = main([str(path)])
        assert rc == 1

    def test_missing_file_returns_two(self, tmp_path):
        rc = main([str(tmp_path / "nope.json")])
        assert rc == 2

    def test_writes_out_file(self, tmp_path):
        path = self._write_profile(tmp_path, _good_profile())
        out_path = tmp_path / "report.json"
        rc = main([str(path), "--out", str(out_path)])
        assert rc == 0
        assert out_path.exists()
        report = json.loads(out_path.read_text(encoding="utf-8"))
        assert report["consistent"] is True


# ---------------------------------------------------------------------------
# Closed vocabularies (enum_mismatch)
# ---------------------------------------------------------------------------


class TestClosedVocabularies:
    """Ein unbekannter *Wert* muss laut scheitern, nicht still filtern.

    Der Validator liess Enum-Werte bewusst durch, mit der Begründung, der
    Evaluator melde sie ohnehin «loudly». Das stimmte nicht: `transport:
    HTTP` ist ein gewöhnlicher String, `transport == "HTTP/SSE"` ergibt
    schlicht `False`, und vier Checks fielen weg, ohne dass irgendwo eine
    Zeile darüber stand.

    `test_unknown_transport_silently_drops_checks` hält genau diese
    Eigenschaft des Evaluators fest — nicht um sie zu beklagen, sondern
    weil sie die Existenzberechtigung des Gates ist. Verschwindet sie
    einmal (etwa weil der Evaluator Werte prüft), fällt der Test auf,
    und dann gehört dieses Gate neu begründet oder entfernt.
    """

    def test_canonical_transports_pass(self):
        for value in ("stdio-only", "dual", "HTTP/SSE"):
            profile = _good_profile()
            profile["transport"] = value
            report = validate_profile(profile)
            assert report["consistent"] is True, f"{value!r} sollte gültig sein"
            assert report["enum_mismatch"] == []

    @pytest.mark.parametrize(
        "value", ["HTTP", "SSE", "http/sse", "streamable-http", "stdio"]
    )
    def test_unknown_transport_is_reported(self, value):
        profile = _good_profile()
        profile["transport"] = value
        report = validate_profile(profile)
        assert report["consistent"] is False, f"{value!r} sollte abgelehnt werden"
        assert report["enum_mismatch"] == [
            {
                "field": "transport",
                "allowed": ["stdio-only", "dual", "HTTP/SSE"],
                "got": value,
            }
        ]

    def test_unknown_transport_returns_exit_one(self, tmp_path):
        bad = _good_profile()
        bad["transport"] = "HTTP"
        path = tmp_path / "profile.json"
        path.write_text(json.dumps(bad), encoding="utf-8")
        assert main([str(path)]) == 1

    def test_missing_transport_is_not_also_an_enum_error(self):
        """Ein Defekt, zweimal benannt, liest sich wie zwei Defekte."""
        profile = _good_profile()
        del profile["transport"]
        report = validate_profile(profile)
        assert "transport" in report["missing"]
        assert report["enum_mismatch"] == []

    def test_placeholder_transport_is_not_also_an_enum_error(self):
        profile = _good_profile()
        profile["transport"] = "..."
        report = validate_profile(profile)
        assert "transport" in report["placeholder"]
        assert report["enum_mismatch"] == []

    def test_wrong_type_transport_is_not_also_an_enum_error(self):
        profile = _good_profile()
        profile["transport"] = ["dual"]
        report = validate_profile(profile)
        assert [m["field"] for m in report["type_mismatch"]] == ["transport"]
        assert report["enum_mismatch"] == []

    def test_open_vocabularies_stay_open(self):
        """`auth_model` / `data_class` sind bewusst nicht gepinnt.

        Sie tragen dokumentierte Werte, die kein Check einzeln abfragt
        (`OIDC`, `Verwaltungsdaten`) — abgedeckt von den `!=`-Klauseln.
        Ein Wert, den niemand vergleicht, ist dort eine Lücke im Katalog,
        kein Fehler im Profil.
        """
        profile = _good_profile()
        profile["auth_model"] = "OIDC"
        profile["data_class"] = "Verwaltungsdaten"
        assert validate_profile(profile)["consistent"] is True

    def test_unknown_transport_silently_drops_checks(self):
        """Die Eigenschaft, gegen die dieses Gate schützt — festgenagelt."""
        from tools.eval_applicability import evaluate

        profile = _good_profile()
        profile["transport"] = "HTTP"
        # Kein Fehler, kein Hinweis — nur ein stilles False.
        assert evaluate('transport == "HTTP/SSE"', profile) is False
        assert evaluate('transport != "stdio-only"', profile) is True
