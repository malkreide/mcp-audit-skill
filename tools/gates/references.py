"""Die Vorlagen-Module: gibt es sie, und lassen sie sich ueberhaupt lesen?

Zusammengefuehrt aus `mcp-data-source-probe-skill` und
`mcp-data-fidelity-skill` — Familie G9 des Merge-Plans.

WAS DIESE PRUEFUNG NICHT TUT, und warum das die Grenze ist: Sie kompiliert,
sie importiert nicht. Vorlagen-Code referenziert Namen, die erst im
Zielserver existieren (`log`, `ctx`, Handler-Symbole) — ein Import fiele
darueber, und zwar zu Recht, aber nicht als Aussage ueber die Vorlage.
`compile()` prueft die Syntax und sonst nichts, und genau das ist hier die
Frage: Ist die Vorlage noch lesbar, oder hat ein Umbau sie zerbrochen?

SEIT PHASE 5 STEHT DIE IMPORT-HAELFTE DANEBEN, und sie hat einen zweiten
Gegenstand bekommen — genau die Schwelle, ab der dieses Repository
verallgemeinert. Sie kam aus `mcp-data-source-probe-skill` («laedt die Vorlage
ueberhaupt?») und hat mit dem Einzug von `mcp-transport-hardening-skill` einen
zweiten Anlass: dort haelt derselbe Import die Vorlage gegen die
SDK-OBERFLAECHE. Zwei Gruende, ein Mechanismus.

WAS DER IMPORT KOSTET, und warum er nicht die Vorgabe ist: Er braucht die
Laufzeit-Pakete der Vorlagen im Interpreter (`requirements-reference.txt`).
Fuer offene Vorlagen, die Namen aus der Zielumgebung nennen, faellt er
ausserdem — `mcp-data-fidelity` bindet ihn deshalb NICHT.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from tools.harness import CheckFailed, pycache_to_temp


def python_sources(
    root: Path, *, source_dirs: tuple[str, ...], skip_private: bool = True
) -> list[Path]:
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
        if not (skip_private and pfad.name.startswith("_"))
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


def python_imports(
    root: Path,
    *,
    source_dirs: tuple[str, ...],
    praefix: str,
) -> str:
    """Die Vorlagen lassen sich LADEN, nicht bloss uebersetzen.

    `python_syntax` prueft, ob die Datei parst. Das ist weniger, als es klingt:
    Ein Import auf ein Modul, das es nicht mehr gibt, ein Dekorator, der beim
    Auswerten wirft, ein Tippfehler in einem Namen auf Modulebene — alles das
    parst einwandfrei und faellt erst beim Importieren auf.

    `praefix` haelt die Modulnamen der Suiten auseinander. Beide Vorlagenbaeume
    fuehren eine `patterns.py`; ohne Praefix ueberschriebe der zweite Import
    den ersten in `sys.modules`, und die zweite Suite pruefte die Datei der
    ersten.
    """
    # `skip_private=False`, und das ist der einzige Unterschied zur
    # Syntax-Haelfte. Er ist GEMESSEN und nicht gewaehlt: Beim Auslagern der
    # Mechanik in dieses Gate uebernahm sie zunaechst den `_`-Filter — und vier
    # Mutationen von `probe/3`, die eine kaputte `_mutant.py` ablegen, wurden
    # damit GRUEN. Eine Vorlage mit fuehrendem Unterstrich wird genauso kopiert
    # wie jede andere; dass sie laedt, ist dieselbe Zusage.
    #
    # Fuer die Syntax-Haelfte bleibt der Filter richtig: Sie faehrt ueber ALLE
    # drei Vorlagenbaeume, und ein `__init__.py` ist dort keine Vorlage.
    quellen = python_sources(root, source_dirs=source_dirs, skip_private=False)
    zeilen = []
    with pycache_to_temp():
        for pfad in quellen:
            name = f"{praefix}{pfad.stem}"
            spec = importlib.util.spec_from_file_location(name, pfad)
            if spec is None or spec.loader is None:
                raise CheckFailed(f"{pfad.name}: kein Importer zustaendig")
            modul = importlib.util.module_from_spec(spec)
            sys.modules[name] = modul
            try:
                spec.loader.exec_module(modul)
            except ModuleNotFoundError as exc:
                raise CheckFailed(
                    f"{pfad.name}: Import scheitert an fehlendem Paket "
                    f"{exc.name!r}.\n"
                    "  Ist es eine Abhaengigkeit der Vorlage, gehoert es "
                    "gepinnt nach requirements-reference.txt:\n"
                    "    pip install -r requirements-reference.txt\n"
                    "  Ist es das nicht, importiert die Vorlage etwas, das "
                    "beim Kopieren nirgends existiert."
                ) from exc
            except BaseException as exc:
                # BaseException, nicht Exception: Eine Vorlage, die beim Import
                # `sys.exit` ruft, ist genauso kaputt wie eine, die wirft — nur
                # wuerde ein SystemExit sonst den ganzen Lauf mitnehmen.
                if isinstance(exc, KeyboardInterrupt):
                    raise
                raise CheckFailed(
                    f"{pfad.name}: Import scheitert — {type(exc).__name__}: {exc}"
                ) from exc
            finally:
                sys.modules.pop(name, None)

            oeffentlich = [n for n in vars(modul) if not n.startswith("_")]
            if not oeffentlich:
                raise CheckFailed(
                    f"{pfad.name}: importiert, stellt aber keinen Namen bereit "
                    "— eine Vorlage ohne kopierbares Symbol ist keine Vorlage."
                )
            zeilen.append(
                f"{pfad.name}: importiert, {len(oeffentlich)} oeffentliche Namen"
            )

    zeilen.append(f"{len(quellen)} Vorlage(n) unter {list(source_dirs)} importierbar")
    return "\n".join(zeilen)
