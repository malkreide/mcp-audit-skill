# mcp-data-fidelity-skill

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Claude Skill](https://img.shields.io/badge/Claude-Skill-orange)

> Claude Skill für MCP-Server-Tools, die eine externe Datenquelle abfragen — damit ein Server nicht still weniger liefert, als die Quelle hat.

🇬🇧 [English Version](README.md)

## Übersicht

Companion zu Anthropics `mcp-builder`. Dessen Best Practices decken ab, ob ein Server **korrekt gebaut** ist — Naming, Annotations, Pagination, Transport, Fehlerbehandlung. Dieser Skill deckt die Frage daneben ab: **liefert er, was die Quelle tatsächlich hat?**

Das ist eine eigene Fehlerklasse, weil sie still ist. HTTP 200, wohlgeformtes JSON, grüne Tests — und inhaltlich falsch. Ein Server, der zwei Prozent des Bestands durchsucht und das nicht meldet, produziert Antworten, die niemand als falsch erkennt.

Die Leitfrage bei jedem datenabfragenden Tool: *Wenn dieses Tool nichts findet — kann ich unterscheiden, ob es nichts gibt oder ob ich falsch gefragt habe?* Ist die Antwort nein, greift eine der sechs Regeln.

## Die sechs Regeln

1. **Scope-Parameter explizit senden, nie erben.** Ein weggelassener optionaler Filter bedeutet oft nicht «unbeschränkt», sondern einen willkürlichen Teilausschnitt — eine Tatsache, die ausschliesslich in der Parameterbeschreibung der Spec steht und an einem funktionierenden Call nicht erkennbar ist.
2. **Parameter-Gruppen vollständig senden.** Sendet man nur einige Mitglieder einer Gruppe, behalten die übrigen ihren serverseitigen Default. Das Argument kann dann nur erweitern, nie einschränken — ein No-op, der wie Steuerung aussieht.
3. **Die Leermenge trägt einen nächsten Schritt.** Null Treffer sind mehrdeutig. Das Resultat braucht ein konkretes `hint`-Feld — im Tool-Result, nicht im README.
4. **Die Tool-Description ist eine Halluzinations-Oberfläche.** Eine Formulierung, die eine Leermenge *erklärt*, erzeugt Konfabulation zuverlässiger als gar keine Formulierung. Zum Nachfassen auffordern, nie eine Schlussfolgerung lizenzieren.
5. **Query-Syntax in die Description, Recall in die Tests.** Abfragesprache und Matching-Granularität dokumentieren; Recall über Live-Untergrenzen absichern, denn ein Mock bildet die Annahme ab, mit der er geschrieben wurde.
6. **Die Antwort auf Struktur prüfen, nicht durchgreifen.** `payload.get("servers", [])` macht aus einer Strukturänderung upstream ein gültig aussehendes leeres Resultat. Ein Schema-Fehler gehört in den Fehlerkanal, nicht in eine leere Liste.

## Voraussetzungen

- Claude Code, Claude Desktop oder claude.ai mit Skill-Unterstützung
- Die Patterns in `reference/patterns.py` zielen auf FastMCP, httpx und Pydantic v2 — die Regeln selbst sind stack-unabhängig

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
├── SKILL.md                  # die sechs Regeln, mit Release-Checkliste
└── reference/
    └── patterns.py           # Copy-Paste-Patterns für FastMCP / httpx / Pydantic v2
```

## Woher diese Regeln stammen

Die Regeln 1–5 stammen aus einem einzelnen realen Vorfall: [`termdat-mcp#11`](https://github.com/malkreide/termdat-mcp/issues/11). Der Server sendete `ClassificationIds` nur bei explizitem Aufruf; die API schränkt eine ID-lose Suche auf `VARIA` ein — eine von 23 Klassifikationen. «Quellensteuer» lieferte null Treffer bei mehreren vorhandenen Einträgen, «Pensionskasse» einen statt 21.

Vier Dinge daran sind übertragbar:

1. **33 grüne Offline-Tests haben nichts gefangen** — Mocks können eine falsche Grundannahme prinzipiell nicht widerlegen.
2. **Ein 68-Punkte-Audit war bestanden** — alle Kategorien prüften die Bauweise, keine die Datentreue.
3. **Die eigene Doku hat das Modell zum Konfabulieren gebracht** — siehe Regel 4.
4. **Gefunden hat es ein User mit dem Web-UI daneben** — Ground Truth kommt von aussen, nicht aus der Testsuite.

Regel 6 kam nach einem zweiten Fall dazu: Eine Abfrage der MCP Registry lieferte eine Zeit lang nichts, weil die Felder unter `servers[].server.*` liegen und der Client eine Ebene höher suchte. Syntaktisch einwandfrei, semantisch blind.

## Verwandte Repos

| Repo | Rolle |
|---|---|
| [`mcp-data-source-probe-skill`](https://github.com/malkreide/mcp-data-source-probe-skill) | Das Vorgehen *vor* dem Bau: Default-Matrix (1.2b), Recall-Ground-Truth (1.4), Leermengen (3.6). Hat diesen Skill unter `companion/` ausgeliefert, bis dieses Repo sein Zuhause wurde. |
| [`mcp-audit-skill`](https://github.com/malkreide/mcp-audit-skill) | Prüfung *nach* dem Bau. Die Regeln 1–5 erscheinen dort als Checks `FID-001`–`FID-005`. |
| [`mcp-builder`](https://github.com/anthropics/skills) | Anthropics generische Bauanleitung — dieser Skill ergänzt sie, ersetzt sie nicht. |
| [`termdat-mcp`](https://github.com/malkreide/termdat-mcp) | Der Server, dessen [Issue #11](https://github.com/malkreide/termdat-mcp/issues/11) die Regeln 1–5 hervorgebracht hat |

Wer nach diesem Skill baut, besteht die `FID`-Checks; wer sie beim Audit reisst, findet hier die Behebung.

## Changelog

Siehe [CHANGELOG.md](CHANGELOG.md)

## Lizenz

MIT License — siehe [LICENSE](LICENSE)

## Autor

Hayal Oezkan · [malkreide](https://github.com/malkreide)
