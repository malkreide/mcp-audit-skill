"""Tests für den Abgleich handgeschriebener Zahlen gegen `summary.json`.

Der Test, auf den es ankommt, ist
`test_richtige_summe_bei_falscher_zusammensetzung_faellt_auf`. Genau dieser Fall
ist real passiert: eine Vorhersage 30 / 4 / 2 gegen ein gemessenes 30 / 5 / 1.
Die Summe stimmte, der Satz las sich bestätigt, und das eine Finding, das von
`fail` nach `partial` gewandert war, verschwand. Eine Prüfung, die nur die
Gesamtzahl vergleicht, lässt das durch.

Der zweite unverzichtbare Test ist
`test_ein_text_ohne_erkannte_angabe_ist_kein_bestehen` — die Anker-Frage. Wenn
sich ein Wortlaut ändert und das Muster ins Leere greift, darf daraus kein
grünes Ergebnis werden.
"""

from __future__ import annotations

import json

import pytest

from tools.check_reported_numbers import (
    check_files,
    check_text,
    extract_claims,
    main,
)

SUMMARY = {
    "totals": {"by_status": {"pass": 30, "partial": 5, "fail": 1, "todo": 2}},
    "findings": {"expected_count": 6},
}


class TestDerFallDerDenAnlassGab:
    def test_richtige_summe_bei_falscher_zusammensetzung_faellt_auf(self):
        """30+4+2 = 36 = 30+5+1. Die Summe verrät nichts, die Aufteilung schon."""
        text = "Der Lauf ergab 30 pass, 4 partial und 2 fail."

        report = check_text(text, SUMMARY, "prognose.md")

        falsch = {
            (m["status"], m["claimed"], m["actual"]) for m in report["mismatches"]
        }
        assert falsch == {("partial", 4, 5), ("fail", 2, 1)}
        assert not any(m["status"] == "pass" for m in report["mismatches"]), (
            "die richtige Angabe darf nicht mitgemeldet werden"
        )

    def test_ein_text_ohne_erkannte_angabe_ist_kein_bestehen(self):
        """Kein Treffer heisst «nicht verglichen», nicht «in Ordnung»."""
        report = check_text(
            "Der Server wurde geprüft und ist in Ordnung.", SUMMARY, "x.md"
        )

        assert report["claims_found"] == 0
        assert report["checked"] is False
        assert report["mismatches"] == []

    def test_stimmige_angaben_erzeugen_keinen_befund(self):
        text = "30 pass, 5 partial, 1 fail, 6 Findings dokumentiert."
        report = check_text(text, SUMMARY, "ok.md")
        assert report["mismatches"] == []
        assert report["claims_found"] == 4


class TestErkennung:
    @pytest.mark.parametrize(
        ("text", "status", "zahl"),
        [
            ("30 pass", "pass", 30),
            ("30 bestanden", "pass", 30),
            ("5 partial", "partial", 5),
            ("5 teilweise", "partial", 5),
            ("1 fail", "fail", 1),
            ("2 todo", "todo", 2),
            ("3 not_verified", "not_verified", 3),
        ],
    )
    def test_deutsche_und_englische_statuswoerter(self, text, status, zahl):
        claims = extract_claims(text)
        assert claims and claims[0]["status"] == status
        assert claims[0]["claimed"] == zahl

    def test_eine_umgebrochene_angabe_wird_trotzdem_erkannt(self):
        """`grep` ist zeilenweise; der Fliesstext bricht bei 88 Zeichen um.

        Genau daran ist in diesem Portfolio schon einmal eine Prüfung
        gescheitert — sie meldete «fehlt», während der Satz dastand.
        """
        claims = extract_claims("Der Lauf ergab 30\npass und 5\npartial.")
        assert {(c["status"], c["claimed"]) for c in claims} == {
            ("pass", 30),
            ("partial", 5),
        }

    def test_ein_mehrwortiges_statuswort_ueberlebt_den_umbruch(self):
        """Nachgetragen, weil eine Mutation überlebt hat.

        Das Entfernen der Whitespace-Normalisierung brach zuerst keinen Test:
        `\\s+` im Muster deckt den Umbruch zwischen Zahl und Wort ohnehin ab.
        Wirksam wird die Normalisierung erst **innerhalb** eines mehrwortigen
        Statusworts — `nicht verifiziert` trägt ein Leerzeichen als Literal,
        und ein Literal matcht keinen Zeilenumbruch. Ohne diesen Fall behauptet
        die Normalisierung einen Nutzen, den nichts belegt.
        """
        claims = extract_claims("Es blieben 3 nicht\nverifiziert.")
        assert [(c["status"], c["claimed"]) for c in claims] == [("not_verified", 3)]

    @pytest.mark.parametrize(
        "text",
        [
            "Version 5 partial-release",  # kein eigenständiges Statuswort
            "v1.5 pass",  # Versionsnummer davor
            "issue #30 passt",  # anderes Wort
        ],
    )
    def test_keine_falschtreffer_auf_versionen_und_teilwoertern(self, text):
        """Gegenprobe zur Erkennung: ein zu weites Muster meldet überall etwas.

        `1.5 pass` darf nicht als «5 pass» gelesen werden, sonst erzeugt das
        Werkzeug Befunde aus Versionsnummern und wird abgeschaltet.
        """
        assert extract_claims(text) == []

    def test_findings_werden_gegen_expected_count_geprueft(self):
        assert check_text("6 Findings", SUMMARY, "x")["mismatches"] == []
        schlecht = check_text("9 Findings", SUMMARY, "x")["mismatches"]
        assert schlecht and schlecht[0]["actual"] == 6


class TestMehrereDateien:
    def _schreib(self, tmp_path, name, inhalt):
        p = tmp_path / name
        p.write_text(inhalt, encoding="utf-8")
        return p

    def test_ein_ungeprueftes_dokument_macht_den_lauf_nicht_konsistent(self, tmp_path):
        gut = self._schreib(tmp_path, "gut.md", "30 pass")
        stumm = self._schreib(tmp_path, "stumm.md", "Alles bestens.")

        report = check_files(SUMMARY, [gut, stumm])

        assert report["mismatches"] == []
        assert report["unchecked"] == [str(stumm)]
        assert report["consistent"] is False, (
            "eine Datei ohne erkannte Angabe darf nicht als geprüft durchgehen"
        )

    def test_alles_stimmig_ist_konsistent(self, tmp_path):
        a = self._schreib(tmp_path, "a.md", "30 pass")
        b = self._schreib(tmp_path, "b.md", "5 partial und 1 fail")
        assert check_files(SUMMARY, [a, b])["consistent"] is True


class TestCLI:
    def _lauf(self, tmp_path, capsys, inhalt, summary=None):
        s = tmp_path / "summary.json"
        s.write_text(json.dumps(summary or SUMMARY), encoding="utf-8")
        d = tmp_path / "doc.md"
        d.write_text(inhalt, encoding="utf-8")
        code = main([str(s), str(d)])
        return code, capsys.readouterr()

    def test_exit_null_wenn_alles_stimmt(self, tmp_path, capsys):
        code, out = self._lauf(tmp_path, capsys, "30 pass, 5 partial, 1 fail")
        assert code == 0
        assert "ok —" in out.out

    def test_exit_eins_bei_abweichung_mit_gemessenem_wert_im_text(
        self, tmp_path, capsys
    ):
        code, out = self._lauf(tmp_path, capsys, "30 pass, 4 partial")
        assert code == 1
        assert "ABWEICHUNG" in out.out
        assert "5" in out.out, "der gemessene Wert muss dastehen, nicht nur der falsche"

    def test_exit_eins_wenn_nichts_erkannt_wurde(self, tmp_path, capsys):
        code, out = self._lauf(tmp_path, capsys, "Keine Zahlen hier.")
        assert code == 1
        assert "UNGEPRUEFT" in out.out

    def test_exit_zwei_ohne_summary(self, tmp_path, capsys):
        d = tmp_path / "doc.md"
        d.write_text("30 pass", encoding="utf-8")
        code = main([str(tmp_path / "fehlt.json"), str(d)])
        assert code == 2
        assert "nicht gefunden" in capsys.readouterr().err

    def test_json_ausgabe_ist_maschinenlesbar(self, tmp_path, capsys):
        s = tmp_path / "summary.json"
        s.write_text(json.dumps(SUMMARY), encoding="utf-8")
        d = tmp_path / "doc.md"
        d.write_text("30 pass, 4 partial", encoding="utf-8")
        main([str(s), str(d), "--format", "json"])
        payload = json.loads(capsys.readouterr().out)
        assert payload["consistent"] is False
        assert payload["mismatches"][0]["actual"] == 5
