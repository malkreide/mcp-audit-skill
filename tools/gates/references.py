"""Die Vorlagen-Module: gibt es sie, und lassen sie sich ueberhaupt lesen?

Zusammengefuehrt aus `mcp-data-source-probe-skill` und
`mcp-data-fidelity-skill` — Familie G9 des Merge-Plans.

WAS DIESE PRUEFUNG NICHT TUT, und warum das die Grenze ist: Sie kompiliert,
sie importiert nicht. Vorlagen-Code referenziert Namen, die erst im
Zielserver existieren (`log`, `ctx`, Handler-Symbole) — ein Import fiele
darueber, und zwar zu Recht, aber nicht als Aussage ueber die Vorlage.
`compile()` prueft die Syntax und sonst nichts, und genau das ist hier die
Frage: Ist die Vorlage noch lesbar, oder hat ein Umbau sie zerbrochen?

(`mcp-data-source-probe-skill` fuehrt daneben eine eigene Pruefung, die die
Referenzen WIRKLICH importiert — die haengt an dessen `requirements` und
zieht in `tools/suites/` um, nicht hierher.)
"""

from __future__ import annotations

from pathlib import Path

from tools.harness import CheckFailed


def python_sources(root: Path, *, source_dirs: tuple[str, ...]) -> list[Path]:
    """Die Vorlagen-Module, oder ein Befund, falls es keine gibt.

    Ueber das Dateisystem statt ueber eine gepflegte Liste: Eine weitere
    Vorlage ist damit automatisch abgedeckt. Eine Abdeckungsgrenze, die
    niemand pflegen muss, altert nicht.

    DER WAECHTER STEHT *IN* DER PRUEFUNG und nicht als eigener Schritt
    daneben: Verschwindet ein Verzeichnis, haette diese Pruefung nichts mehr
    zu tun — und ein leeres Ergebnis als Erfolg zu melden ist genau der
    Fehler, gegen den sie gerichtet ist. So kann der Waechter nicht
    unabhaengig von dem verschwinden, was er bewacht.
    """
    if not source_dirs:
        raise CheckFailed(
            "Kein Verzeichnis genannt — dann prueft diese Pruefung nichts und "
            "meldete genau das als Erfolg."
        )

    fehlend = [name for name in source_dirs if not (root / name).is_dir()]
    if fehlend:
        raise CheckFailed(
            f"Verzeichnis fehlt: {fehlend} — umbenannt oder geloescht. Ohne es "
            "hat diese Pruefung nichts zu lesen und meldete das als Erfolg."
        )

    quellen = sorted(
        pfad
        for name in source_dirs
        for pfad in (root / name).glob("*.py")
        if not pfad.name.startswith("_")
    )
    if not quellen:
        raise CheckFailed(
            f"Kein `*.py` unter {list(source_dirs)} — entweder sind die "
            "Vorlagen weg, oder sie heissen anders. Beides laesst diese "
            "Pruefung ins Leere laufen."
        )
    return quellen


def python_syntax(root: Path, *, source_dirs: tuple[str, ...]) -> str:
    """G9 — jede Vorlage laesst sich uebersetzen.

    Uebersetzt wird OHNE Bytecode zu schreiben: `compileall` legte sonst
    `__pycache__/` neben die Quellen, und genau daraus wurde in einem der
    Herkunftsrepos schon einmal eine eingecheckte `.pyc`. Eine Pruefung, die
    die naechste rot macht, ist kein Befund, sondern ein Eigentor.
    """
    quellen = python_sources(root, source_dirs=source_dirs)
    for pfad in quellen:
        text = pfad.read_text(encoding="utf-8")
        try:
            compile(text, str(pfad), "exec")
        except SyntaxError as exc:
            raise CheckFailed(
                f"{pfad.relative_to(root).as_posix()}: Syntaxfehler in Zeile "
                f"{exc.lineno} — {exc.msg}"
            ) from exc
    wort = "Vorlagen-Modul laesst" if len(quellen) == 1 else "Vorlagen-Module lassen"
    return f"{len(quellen)} {wort} sich uebersetzen"
