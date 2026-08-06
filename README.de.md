# mcp-data-fidelity-skill

![Version](https://img.shields.io/badge/version-1.7.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Claude Skill](https://img.shields.io/badge/Claude-Skill-orange)

> Claude Skill für MCP-Server-Tools, die eine externe Datenquelle abfragen — damit ein Server nicht still weniger liefert, als die Quelle hat.

🇬🇧 [English Version](README.md)

## Übersicht

Companion zu Anthropics `mcp-builder`. Dessen Best Practices decken ab, ob ein Server **korrekt gebaut** ist — Naming, Annotations, Pagination, Transport, Fehlerbehandlung. Dieser Skill deckt die Frage daneben ab: **liefert er, was die Quelle tatsächlich hat?**

Das ist eine eigene Fehlerklasse, weil sie still ist. HTTP 200, wohlgeformtes JSON, grüne Tests — und inhaltlich falsch. Ein Server, der zwei Prozent des Bestands durchsucht und das nicht meldet, produziert Antworten, die niemand als falsch erkennt.

Die Leitfrage bei jedem datenabfragenden Tool: *Wenn dieses Tool nichts findet — kann ich unterscheiden, ob es nichts gibt oder ob ich falsch gefragt habe?* Ist die Antwort nein, greift eine der zehn Regeln. Und die Stufe darunter, seit Regel 10: *und wenn ich falsch gefragt habe — komme ich von hier zur richtigen Frage?*

## Die zehn Regeln

Die Regeln 1–6 und 10 stammen aus Vorfällen, die Regeln 7–9 aus der MCP-Spec 2026-07-28 — der Unterschied wird benannt statt geglättet, hier wie in `SKILL.md`. Die Nummerierung folgt der Reihenfolge, in der die Regeln dazugekommen sind, nicht dieser Gruppierung.

1. **Scope-Parameter explizit senden, nie erben.** Ein weggelassener optionaler Filter bedeutet oft nicht «unbeschränkt», sondern einen willkürlichen Teilausschnitt — eine Tatsache, die ausschliesslich in der Parameterbeschreibung der Spec steht und an einem funktionierenden Call nicht erkennbar ist. Umgekehrt gilt: Wer den Recall bewusst verengt (exakt statt Wildcard, kein Fuzzy), muss die Rubriken oder Datenklassen nennen, die das Risiko tragen, **und** aus der Scope-Aufzählung belegen, dass sie erreichbar sind. Eine Begründung, die für jede beliebige Quelle wortgleich dastünde, ist an nichts gekoppelt.
2. **Parameter-Gruppen vollständig senden.** Sendet man nur einige Mitglieder einer Gruppe, behalten die übrigen ihren serverseitigen Default. Das Argument kann dann nur erweitern, nie einschränken — ein No-op, der wie Steuerung aussieht.
3. **Die Leermenge trägt einen nächsten Schritt.** Null Treffer sind mehrdeutig. Das Resultat braucht ein konkretes `hint`-Feld — im Tool-Result, nicht im README. Ein Transport- oder Autorisierungsfehler ist keine Leermenge und darf nie als solche formatiert werden — er trägt einen anderen nächsten Schritt: Konfiguration prüfen, nicht Suche verbreitern.
4. **Die Tool-Description ist eine Halluzinations-Oberfläche.** Eine Formulierung, die eine Leermenge *erklärt*, erzeugt Konfabulation zuverlässiger als gar keine Formulierung. Zum Nachfassen auffordern, nie eine Schlussfolgerung lizenzieren.
5. **Query-Syntax in die Description, Recall in die Tests.** Abfragesprache und Matching-Granularität dokumentieren; Recall über Live-Untergrenzen absichern, denn ein Mock bildet die Annahme ab, mit der er geschrieben wurde.
6. **Die Antwort auf Struktur prüfen, nicht durchgreifen.** `payload.get("servers", [])` macht aus einer Strukturänderung upstream ein gültig aussehendes leeres Resultat. Ein Schema-Fehler gehört in den Fehlerkanal, nicht in eine leere Liste.
7. **Totale, dokumentierte Sortierreihenfolge.** Ein Relevanz-Score hat Ties, und eine instabile Ordnung über Seitengrenzen hinweg *verliert Treffer* — dieselbe stille Unvollständigkeit wie Regel 1, nur beim Blättern statt beim Filtern entstanden. Gilt auf jeder Spec-Version; auf 2026-07-28 entscheidet sie zusätzlich, ob ein Reconnect den Prompt-Cache des Clients behält.
8. **Ehrliches `ttlMs`.** Nie länger als die tatsächliche Quellen-Frische: Ein `ttlMs`, das die nächste Aktualisierung überdauert, lässt den Client eine Antwort ausliefern, von der der Server schon wusste, dass sie überholt sein wird. Aus `source_freshness` ableiten — und `cacheScope` gegen `requires_credentials` prüfen: Ein zu weiter Scope auf einem credential-abhängigen Resultat ist ein Leck, kein Frischeproblem.
9. **`input_required` ist keine leere Antwort.** Eine MRTR-Rückfrage sieht erfolgreich aus — HTTP 200, wohlgeformt, keine Treffer darin. Strikt trennen vom echten Null-Treffer: kein `hint` auf einer Rückfrage, kein `inputRequests` auf einer Leermenge. Ein Modell darf aus «Rückfrage» nie «keine Daten» schliessen — und umgekehrt.
10. **Vorschlagen ist nicht Erweitern.** Auf der Leermenge kürzere Varianten des Begriffs anbieten, den der Aufrufer selbst geschickt hat — und keine davon abfragen. Die Sicherheitseigenschaft: Keine Meldung im Resultat darf einem Begriff zuzuschreiben sein, den der Aufrufer nicht gewählt hat. Der Nachweis ist ein Paar und keine einzelne Assertion — Vorschläge erscheinen, Vorschläge werden nie gesucht (Zähler auf der Upstream-Route). Fällt eine Hälfte weg, besteht die andere trivial.

## Voraussetzungen

- Claude Code, Claude Desktop oder claude.ai mit Skill-Unterstützung
- Die Patterns in `reference/patterns.py` zielen auf FastMCP, httpx und Pydantic v2 — die Regeln selbst sind stack-unabhängig
- Die Regeln 8 und 9 setzen die MCP-Spec 2026-07-28 voraus: `ttlMs`/`cacheScope` auf den List-Responses und MRTR (`resultType: "input_required"`) existieren vorher nicht. Auf einem älteren oder eingefrorenen Server werden sie als nicht anwendbar abgehakt, nicht als unerfüllt. Die Regeln 1–7 und 10 gelten so oder so.

## Installation

```bash
git clone https://github.com/malkreide/mcp-data-fidelity-skill.git
cp -r mcp-data-fidelity-skill ~/.claude/skills/mcp-data-fidelity
```

Der Verzeichnisname muss `mcp-data-fidelity` lauten — die Skill-Erkennung nutzt ihn.

## Verwendung

Der Skill greift selbstständig, sobald ein Such-, Query- oder Filter-Tool entworfen, eine Tool-Description geschrieben oder gemeldet wird, dass ein Server zu wenig liefert. Explizit ansprechen:

```
> Schreib die Tool-Description für dieses Such-Tool
> Warum findet mein Server nichts, obwohl das Web-UI 12 Treffer zeigt?
```

## Projektstruktur

```
.
├── SKILL.md                  # die zehn Regeln, mit Release-Checkliste
├── reference/
│   └── patterns.py           # Copy-Paste-Patterns für FastMCP / httpx / Pydantic v2
├── scripts/
│   └── validate.sh           # Einstieg für die Checks; die CI ruft diese Datei auf
├── tools/
│   └── checks/               # die Checks selbst — eine Funktion pro Gate
└── tests/
    ├── mutations.py          # pro Check ein Baum, auf dem er rot werden MUSS
    └── test_*.py             # fährt sie, und hält die Checks gegens echte Repo
```

## Woher diese Regeln stammen

Die Regeln 1–5 stammen aus einem einzelnen realen Vorfall: [`termdat-mcp#11`](https://github.com/malkreide/termdat-mcp/issues/11). Der Server sendete `ClassificationIds` nur bei explizitem Aufruf; die API schränkt eine ID-lose Suche auf `VARIA` ein — eine von 23 Klassifikationen. «Quellensteuer» lieferte null Treffer bei mehreren vorhandenen Einträgen, «Pensionskasse» einen statt 21.

Vier Dinge daran sind übertragbar:

1. **33 grüne Offline-Tests haben nichts gefangen** — Mocks können eine falsche Grundannahme prinzipiell nicht widerlegen.
2. **Ein 68-Punkte-Audit war bestanden** — alle Kategorien prüften die Bauweise, keine die Datentreue.
3. **Die eigene Doku hat das Modell zum Konfabulieren gebracht** — siehe Regel 4.
4. **Gefunden hat es ein User mit dem Web-UI daneben** — Ground Truth kommt von aussen, nicht aus der Testsuite.

Regel 6 kam nach einem zweiten Fall dazu: Eine Abfrage der MCP Registry lieferte eine Zeit lang nichts, weil die Felder unter `servers[].server.*` liegen und der Client eine Ebene höher suchte. Syntaktisch einwandfrei, semantisch blind.

Regel 10 und der Zusatz zu Regel 1 kamen nach einem dritten Fall dazu, [`amtsblatt-mcp`](https://github.com/malkreide/amtsblatt-mcp): Version 0.20.0 lehnte einen Vorschlagsmechanismus ab und begründete das mit Konkursmeldungen, Betreibungen, Erbschaftsaufrufen und Baueinsprachen — Rubriken, die die Allow-Liste des Servers gerade ausschliesst. Weil der durchsuchbare Bestand damit der nicht-sensible ist, wurde die Ausnahme für sensible Daten für genau die Menge beansprucht, auf die das Kriterium anzuwenden gewesen wäre. Die Begründung stand in beiden `SECURITY`-Dateien, im CHANGELOG und im abschliessenden PR; gefangen hat sie erst das [Re-Audit vom 2026-07-30](https://github.com/malkreide/amtsblatt-mcp/blob/main/audits/2026-07-30T105205-Z-amtsblatt-mcp/findings/ARCH-003.md), behoben hat sie 0.22.0.

Die Gegenrichtung ist der zweite Fehler desselben Falls: Der Vorschlagsmechanismus, den der Check verlangt, ist als Erlaubnis lesbar, die Vorschläge gleich mitzusuchen — dann liefert der Server Meldungen unter einem Begriff aus, den niemand gewählt hat. Beide Wege laufen in dieselbe Falle, und deshalb ist die Auflösung keine Wahl zwischen ihnen, sondern die Aufteilung.

Die Regeln 7–9 haben diese Herkunft **nicht**, und der Skill sagt das dort, wo er sie aufstellt. Sie sind aus der MCP-Spec 2026-07-28 hergeleitet: stateless Core ohne `initialize`, Reconnect als Normalfall (Regel 7); `ttlMs`/`cacheScope` auf den List-Responses (Regel 8); MRTR statt serverinitiierter Elicitation (Regel 9). Hergeleitet, nicht gemessen — in diesem Repo ein Unterschied, der genannt gehört. Die Latte für Vorschläge von aussen bleibt unverändert: Sie brauchen weiterhin einen eingetretenen Schaden. Über die tiefere Latte gekommen ist hier eine Protokolländerung, die alle 42 Server des Portfolios gleichzeitig trifft — keine plausibel klingende Empfehlung.

## Verwandte Repos

### Die MCP-Qualitätskette

Fünf Repos, ein Lebenszyklus. Jedes beantwortet eine andere Frage, in der Reihenfolge, in der sie aufkommt. Das gemeinsame GitHub-Topic ist [`mcp-quality-chain`](https://github.com/topics/mcp-quality-chain) und listet alle fünf auf einer Seite.

| Phase | Repo | Frage, die es beantwortet |
|---|---|---|
| vor dem Bau | [`mcp-data-source-probe-skill`](https://github.com/malkreide/mcp-data-source-probe-skill) | Taugt die Quelle, und was hat sie? Default-Matrix (1.2b), Recall-Ground-Truth (1.4), Leermengen (3.6). Hat diesen Skill unter `companion/` ausgeliefert, bis dieses Repo sein Zuhause wurde. |
| im Bau | **`mcp-data-fidelity-skill`** | **Dieser Skill:** liefert er, was die Quelle hat? |
| im Bau | [`mcp-transport-hardening-skill`](https://github.com/malkreide/mcp-transport-hardening-skill) | Kommt er hoch, weist er richtig ab? Dieselbe stille Fehlerklasse eine Schicht tiefer — nicht der Inhalt der Antwort, sondern ob überhaupt eine kommt |
| nach dem Bau | [`mcp-audit-skill`](https://github.com/malkreide/mcp-audit-skill) | Hält er gegen den Katalog? Die Regeln 1–6 liegen auf den sechs `FID`-Checks — nicht eins zu eins: Regeln 3 und 4 teilen sich `FID-003`, Regel 5 braucht `FID-005` und `FID-002`, Regel 6 ist `FID-006`. Die Regeln 7–9 liegen ausserhalb von `FID`, in `ARCH-020`, `HITL-006` und `ARCH-018`, die Abgrenzung von Regel 9 gegen die Leermenge in `FID-003`; Regel 10 liegt auf `ARCH-003` (Katalogstand: 113 Checks auf `main`, geschnitten v2.0.0; alle diese Checks sind `advisory` — ausser `ARCH-003`, das `enforced` ist und `always` gilt). Vollständige Tabelle samt der Reichweite, die jeder Check *nicht* abdeckt, in `SKILL.md`. |
| im Betrieb | [`mcp-continuous-auditor`](https://github.com/malkreide/mcp-continuous-auditor) | Hält er morgen noch? Seine Recall-Floors sind Regel 5, laufend gegen die echte Quelle gemessen. |

Daneben, nicht Teil der Kette: [`mcp-builder`](https://github.com/anthropics/skills/tree/main/skills/mcp-builder) — generische Bauanleitung von Anthropic, wird ergänzt und nicht ersetzt. Fremdes Repo, kann das Topic nicht tragen.

Dazu die beiden Server, aus denen dieser Skill stammt: [`termdat-mcp`](https://github.com/malkreide/termdat-mcp), dessen [Issue #11](https://github.com/malkreide/termdat-mcp/issues/11) die Regeln 1–5 hervorgebracht hat, und [`amtsblatt-mcp`](https://github.com/malkreide/amtsblatt-mcp), dessen [`ARCH-003`-Finding](https://github.com/malkreide/amtsblatt-mcp/blob/main/audits/2026-07-30T105205-Z-amtsblatt-mcp/findings/ARCH-003.md) Regel 10 und den Scope-Zusatz zu Regel 1 hervorgebracht hat.

Wer nach den Regeln 1–6 baut, besteht die `FID`-Checks; wer sie beim Audit reisst, findet hier die Behebung. Die Regeln 7–9 sind ausserhalb von `FID` abgedeckt, und diese Checks sind `advisory` — sie werden gezählt, nicht erzwungen. Regel 10 ist die Ausnahme: `ARCH-003` blockiert. Ohne Check ist keine Regel mehr; offen ist nur noch Reichweite, und am weitesten bei Regel 7: Ihr Check misst auf Baseline `2026-07-28`, den Pagination-Verlust gibt es aber auch auf `2025-11-25`. Die Lücken stehen je Zeile in `SKILL.md`.

## Changelog

Siehe [CHANGELOG.md](CHANGELOG.md)

## Mitwirken

Korrekturen sind willkommen: eine Regel, die falsch ist, ein Fall, den sie
schlecht entscheidet, eine Quelle, deren Defaults sich seit der Tabelle geändert
haben.

Für neue Regeln liegt die Latte höher. Die Regeln 1–6 stammen je aus einem
konkreten Schaden, der tatsächlich eingetreten ist — und vor allem deshalb lohnt
sich die Sammlung überhaupt. Regel 10 steht auf derselben Latte: ausgeliefert in
`amtsblatt-mcp` 0.20.0, gefangen vom Re-Audit, behoben in 0.22.0. Eine plausibel klingende Empfehlung ohne Narbe
dahinter macht den Skill länger und schwächer. Ein Vorschlag sollte den Vorfall
benennen, ein ✗/✓-Paar mitbringen und seinen **Nachweis** angeben: die zwei
Calls, das Delta, die Assertion, die eine funktionierende Kontrolle von einer
kaputten trennt.

Die Regeln 7–9 sind über eine tiefere Latte gekommen und sagen das im Text: Ihr
Beleg ist der Mechanismus der MCP-Spec 2026-07-28, hergeleitet statt gemessen.
Diese Ausnahme gilt einer Protokolländerung, die alle Server gleichzeitig
betrifft — sie ist kein zweiter Weg hinein für Empfehlungen im Allgemeinen.
Taucht eine der drei in freier Wildbahn auf, gehört der Vorfall in diese Datei.

Der Gegenstand des Skills gilt auch für den Vorschlag. Wenn sich eine Regel nicht
so verletzen lässt, dass es jemandem auffällt, ist es noch keine Regel — und wenn
der Beleg dafür nur aus einem Mock stammt, ist es noch kein Beleg.

Vor einem Pull Request die Checks laufen lassen:

```bash
pip install -r requirements-dev.txt
bash scripts/validate.sh
pytest
```

`validate.sh` ist dieselbe Datei, die die CI aufruft — es gibt also keine zweite
Kopie, die auseinanderlaufen könnte. Jeder Check läuft auch nach einem
Fehlschlag weiter, ein roter Durchlauf benennt damit alle Probleme auf einmal.

`pytest` wendet den Absatz oben auf die Checks selbst an. Jeder ist eine
gewöhnliche Funktion unter `tools/checks/`, und zu jedem gibt es in
`tests/mutations.py` mindestens einen Baum, auf dem er rot werden **muss** —
samt der Zusicherung, *was* er dann sagt. Ein Check ohne Mutation lässt die
Suite fehlschlagen. Derselbe Satz, eine Ebene höher: Ein Check, der sich nicht
so verletzen lässt, dass es jemandem auffällt, ist noch kein Check.

Vor einem grösseren Pull Request bitte ein Issue eröffnen, damit die Form vorher
geklärt ist.

## Sicherheit

Dieses Repo liefert Dokumentation und Referenzcode — keinen laufenden Server und
kein installierbares Paket. `reference/patterns.py` ist Material zum Anpassen und
keine Bibliothek zum Importieren: Die Namen stehen für das, was das Zielprojekt
ohnehin schon so nennt.

Die Fehlerklasse, um die es hier geht, ist ein Integritätsproblem und keine
klassische Schwachstelle. Ein Server, der einen Bruchteil seines Bestands
durchsucht und das nicht meldet, liefert Antworten, die richtig aussehen, als
falsch nicht erkennbar sind — und auf deren Grundlage entschieden wird. Regel 4
ist die schärfste Ausprägung: Eine Tool-Description, die eine Leermenge
*erklärt*, erzeugt Konfabulation zuverlässig.

Eine Hälfte von Regel 8 ist dagegen eine klassische Schwachstelle und kein
Integritätsproblem: `cacheScope`. Auf einem Server, dessen Resultate von den
Credentials des Aufrufers abhängen, bedeutet ein zu weiter Scope, dass die
Antwort des einen an den anderen ausgeliefert wird. Das ist ein Datenleck und
kein veralteter Cache — entschieden wird es in derselben Codezeile wie das
`ttlMs`.

Zwei Grenzen gehören dazugesagt. Die Scope-Erweiterung aus Regel 1 ist bewusst
best-effort — fällt der Vokabular-Endpoint aus, läuft die Abfrage unerweitert
weiter —, ein vorübergehender Upstream-Ausfall verengt also den Recall, ohne den
Call scheitern zu lassen. Und der `rows_of()`-Guard aus Regel 6 prüft nur die
Hülle und die tatsächlich gelesenen Felder, nicht das ganze Response-Schema; das
ist eine bewusste Abwägung, kein Versehen.

Fehler in den Regeln gefunden, oder einen Fall, den sie falsch behandeln? Bitte
ein Issue eröffnen.

## Lizenz

MIT License — siehe [LICENSE](LICENSE)

## Autor

Hayal Oezkan · [malkreide](https://github.com/malkreide)
