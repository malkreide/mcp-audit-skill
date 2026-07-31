# mcp-transport-hardening-skill

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Claude Skill](https://img.shields.io/badge/Claude-Skill-orange)

> Claude Skill für MCP-Server mit Netz-Transport — damit ein Server unter dem konfigurierten Transport überhaupt hochkommt und abweist, wen er abweisen muss.

🇬🇧 [English Version](README.md)

## Übersicht

Companion zu Anthropics `mcp-builder`. Dessen Best Practices decken ab, ob ein Server **korrekt gebaut** ist — Naming, Annotations, Pagination, Transport, Fehlerbehandlung. Dieser Skill deckt die Frage daneben ab: **kommt er unter dem konfigurierten Transport überhaupt hoch, und weist er ab, wen er abweisen muss?**

Das ist eine eigene Fehlerklasse, weil sie still ist — nur anders still als bei [`mcp-data-fidelity`](https://github.com/malkreide/mcp-data-fidelity-skill). Dort liefert der Server eine plausible Antwort, die inhaltlich falsch ist. Hier liefert er gar keine: grüne Unit-Tests, sauberer Linter, und in Produktion startet der Prozess nicht oder beantwortet jede Anfrage unter einem echten Hostnamen mit HTTP 421. Der Transport-Pfad ist genau der Teil, den eine Testsuite über stdio nie berührt.

Die Leitfrage bei jedem Server mit Netz-Transport: *Wenn ich den Bind ändere — folgt die eingehende Allow-List mit, auf jedem Pfad, der eine App baut, und wird ein Test rot, wenn sie es nicht tut?*

## Die fünf Regeln

1. **Der SDK-Major-Sprung bricht drei Dinge, nur eines davon mechanisch.** Modul- und Klassennamen sind Suchen-und-Ersetzen; das schreibgeschützte `mcp.settings` verhindert den Start überhaupt; snake_case-Annotations brechen nur den lesenden Zugriff in Python, weil das Drahtformat unverändert bleibt — weshalb camelCase in TypeScript-Servern korrekt bleibt.
2. **`host` ist die Saat der Allow-List, kein kosmetischer Parameter.** Er defaultet auf `127.0.0.1`, und das SDK leitet daraus die eingehende Allow-List ab. Wird er nicht durchgereicht, gibt es HTTP 421 auf genau dem `0.0.0.0`-Deployment, für das der Server dokumentiert ist. uvicorn ruft eine `--factory` ohne Argumente auf, `--host` erreicht die App also nie.
3. **Jeder Pfad, der eine ASGI-App baut, wird identisch verdrahtet.** Ein eigener Builder, der nur bei gesetztem Auth oder CORS greift, der SDK-servierte `run()`-Pfad, ein deprecateter SSE-Pfad — wer nur einen verdrahtet, macht das Scharfschalten einer Sicherheitskontrolle von unbeteiligter Konfiguration abhängig. Der Port reist mit dem Host mit.
4. **Die eingehende Host-Allow-List ist eine eigene Kontrolle.** CORS hilft nicht (aus Browsersicht same-origin), ein Token hilft nicht (die angreifende Seite hält eines), die Egress-Allow-List ist die Gegenrichtung. Portgenau, Loopback immer drin, CORS-Origins aufgenommen, kein `*` — und Fail-open auf Nicht-Loopback wird mit einer Startwarnung sichtbar gemacht.
5. **Eine Kontrolle ist unbewiesen, bis ihre Entfernung rot wird.** Jede Kontrolle einzeln entfernen und die scheiternden Tests zählen. Eine Mutation mit null roten Tests ist eine unbewiesene Kontrolle, keine bestandene Prüfung — und ein Test, der *hängt* statt zu scheitern, ist schlimmer als keiner.

## Voraussetzungen

- Claude Code, Claude Desktop oder claude.ai mit Skill-Unterstützung
- Der konkrete Code zielt auf das Python-MCP-SDK 2.x (`mcp.server.mcpserver`) hinter einem ASGI-Server; die Argumentation in den Regeln 3–5 ist stack-unabhängig

## Installation

```bash
git clone https://github.com/malkreide/mcp-transport-hardening-skill.git
cp -r mcp-transport-hardening-skill ~/.claude/skills/mcp-transport-hardening
```

Der Verzeichnisname muss `mcp-transport-hardening` lauten — die Skill-Erkennung nutzt ihn.

## Verwendung

Der Skill greift selbstständig, sobald ein Server auf eine neue SDK-Major migriert, von stdio auf einen Netz-Transport umgestellt oder mit HTTP 421 gemeldet wird. Explizit ansprechen:

```
> Migrier diesen Server auf mcp 2.x
> Warum antwortet mein Server mit 421, obwohl der Bind auf 0.0.0.0 steht?
```

## Projektstruktur

```
.
└── SKILL.md                  # die fünf Regeln, mit Deployment-Checkliste
```

## Woher diese Regeln stammen

Aus drei Pull Requests desselben Zyklus (2026-07):

| PR | Ausgangslage |
|---|---|
| [`parlament-mcp#29`](https://github.com/malkreide/parlament-mcp/pull/29) | Migration 1.x → 2.x. Echter Startfehler plus 421 im HTTP-Pfad, vor dem Fix gegen den echten ASGI-Stack reproduziert |
| [`bag-health-mcp#51`](https://github.com/malkreide/bag-health-mcp/pull/51) | Kein 421-Bug — der Bind kam korrekt an. Es fehlte die Möglichkeit, überhaupt zu sagen, unter welchen Namen der Server erreichbar sein darf |
| [`swiss-transport-mcp#25`](https://github.com/malkreide/swiss-transport-mcp/pull/25) | Kein 421-Bug. Egress-Allow-List vorhanden, eingehend nichts — und der Port fiel auf dem Weg zum App-Builder heraus |

Was daran übertragbar ist:

1. **Nur einer der drei war ein Bug.** Die anderen zwei waren eine fehlende Kontrolle — für das gedachte Deployment vertretbar begründet, aber wer den Server anders betreibt, hatte keinen Weg, sich einzuklinken. Fehlende Konfigurierbarkeit fällt in keinem Test auf, weil nichts falsch ist.
2. **Grüne Tests und sauberer Linter, und der Prozess startet nicht.** Tool-Tests laufen über stdio und berühren den Transport-Pfad nie. Der Fehler wartet auf das erste HTTP-Deployment.
3. **Der Mutationstest hat in zwei von drei Repos die Tests korrigiert, nicht den Code** — daraus Regel 5.
4. **Ein Test, der hängt statt zu scheitern, ist schlimmer als keiner.** Ohne die Kontrolle wird die verbotene Anfrage *zugelassen*, und zugelassen heisst bei einem Stream: warten.

**Zur Benennung:** Zwei der drei PRs führen `SEC-005` im Titel, implementieren aber die *eingehende* Kontrolle — im Audit-Katalog `SEC-024`. `SEC-005` ist die ausgehende Richtung (DNS-Pinning gegen TOCTOU). Zwei Angriffe, ein Name.

## Verwandte Repos

| Repo | Rolle |
|---|---|
| [`mcp-data-fidelity-skill`](https://github.com/malkreide/mcp-data-fidelity-skill) | Dieselbe stille Fehlerklasse eine Schicht höher: liefert der Server, was die Quelle hat? |
| [`mcp-audit-skill`](https://github.com/malkreide/mcp-audit-skill) | Prüfung *nach* dem Bau. Regel 4 ist Check `SEC-024`, `SEC-005` ist die Gegenrichtung. |
| [`mcp-data-source-probe-skill`](https://github.com/malkreide/mcp-data-source-probe-skill) | Vorgehen *vor* dem Bau — dort wird die Datenquelle geprüft, hier der eigene Transport |
| [`mcp-builder`](https://github.com/anthropics/skills) | Anthropics generische Bauanleitung — dieser Skill ergänzt sie, ersetzt sie nicht. |

Wer nach diesem Skill baut, besteht `SEC-024`. Wer ihn beim Audit reisst, findet hier die Behebung.

## Changelog

Siehe [CHANGELOG.md](CHANGELOG.md)

## Lizenz

MIT License — siehe [LICENSE](LICENSE)

## Autor

Hayal Oezkan · [malkreide](https://github.com/malkreide)
