# Checks greifen semantisch, nicht über die Form

Diese Seite ist eine Regel für alle, die Checks in diesen Katalog schreiben. Sie ist bewusst **kein** Check: Sie beschreibt keine Eigenschaft eines auditierten Servers, sondern eine Eigenschaft unserer eigenen Prüfungen. Ein Check, der sie einfordert, hätte keinen Server, auf den er zeigen könnte — er würde auf `checks/` zeigen, und damit wäre der Katalog Gegenstand seiner selbst.

## Die Regel

> Ein Check prüft, was etwas **bedeutet**, nicht, wie es **aussieht**.

Der Unterschied ist keine Stilfrage. Er entscheidet, ob ein Befund gelesen oder weggeklickt wird.

## Der Vorfall

Der erste Versions-Scanner in diesem Repo suchte nach Versionsnummern über ihre Gestalt: Ziffern, getrennt durch Punkte.

```python
VERSION = re.compile(r"\d+\.\d+\.\d+")     # sieht aus wie eine Version
```

Was er fand:

| Fund | Was es wirklich war |
|---|---|
| `127.0.0.1` | eine Loopback-Adresse |
| `10.0.0.0/8` | ein privater Adressbereich |
| `0.0.0.0` | eine Bind-Adresse |
| `1.2.3` | ein Beispiel in einem Docstring |

Alle vier passen auf das Muster. Keiner ist eine Versionsnummer. Ein Report, der mit diesen vier Zeilen beginnt, hat sein Publikum verloren, bevor der fünfte Fund — ein echter — überhaupt gelesen wird.

## Warum das schlimmer ist als ein fehlender Check

Ein fehlender Check findet nichts. Ein formbasierter Check findet das Falsche, und das kostet mehr als nichts:

1. **Rauschen wird weggeklickt, und zwar pauschal.** Wer dreimal einen Befund als Fehlalarm abgetan hat, liest den vierten nicht mehr. Ab da ist der Check nicht wirkungslos, sondern schädlich — er verdeckt die Fälle, für die er gebaut wurde.
2. **Die Reaktion ist das Ausschalten, nicht das Nachschärfen.** Ein Muster, das zu viel findet, wird abgeschaltet oder mit Ausnahmen zugeschüttet. Beides endet an derselben Stelle: Der Check läuft und prüft nichts mehr — dieselbe Fehlerklasse, gegen die `OPS-005` steht.
3. **Ein Fehlalarm sieht aus wie ein Befund.** Wer ihn «behebt», ändert korrekten Code. Der Scanner oben hätte jemanden dazu gebracht, an einer Bind-Adresse zu drehen.

## Der Test beim Schreiben eines Checks

Vor dem Muster steht die Frage: **Woran erkenne ich das Gemeinte, wenn die Form mehrdeutig ist?** Drei brauchbare Antworten:

**An der Position.** Nicht «eine Zeichenkette, die wie eine Version aussieht», sondern «der Wert von `version` in `server.json`», «die rechte Seite einer Zuweisung an `__version__`». Der Ort trägt die Bedeutung, die der Gestalt fehlt. So macht es `IDENT-002`: verankert auf `__version__\s*=`, nicht auf `\d+\.\d+`.

**Am Kontext, der die Alternativen ausschliesst.** `SDK-006` sucht camelCase-Annotations mit führendem Punkt (`\.readOnlyHint`), weil nur der **Attributzugriff** unter 2.x bricht — dasselbe Wort in einem Dict-Literal ist gültig. Und der Suchpfad ist `src/ tests/` eines Python-Servers statt eines repo-weiten `grep -r`, weil dasselbe Wort in `.ts`-Dateien richtig ist.

**Am Verhalten statt am Text.** Die stärkste Form: nicht lesen, sondern ausführen. `DEP-001` liest nicht die Range, sondern lässt auflösen und schaut, was herauskommt. `ARCH-022` liest nicht den Importgraphen, sondern importiert kalt und warm. `OBS-008` liest nicht den Logging-Aufruf, sondern startet den Server und sieht auf stderr nach. Ein Verhalten hat keine Gestalt, die man verwechseln könnte.

Lässt sich keine dieser drei Antworten geben, ist der Befund noch nicht scharf genug für einen Check. Dann gehört er hierher — in `docs/` — oder in die Beschreibung eines bestehenden Checks, nicht in ein Muster.

## Wenn die Form doch das Beste ist, was verfügbar ist

Manchmal gibt es keinen semantischen Anker, und ein grobes Muster ist trotzdem nützlich — als **Kandidatenliste**. Dann gilt:

- Die Ausgabe wird als Kandidatenliste **bezeichnet**, nicht als Befundliste. `DEP-001` schreibt das ausdrücklich hin: «Die Ausgabe ist eine Kandidatenliste, kein Befund.»
- Die Einordnung jedes Kandidaten ist Teil der Evidenz. Eine Liste ohne Einordnung ist der Grund, warum solche Checks als Rauschen abgetan werden.
- Und die **negative Kontrolle** gehört dazu: Ein Muster, das nichts findet, kann bedeuten, dass nichts da ist — oder dass es ins Leere greift. Ohne Gegenprobe sind die beiden nicht zu unterscheiden, und die bequemere Lesart gewinnt.

Diese drei Punkte sind der Preis dafür, formbasiert zu prüfen. Wer ihn nicht zahlen will, prüft semantisch oder gar nicht.

## Verwandtes

- `OPS-005` — «nicht geprüft» ist kein Pass. Ein abgeschalteter Check und ein bestandener sehen im Report gleich aus, wenn niemand den Unterschied festhält
- `docs/applies-when-dsl.md` — dieselbe Haltung eine Ebene tiefer: keine `eval()`-Semantik, keine stille Umdeutung, ein unbekanntes Feld ist ein Fehler und kein `False`
- `tests/test_negative_control.py` — die Regel zur negativen Kontrolle, wie sie in `SKILL.md` festgehalten und dort erzwungen wird
- `tests/test_transport_vocabulary.py` — dort in der Kopfzeile: «Jede Prüfung scheitert auch, wenn ihr Muster gar nichts findet.» Genau der Fall, den ein formbasiertes Muster still verliert
