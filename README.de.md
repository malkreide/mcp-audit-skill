# mcp-data-source-probe-skill

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Claude Skill](https://img.shields.io/badge/Claude-Skill-orange)

> Claude Skill, der eine öffentliche Datenquelle prüft, *bevor* ein MCP-Server dagegen gebaut wird — und misst, ob der fertige Server liefert, was die Quelle tatsächlich hat.

🇬🇧 [English Version](README.md)

## Übersicht

Einen MCP-Server gegen eine dokumentierte API zu bauen ist einfach. Einen zu bauen, der den *ganzen* Bestand liefert, ist es nicht — denn die Arten, auf die eine API stillschweigend weniger als alles zurückgibt, sind an einem funktionierenden Beispiel nicht erkennbar: ein weggelassener Filter, der den Suchraum einschränkt; ein Limit, das auf 25 steht; ein Volltextindex, der auf ganzen Wörtern matcht, womit deutsche Komposita unauffindbar bleiben.

Dieser Skill kodiert ein Vorgehen aus vier Disziplinen, das im Swiss Public Data MCP Portfolio (40+ Server) für jede neue Datenquelle gilt. Es ist bewusst empirisch: Dokumentation ist ein Foto, die Live-Probe ist der aktuelle Zustand — und wir bauen auf dem aktuellen Zustand.

Die vierte Disziplin — **Ground Truth vor Selbstvertrauen** — kam nach einem realen Vorfall dazu. Ein Server bestand ein Audit mit 68 Checks und 33 grüne Tests, während er ein Dreiundzwanzigstel seiner Datenbank durchsuchte: Ein optionaler Parameter, den er nie sendete, schränkt upstream auf ein einziges Sachgebiet ein. Gefunden hat es ein User mit dem offiziellen Web-UI daneben.

## Funktionen

- **Schritt 1 — Live-Probe vor dem Design.** Fünf Probe-Calls pro Endpoint, Default-Matrix für jeden optionalen Parameter, Recall-Ground-Truth gegen das Web-UI der Quelle, Dump-Verfügbarkeit.
- **Schritt 2 — Architektur-Entscheid.** Entscheidungsbaum von den Probe-Befunden zu Live-API / Hybrid / Dump-only, plus Portfolio-Synergie-Check (neuer Server oder Tool-Erweiterung?).
- **Schritt 3 — Nicht verhandelbare Resilienz-Defaults.** Retry mit Backoff, Provenance und Attribution in jeder Response, Anchor Demo Query, Tests gegen Fehlerzustände, Graceful Degradation — und Leermengen, die einen nächsten Schritt tragen statt einer Ausrede.
- **Schritte 4–5 — Übergabe.** Eingaben für die Repo-Erstellung und die Portfolio-Karte.
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
└── reference/
    ├── probe_template.sh                 # lauffähiges Probe-Gerüst inkl. scope_probe()
    ├── befund_tabelle_template.md        # Befund-Tabelle: Default-Matrix, Recall-Ground-Truth
    ├── response_envelope.py              # Pydantic-v2-Envelope mit source + provenance
    └── retry_backoff.py                  # Referenz-Implementation für exponentielles Backoff
```

## Die vier Disziplinen

1. Live-Probe **vor** Design
2. Dump-Fallback **vor** API-Abhängigkeit
3. Retry **vor** Defaitismus
4. Ground Truth **vor** Selbstvertrauen

## Verwandte Repos

| Repo | Rolle |
|---|---|
| [`mcp-audit-skill`](https://github.com/malkreide/mcp-audit-skill) | Prüfung *nach* dem Bau. Dieselben Regeln erscheinen dort als Checks `FID-001`–`FID-005`. |
| [`mcp-continuous-auditor`](https://github.com/malkreide/mcp-continuous-auditor) | Laufende Verifikation von Servern im Betrieb |
| [`termdat-mcp`](https://github.com/malkreide/termdat-mcp) | Der Server, dessen [Issue #11](https://github.com/malkreide/termdat-mcp/issues/11) die vierte Disziplin hervorgebracht hat |

Wer nach diesem Skill baut, besteht die `FID`-Checks; wer sie beim Audit reisst, findet hier das Vorgehen zur Behebung.

## Changelog

Siehe [CHANGELOG.md](CHANGELOG.md)

## Lizenz

MIT License — siehe [LICENSE](LICENSE)

## Autor

Hayal Oezkan · [malkreide](https://github.com/malkreide)
