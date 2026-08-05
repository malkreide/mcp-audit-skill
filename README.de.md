# mcp-data-source-probe-skill

![Version](https://img.shields.io/badge/version-1.7.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Claude Skill](https://img.shields.io/badge/Claude-Skill-orange)

> Claude Skill, der eine öffentliche Datenquelle prüft, *bevor* ein MCP-Server dagegen gebaut wird — und misst, ob der fertige Server liefert, was die Quelle tatsächlich hat.

🇬🇧 [English Version](README.md)

## Übersicht

Einen MCP-Server gegen eine dokumentierte API zu bauen ist einfach. Einen zu bauen, der den *ganzen* Bestand liefert, ist es nicht — denn die Arten, auf die eine API stillschweigend weniger als alles zurückgibt, sind an einem funktionierenden Beispiel nicht erkennbar: ein weggelassener Filter, der den Suchraum einschränkt; ein Limit, das auf 25 steht; ein Volltextindex, der auf ganzen Wörtern matcht, womit deutsche Komposita unauffindbar bleiben.

Dieser Skill kodiert ein Vorgehen aus vier Disziplinen, das im Swiss Public Data MCP Portfolio (40+ Server) für jede neue Datenquelle gilt. Es ist bewusst empirisch: Dokumentation ist ein Foto, die Live-Probe ist der aktuelle Zustand — und wir bauen auf dem aktuellen Zustand.

Die vierte Disziplin — **Ground Truth vor Selbstvertrauen** — kam nach einem realen Vorfall dazu. Ein Server bestand ein Audit mit 68 Checks und 33 grüne Tests, während er ein Dreiundzwanzigstel seiner Datenbank durchsuchte: Ein optionaler Parameter, den er nie sendete, schränkt upstream auf ein einziges Sachgebiet ein. Gefunden hat es ein User mit dem offiziellen Web-UI daneben.

## Funktionen

- **Schritt 1 — Live-Probe vor dem Design.** Fünf Probe-Calls pro Endpoint, Default-Matrix für jeden optionalen Parameter, Abdeckungs-Matrix mit dem Teil des Bestands, den kein geplantes Tool erreicht, Recall-Ground-Truth gegen das Web-UI der Quelle, gemessene Widening-Staffel, Dump-Verfügbarkeit — und der über mindestens zwei Zyklen gemessene Aktualisierungsrhythmus der Quelle, aus dem das zugesagte `ttlMs` abgeleitet wird.
- **Schritt 2 — Architektur-Entscheid.** Entscheidungsbaum von den Probe-Befunden zu Live-API / Hybrid / Dump-only, Portfolio-Synergie-Check (neuer Server oder Tool-Erweiterung?) und ein zweiter Pflicht-Entscheid: welche `mcp_spec_version` der Server spricht — Standard `2026-07-28`, jede Abweichung schriftlich begründet, kein neuer Server auf deprecated Bausteinen.
- **Schritt 3 — Nicht verhandelbare Resilienz-Defaults.** Retry mit Backoff, Provenance und Attribution in jeder Response, Anchor Demo Query, Tests gegen Fehlerzustände, Graceful Degradation — und Leermengen, die einen nächsten Schritt tragen statt einer Ausrede.
- **Schritte 4–5 — Übergabe.** Eingaben für die Repo-Erstellung und ein Portfolio-Register, dessen normative Hälfte eine `portfolio.json` im Index-Repo ist — versioniert, im Diff, ohne Konto bei irgendwem. Die menschenlesbare Hälfte ist eine Darstellung nach Wahl: Notion-Datenbank, generierte Markdown-Tabelle oder gar keine.
- **Fundstück-Kultur.** Nicht offensichtliche Funde werden festgehalten, damit der nächste Server sie erbt, statt sie neu zu entdecken.

## Voraussetzungen

- Claude Code, Claude Desktop oder claude.ai mit Skill-Unterstützung
- `curl` und `python3` für die Probe-Befehle
- Optional: `jq` für JSON-Inspektion von Hand

## Installation

```bash
git clone https://github.com/malkreide/mcp-data-source-probe-skill.git
cp -r mcp-data-source-probe-skill ~/.claude/skills/mcp-data-source-probe
```

Der Verzeichnisname muss `mcp-data-source-probe` lauten — die Skill-Erkennung nutzt ihn.

Den Companion-Skill `mcp-data-fidelity` (siehe unten) zusätzlich installieren —
er liegt in einem eigenen Repo:

```bash
git clone https://github.com/malkreide/mcp-data-fidelity-skill.git
cp -r mcp-data-fidelity-skill ~/.claude/skills/mcp-data-fidelity
```

## Verwendung

Der Skill greift selbstständig, sobald ein MCP-Server gegen eine Datenquelle geplant, gebaut oder debuggt wird. Explizit ansprechen:

```
> Ich würde gerne die API von opendata.swiss via MCP anbinden
> Warum findet mein Server nichts, obwohl das Web-UI 12 Treffer zeigt?
```

Das Probe-Template direkt ausführen:

```bash
BASE="https://api.example.ch/v2" OUTDIR=/tmp/probe bash reference/probe_template.sh
```

## Projektstruktur

```
.
├── SKILL.md                              # das Vorgehen selbst
├── reference/
│   ├── probe_template.sh                 # lauffähiges Probe-Gerüst: Scope, Abdeckung,
│   │                                     #   Widening, Frische, Reihenfolge
│   ├── befund_tabelle_template.md        # Befund-Tabelle: Default-Matrix, Recall-Ground-
│   │                                     #   Truth, Aktualisierungsrhythmus, Spec-Ziel
│   ├── response_envelope.py              # Pydantic-v2-Envelope mit source + provenance
│   └── retry_backoff.py                  # Referenz-Implementation für exponentielles Backoff
├── companion/
│   └── mcp-data-fidelity/
│       └── README.md                     # Pointer — der Skill hat ein eigenes Repo
└── scripts/
    └── validate.sh                       # die Checks des Repos; die CI ruft diese Datei auf
```

## Companion-Skill: `mcp-data-fidelity`

`mcp-data-fidelity` wurde bisher in diesem Repo unter `companion/` ausgeliefert.
Er hat jetzt ein eigenes Repo, das sein kanonisches Zuhause ist:
**[`mcp-data-fidelity-skill`](https://github.com/malkreide/mcp-data-fidelity-skill)**.

Die beiden teilen sich die Arbeit nach Phase. `mcp-data-source-probe` deckt ab, was
*vor und um* den Bau herum passiert: Quelle proben, Architektur wählen, Recall gegen
Ground Truth messen. `mcp-data-fidelity` deckt den Code selbst ab — er ergänzt
Anthropics `mcp-builder` um sechs Regeln für Tools, die eine externe Quelle abfragen:

1. Scope-Parameter explizit senden, nie erben
2. Parameter-Gruppen vollständig senden — eine Teilmenge erbt still die Server-Defaults
3. Eine Leermenge trägt einen konkreten nächsten Schritt
4. Die Tool-Description ist eine Halluzinations-Oberfläche
5. Query-Syntax gehört in die Description, Recall in die Tests
6. Die Antwort auf Struktur prüfen, bevor gezählt wird — eine falsch angenommene
   Verschachtelung liefert dieselbe leere Liste wie ein echter Nullbefund

Er existiert als Companion und nicht als Patch, weil `mcp-builder` ein von Anthropic
mitgeliefertes Skill ist: Eine Änderung darin würde beim nächsten Sync überschrieben,
ein Fork würde künftige Verbesserungen abschneiden. Wer beide installiert, bekommt die
generische Bauanleitung und diese Regeln zusammen.

## Die vier Disziplinen

1. Live-Probe **vor** Design
2. Dump-Fallback **vor** API-Abhängigkeit
3. Retry **vor** Defaitismus
4. Ground Truth **vor** Selbstvertrauen

Dazu der Merksatz fürs Portfolio, für die beiden Zeitangaben, die am häufigsten verwechselt werden: *«Frische innen (`source_freshness`), Haltbarkeit aussen (`ttlMs`).»* Die eine sagt, wie alt die Daten sind, und blickt zurück — an den Leser der Antwort. Die andere sagt, wie lange die Antwort gültig bleibt, und blickt nach vorn — an den Cache des Clients. Sie sind nie dieselbe Zahl.

## Verwandte Repos

### Die MCP-Qualitätskette

Fünf Repos, ein Lebenszyklus. Jedes beantwortet eine andere Frage, in der Reihenfolge, in der sie aufkommt — dieses kommt zuerst. Das gemeinsame GitHub-Topic ist [`mcp-quality-chain`](https://github.com/topics/mcp-quality-chain) und listet alle fünf auf einer Seite.

| Phase | Repo | Frage, die es beantwortet |
|---|---|---|
| vor dem Bau | **`mcp-data-source-probe-skill`** | **Dieser Skill:** taugt die Quelle, und was hat sie? |
| im Bau | [`mcp-data-fidelity-skill`](https://github.com/malkreide/mcp-data-fidelity-skill) | Liefert er, was die Quelle hat? Wurde hier unter `companion/` ausgeliefert, bis er ein eigenes Repo bekam |
| im Bau | [`mcp-transport-hardening-skill`](https://github.com/malkreide/mcp-transport-hardening-skill) | Kommt er hoch, weist er richtig ab? |
| nach dem Bau | [`mcp-audit-skill`](https://github.com/malkreide/mcp-audit-skill) | Hält er gegen den Katalog? |
| im Betrieb | [`mcp-continuous-auditor`](https://github.com/malkreide/mcp-continuous-auditor) | Hält er morgen noch? Die Recall-Ground-Truth aus Schritt 1.4, laufend statt einmalig gemessen |

Daneben, nicht Teil der Kette: [`mcp-builder`](https://github.com/anthropics/skills/tree/main/skills/mcp-builder) — generische Bauanleitung von Anthropic, wird ergänzt und nicht ersetzt. Fremdes Repo, kann das Topic nicht tragen.

Dazu der Server, aus dem die vierte Disziplin stammt: [`termdat-mcp`](https://github.com/malkreide/termdat-mcp), dessen [Issue #11](https://github.com/malkreide/termdat-mcp/issues/11) sie hervorgebracht hat.

Wer nach diesem Skill probt und nach `mcp-data-fidelity` baut, besteht die `FID`-Checks; wer sie beim Audit reisst, findet dort das Vorgehen zur Behebung.

## Changelog

Siehe [CHANGELOG.md](CHANGELOG.md)

## Mitwirken

Korrekturen sind willkommen: ein Probe-Befehl, der nicht mehr funktioniert, eine
Quelle, deren Verhalten sich geändert hat, ein Schritt, der anders formuliert
klarer wird.

Für neue Schritte und Anti-Patterns liegt die Latte höher. Dieses Vorgehen ist
bewusst empirisch — Dokumentation ist ein Foto, die Live-Probe ist der aktuelle
Zustand —, und derselbe Massstab gilt für das Vorgehen selbst. Ein
vorgeschlagener Schritt sollte aus einer Quelle stammen, die sich tatsächlich so
verhalten hat, und benennen, welche das war, damit die nächste Person nachproben
kann. Genau dafür ist die Fundstück-Kultur da: Ein Fund, den niemand aufschreibt,
wird zum vollen Preis neu entdeckt.

Der nützlichste Beitrag ist meist der kleinste — eine einzelne Zeile in der
Default-Matrix für eine noch nicht gelistete Quelle, mit der Parameterbeschreibung,
die sie belegt.

Vor einem Pull Request die Checks laufen lassen:

```bash
bash scripts/validate.sh
```

Es ist dieselbe Datei, die die CI aufruft — es gibt also keine zweite Kopie, die
auseinanderlaufen könnte. Jeder Check läuft auch nach einem Fehlschlag weiter,
ein roter Durchlauf benennt damit alle Probleme auf einmal. Vor einer
Änderung an der Frontmatter zu wissen: Das Limit für `description` liegt bei 1024
Zeichen, und die aktuelle lässt einstelligen Spielraum — das Skript gibt aus,
wie viel übrig ist.

Vor einem grösseren Pull Request bitte ein Issue eröffnen, damit die Form vorher
geklärt ist.

## Sicherheit

Dieses Repo liefert Dokumentation und Referenzcode — keinen laufenden Server und
kein installierbares Paket. Die Python-Dateien unter `reference/` sind Material
zum Anpassen, keine Bibliothek zum Importieren.

`reference/probe_template.sh` ist die Ausnahme, die man vor dem Ausführen lesen
sollte: Das Skript setzt **echte HTTP-Requests** gegen das ab, worauf `BASE`
zeigt — mehrere pro Endpoint —, und die Scope-Probe fragt bewusst das Maximum
ab, das eine Quelle hergibt. Nur auf Quellen richten, für die eine Berechtigung
besteht, und deren Rate Limits beachten: Eine empirische Probe ist trotzdem
Last auf fremden Servern.

Ausserdem schreibt es **rohe API-Antworten** nach `$OUTDIR` (Default
`/tmp/mcp-probe`). Diese Dateien sind der Beleg, den eine Probe erzeugen soll,
und sie enthalten, was die Quelle geliefert hat. Nicht mitcommitten und als
Daten behandeln, für die die Nutzungsbedingungen der Quelle gelten — nicht als
beliebige Zwischenausgabe.

Fehler im Vorgehen gefunden, oder einen Fall, den es falsch behandelt? Bitte ein
Issue eröffnen.

## Lizenz

MIT License — siehe [LICENSE](LICENSE)

## Autor

Hayal Oezkan · [malkreide](https://github.com/malkreide)
