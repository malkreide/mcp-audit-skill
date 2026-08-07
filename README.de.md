# mcp-transport-hardening-skill

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Claude Skill](https://img.shields.io/badge/Claude-Skill-orange)

> Claude Skill für MCP-Server mit Netz-Transport — damit ein Server unter dem konfigurierten Transport überhaupt hochkommt, abweist wen er abweisen muss, und das auch ohne Sitzung durchhält.

🇬🇧 [English Version](README.md)

## Übersicht

Companion zu Anthropics `mcp-builder`. Dessen Best Practices decken ab, ob ein Server **korrekt gebaut** ist — Naming, Annotations, Pagination, Transport, Fehlerbehandlung. Dieser Skill deckt die Frage daneben ab: **kommt er unter dem konfigurierten Transport überhaupt hoch, weist er ab wen er abweisen muss, und hält das auch, wenn die Sitzung wegfällt?**

Das ist eine eigene Fehlerklasse, weil sie still ist — nur anders still als bei [`mcp-data-fidelity`](https://github.com/malkreide/mcp-data-fidelity-skill). Dort liefert der Server eine plausible Antwort, die inhaltlich falsch ist. Hier liefert er gar keine: grüne Unit-Tests, sauberer Linter, und in Produktion startet der Prozess nicht oder beantwortet jede Anfrage unter einem echten Hostnamen mit HTTP 421. Der Transport-Pfad ist genau der Teil, den eine Testsuite über stdio nie berührt.

Zwei Leitfragen, je eine pro Ära:

- *Wenn ich den Bind ändere — folgt die eingehende Allow-List mit, auf jedem Pfad, der eine App baut, und wird ein Test rot, wenn sie es nicht tut?* (Regeln 1–4)
- *Wenn zwei Aufrufer nichts mehr teilen — keinen Handshake, keine Sitzung, keine Verbindung —, sieht der eine dann noch etwas vom anderen, und wird ein Test rot, wenn er es tut?* (Regeln 8–12)

## Wie die dreizehn Regeln geordnet sind

| Block | Regeln | Frage |
|---|---|---|
| Bind und Verdrahtung | 1–4 | Kommt er hoch, und weist er richtig ab? |
| Der Beweis | 5–7, 13 | Woran erkennt man, dass es trägt, und wen deckt der Beweis ab? Gilt auch für 8–12 |
| Die Stateless-Welt, Spec `2026-07-28` | 8–12 | Hält er ohne Sitzung, und spricht er den neuen Umschlag? |

Der Beweisblock steht in der Mitte und nicht am Ende, weil er älter ist als der dritte Block und weil dieses Repo, sein eigenes CHANGELOG und vier Nachbar-Repos «Regel 6» und «Regeln 5–7» namentlich zitieren. Eine Umnummerierung würde die eigene Historie rückwirkend falsch machen — neue Regeln werden deshalb angehängt, nicht eingeschoben. Regel 13 gehört zum Beweisblock und steht aus genau demselben Grund trotzdem am Ende.

Die Regeln 1–7 gelten auf **beiden** Spec-Baselines: Bind, Verdrahtung, Host-Allow-List und Beweisführung hängen am Transport, nicht am Lebenszyklus. Die Regeln 8–12 gelten auf `2026-07-28`. Und die beiden Stände stehen nicht nacheinander, sondern nebeneinander — am Portfolio nachgemessen bedient ein und derselbe Prozess den Legacy-`initialize`-Handshake mit Cap bei `2025-11-25` und daneben einen per-request-Umschlag, der `2026-07-28` erreicht. Ein Stateless-Fehler ist damit für jeden Client unsichtbar, der noch auf der alten Ära spricht.

## Die dreizehn Regeln

1. **Der SDK-Major-Sprung bricht drei Dinge, nur eines davon mechanisch.** Modul- und Klassennamen sind Suchen-und-Ersetzen; das schreibgeschützte `mcp.settings` verhindert den Start überhaupt; snake_case-Annotations brechen nur den lesenden Zugriff in Python, weil das Drahtformat unverändert bleibt — weshalb camelCase in TypeScript-Servern korrekt bleibt. Der Versions-Cap trägt an beiden Enden, und das eigenständige `fastmcp` pinnt `mcp<2.0`, ist also eine Weiche und keine Formalie. Und ein Bound wirkt erst im Lock: Ihn allein in `pyproject.toml` zu setzen lässt das Deployment weiter installieren, was vorher galt.
2. **`host` ist die Saat der Allow-List, kein kosmetischer Parameter.** Er defaultet auf `127.0.0.1`, und das SDK leitet daraus die eingehende Allow-List ab. Wird er nicht durchgereicht, gibt es HTTP 421 auf genau dem `0.0.0.0`-Deployment, für das der Server dokumentiert ist. uvicorn ruft eine `--factory` ohne Argumente auf, `--host` erreicht die App also nie; auf einer PaaS kommt der Port erst beim Start, die Allow-List muss daraus zusammengesetzt werden statt als Literal dazustehen.
3. **Jeder Pfad, der eine ASGI-App baut, wird identisch verdrahtet.** Ein eigener Builder, der nur bei gesetztem Auth oder CORS greift, der SDK-servierte `run()`-Pfad, ein deprecateter SSE-Pfad — wer nur einen verdrahtet, macht das Scharfschalten einer Sicherheitskontrolle von unbeteiligter Konfiguration abhängig. Der Port reist mit dem Host mit, und seit `2026-07-28` auch die Header-Prüfung aus Regel 9.
4. **Die eingehende Host-Allow-List ist eine eigene Kontrolle.** CORS hilft nicht (aus Browsersicht same-origin), ein Token hilft nicht (die angreifende Seite hält eines), die Egress-Allow-List ist die Gegenrichtung. Portgenau, Loopback immer drin, CORS-Origins aufgenommen, kein `*` — und Fail-open auf Nicht-Loopback wird mit einer Startwarnung sichtbar gemacht. Sie ist die einzige eingehende Kontrolle, die mit dem Lebenszyklus nicht verschwunden ist.
5. **Ein Negativtest muss aus *deinem* Grund scheitern, nicht aus dem eines Defaults.** Grün heisst nur, dass die Anfrage abgewiesen wurde — nicht, dass deine Kontrolle sie abgewiesen hat. `evil.example.com` wird in jedem Zustand abgewiesen, auch von einer zurückgefallenen Loopback-Policy; richtiger Hostname mit *falschem Port* ist der Fall, den nur eine portgenaue Liste richtig entscheidet. Jeder Negativtest braucht seinen positiven Zwilling.
6. **Der Mutationstest ist das Abnahmekriterium für jede Sicherheitskontrolle.** Nicht «Tests schreiben», sondern: Mutation benennen, anwenden, *per Diff belegen, dass sie angekommen ist*, protokollieren, welche Tests fallen — und die Tabelle in den PR. Eine Zeile mit null roten Tests ist ein Befund: Entweder fehlt der Test, oder die Kontrolle tut nichts, oder die Mutation war ein No-op — und eine Ersetzung, die nichts trifft, sieht aus wie ein überlebender Mutant.
7. **Die Test-Harness ist bei HTTP-Transporten selbst eine Fehlerquelle.** Ein blanker `httpx.ASGITransport` liefert auf alles 500, weil er den App-Lifespan nie ausführt; ein Instanz-`monkeypatch` kann `mcp.run` dauerhaft verdecken und echtes uvicorn mitten in der Suite starten; und ein Zweig-Test, der seinen Zweig nicht behauptet, hängt statt zu scheitern. Die vierte Falle hat gar kein Symptom: Eine `autouse`-Fixture, die ein *fremdes* Modul patcht — `monkeypatch.setattr(modul.asyncio, "sleep", …)` liest sich lokal, greift aber ins Modul `asyncio` selbst und gilt damit für jeden Import im Prozess und jeden Test der Suite —, kann eine Parallelitätsprüfung stilllegen, indem sie die Übergabe an den Event-Loop entfernt: Zurück bleibt ein grüner Test ohne Gegenstand. Gepatcht wird ein Modul-Alias, den das Repo besitzt, und ersetzt wird die Dauer, nicht die Übergabe.
8. **Ohne Sitzung teilt sich Zustand still, statt zu fehlen.** `initialize` und `Mcp-Session-Id` sind weg; jede Anfrage trägt Protokollversion, `clientInfo` und Capabilities in `_meta`. Der gefährliche Server ist nicht der, der abstürzt, sondern der, der weiterläuft und prozesslokalen Zustand hält, der per Konvention über die Sitzung adressiert war — bei einem Aufrufer merkt es niemand, bei zweien ist es ein Datenleck ohne Fehlermeldung. Zustand reist als expliziter, server-geprägter, ablaufender Handle im Tool-Argument, und `server/discover` ist für Server ein MUSS, auch wenn es für Clients ein MAY ist.
9. **Die Adresse steht neu aussen auf dem Umschlag, und beide Seiten müssen dasselbe lesen.** `Mcp-Method` und `Mcp-Name` sind Pflichtheader auf Streamable-HTTP-POSTs, eine Abweichung ist `-32020`. Entscheidet ein Gateway am Header und der Server am Body, entscheiden zwei Instanzen über zwei Anfragen — der serverseitige Vergleich ist deshalb eine Sicherheitsgrenze, und zwar inklusive des Auslassungsfalls: Wer nur prüft, wenn die Header da sind, wird durch Weglassen umgangen.
10. **Legacy HTTP+SSE hat jetzt ein Datum: `2027-07-28`.** Deprecated seit `2025-03-26`, aber erst jetzt unter der Feature-Lifecycle-Politik mit Zwölfmonatsfenster. Eine Empfehlung ohne Termin erzeugt keinen Vorgang, sondern einen Kompatibilitätspfad, den niemand abschaltet — und dieser zweite Netzweg erbt die Härtung des ersten nicht. Das Erkennungsrezept läuft über drei Orte: Code, was das Deployment tatsächlich startet, und den Draht.
11. **MRTR: der Server antwortet und hält nichts offen — dafür läuft die Arbeit mehrfach.** `resultType: "input_required"` beendet die Bearbeitung, der Client wiederholt den ganzen Request mit `inputResponses`. Alles vor dem Rückfragepunkt passiert bei jedem Retry erneut, aus einem Bedienthema wird damit ein Korrektheitsthema: Nebenwirkungen gehören hinter den Rückfragepunkt oder hinter einen Idempotenzschlüssel. Und kein Retry ist garantiert, es darf also nichts reserviert werden, das ohne Abschluss nicht wieder freikommt.
12. **Auth-Härten — und der Negativbefund, den dieses Portfolio einträgt statt auszulassen.** RFC-9207-`iss` geprüft, bevor der Code eingelöst wird (auch ein *fehlender* `iss` bei einem Issuer, der ihn ankündigt), CIMD statt DCR, Credentials nach Issuer geschlüsselt. Für dieses read-only-Portfolio ist die Regel nicht anwendbar, aus einem benennbaren Grund: Kein Server löst einen Authorization Code ein. Ausgeschrieben statt weggelassen, weil ein weggelassener Abschnitt von einem übersehenen nicht zu unterscheiden ist.
13. **Ein Guard prüft nicht, was vor ihm abgezweigt wurde.** Er gilt ab dem Merge-Commit und nur vorwärts: Der Stand, der schon auf `main` liegt, ist nie gegen ihn gelaufen, und jeder vorher geschnittene Zweig mergt ohne ihn. Also den Workflow auch auf `push` nach `main` triggern, diesen Lauf nach dem Merge einmal ansehen, und die offenen Zweige auf `main` nachziehen (`git branch -r --no-contains <merge-sha>`). Gehört zu den Regeln 5–7 und steht als Letzte, damit die bestehenden Nummern halten.

## Voraussetzungen

- Claude Code, Claude Desktop oder claude.ai mit Skill-Unterstützung
- Der konkrete Code zielt auf das Python-MCP-SDK 2.x (`mcp.server.mcpserver`) hinter einem ASGI-Server; die Argumentation in den Regeln 3–12 ist stack-unabhängig

## Installation

```bash
git clone https://github.com/malkreide/mcp-transport-hardening-skill.git
cp -r mcp-transport-hardening-skill ~/.claude/skills/mcp-transport-hardening
```

Der Verzeichnisname muss `mcp-transport-hardening` lauten — die Skill-Erkennung nutzt ihn.

## Verwendung

Der Skill greift selbstständig, sobald ein Server auf eine neue SDK-Major oder auf Spec `2026-07-28` migriert, von stdio auf einen Netz-Transport umgestellt oder mit HTTP 421 gemeldet wird. Explizit ansprechen:

```
> Migrier diesen Server auf Spec 2026-07-28
> Warum antwortet mein Server mit 421, obwohl der Bind auf 0.0.0.0 steht?
> Hat dieser Server noch einen Legacy-SSE-Pfad?
```

## Projektstruktur

```
.
├── SKILL.md                  # die dreizehn Regeln, mit Release-Checkliste
└── reference/
    └── patterns.py           # Copy-Paste-Patterns für MCP-SDK 2.x / ASGI / uvicorn
```

## Woher diese Regeln stammen

**Die Regeln 1–7 stammen aus drei Pull Requests desselben Zyklus (2026-07):**

| PR | Ausgangslage |
|---|---|
| [`parlament-mcp#29`](https://github.com/malkreide/parlament-mcp/pull/29) | Migration 1.x → 2.x, als **letzter Server im Portfolio** auf der alten Major. Echter Startfehler plus 421 im HTTP-Pfad, vor dem Fix gegen den echten ASGI-Stack reproduziert |
| [`bag-health-mcp#51`](https://github.com/malkreide/bag-health-mcp/pull/51) | Kein 421-Bug — der Bind kam korrekt an. Es fehlte die Möglichkeit, überhaupt zu sagen, unter welchen Namen der Server erreichbar sein darf |
| [`swiss-transport-mcp#25`](https://github.com/malkreide/swiss-transport-mcp/pull/25) | Kein 421-Bug. Egress-Allow-List vorhanden, eingehend nichts — und der Port fiel auf dem Weg zum App-Builder heraus |

Was daran übertragbar ist:

1. **Nur einer der drei war ein Bug.** Die anderen zwei waren eine fehlende Kontrolle — für das gedachte Deployment vertretbar begründet, aber wer den Server anders betreibt, hatte keinen Weg, sich einzuklinken. Fehlende Konfigurierbarkeit fällt in keinem Test auf, weil nichts falsch ist.
2. **Grüne Tests und sauberer Linter, und der Prozess startet nicht.** Tool-Tests laufen über stdio und berühren den Transport-Pfad nie. Der Fehler wartet auf das erste HTTP-Deployment.
3. **Der letzte Server auf der alten Major war der, den keine Liste kannte.** `openparldata-mcp` liegt *verschachtelt* in einem anderen Repo und hat eine eigene `pyproject.toml` — damit ist er durch jede Aufzählung gefallen, die Top-Level-Repos listet, und die Abhängigkeits-Constraint des Elternprojekts hat ihn nie erfasst. Ein Inventar, das Repos zählt statt Deployment-Einheiten, übersieht genau die Fälle, die am längsten unmigriert bleiben.
4. **Der Mutationstest hat in zwei von drei Repos die Tests korrigiert, nicht den Code** — daraus Regel 6.
5. **Ein Test, der hängt statt zu scheitern, ist schlimmer als keiner** — daraus Regel 7. Ohne die Kontrolle wird die verbotene Anfrage *zugelassen*, und zugelassen heisst bei einem Stream: warten.

**Die Regeln 8–12 haben keine Narbe, sondern ein Datum.** Das steht hier ausgeschrieben, weil der Abschnitt «Mitwirken» weiter unten von jeder neuen Regel einen konkreten Schaden verlangt. Ihr Anlass ist die Spec-Revision `2026-07-28` — ein externes, datiertes Ereignis, dessen Änderungen nicht plausibel klingen, sondern nachlesbar sind. Was sie mit den ersten sieben teilt, ist die Form: ein ✗/✓-Paar und ein Nachweis, der die Mutation benennt, unter der er rot wird.

Zwei Dinge daran sind **gemessen** und nicht angenommen, beide an `zurich-opendata-mcp`: dass ein mcp-2.x-Prozess den Legacy-Handshake und den neuen per-request-Umschlag nebeneinander bedient, und dass das Erkennungsrezept aus Regel 10 an allen drei Orten negativ zurückkommt bei einem Server ohne Legacy-Pfad. Beides sind Messungen an einem Repo, und mehr behaupten die Regeln an dieser Stelle nicht.

**Zur Benennung:** Zwei der drei PRs führen `SEC-005` im Titel, implementieren aber die *eingehende* Kontrolle — im Audit-Katalog `SEC-024`. `SEC-005` ist die ausgehende Richtung (DNS-Pinning gegen TOCTOU). Zwei Angriffe, ein Name.

## Verwandte Repos

### Die MCP-Qualitätskette

Fünf Repos, ein Lebenszyklus. Jedes beantwortet eine andere Frage, in der Reihenfolge, in der sie aufkommt. Das gemeinsame GitHub-Topic ist [`mcp-quality-chain`](https://github.com/topics/mcp-quality-chain) und listet alle fünf auf einer Seite.

| Phase | Repo | Frage, die es beantwortet |
|---|---|---|
| vor dem Bau | [`mcp-data-source-probe-skill`](https://github.com/malkreide/mcp-data-source-probe-skill) | Taugt die Quelle, und was hat sie? |
| im Bau | [`mcp-data-fidelity-skill`](https://github.com/malkreide/mcp-data-fidelity-skill) | Liefert er, was die Quelle hat? |
| im Bau | **`mcp-transport-hardening-skill`** | **Dieser Skill:** kommt er hoch, weist er richtig ab, bleibt er zustandslos? |
| nach dem Bau | [`mcp-audit-skill`](https://github.com/malkreide/mcp-audit-skill) | Hält er gegen den Katalog? |
| im Betrieb | [`mcp-continuous-auditor`](https://github.com/malkreide/mcp-continuous-auditor) | Hält er morgen noch? |

Daneben, nicht Teil der Kette: [`mcp-builder`](https://github.com/anthropics/skills/tree/main/skills/mcp-builder) — generische Bauanleitung von Anthropic, wird ergänzt und nicht ersetzt. Fremdes Repo, kann das Topic nicht tragen.

### Abgrenzung: dieser Skill, der Katalog, die Live-Probe

Die drei Repos berühren dieselben Gegenstände und stellen verschiedene Fragen. Ohne diese Trennung entsteht Duplikation, und Duplikation altert auseinander.

**Hier steht, wie man es verdrahtet und woran man sieht, dass es trägt. Der Katalog fragt, ob es da ist. Der Auditor fragt, ob es heute noch da ist.**

Gegen `mcp-audit` v2.0.0 (112 Checks in zwölf Kategorien, zwei Spec-Baselines): Regel 1 ist `SDK-006` plus `DEP-001`, Regel 3 ist `ARCH-013`, Regel 4 ist `SEC-024` (mit `SEC-005` als ausgehender Gegenrichtung), Regel 8 ist `ARCH-015`/`ARCH-016`/`ARCH-017`, Regel 9 ist `SCALE-008`, Regel 10 ist `SCALE-009`/`SCALE-010`, Regel 11 ist `HITL-006`, Regel 12 ist `SEC-025`/`SEC-026`. Für die Regeln 2 und 6 gibt es keinen Check; bei den Regeln 5, 7 und 13 liegt je einer daneben oder deckt eine Hälfte — die vollständige Zuordnung in [SKILL.md](SKILL.md) benennt die Lücken, statt sie zu überdecken, dazu die fünf Checks, die einen von `2026-07-28` entfernten Gegenstand messen, und die Spec-Änderungen, die dieser Skill bewusst dem Katalog überlässt.

## Changelog

Siehe [CHANGELOG.md](CHANGELOG.md)

## Mitwirken

Korrekturen sind willkommen: eine Regel, die falsch ist, ein Fall, den sie
schlecht entscheidet, ein SDK-Detail, das sich weiterbewegt hat.

Für neue Regeln liegt die Latte höher. Eine Regel verdient ihren Platz durch
einen konkreten Schaden, der tatsächlich eingetreten ist — oder durch eine
datierte, zitierbare Änderung von aussen. Welches von beidem es ist, gehört
dazugesagt, so wie bei den Regeln 8–12. Eine plausibel klingende Empfehlung ohne
das eine oder andere macht den Skill länger und schwächer. Ein Vorschlag sollte
seinen Anlass benennen, ein ✗/✓-Paar mitbringen und seinen **Nachweis** angeben:
wie man zeigt, dass die Regel trägt, und was man kaputtmachen müsste, damit es
auffällt. Die CI erzwingt diese Form.

Die Regeln 5–7 und 13 gelten auch für den Vorschlag selbst. Wenn sich eine Regel nicht so
verletzen lässt, dass es jemandem auffällt, ist es noch keine Regel.

Vor einem grösseren Pull Request bitte ein Issue eröffnen, damit die Form vorher
geklärt ist.

## Sicherheit

Dieses Repo liefert Dokumentation und Referenzcode — keinen laufenden Server und
kein installierbares Paket. `reference/patterns.py` ist Material zum Anpassen und
keine Bibliothek zum Importieren: Die Namen stehen für das, was das Zielprojekt
ohnehin schon so nennt, und die referenzierten Fixtures kommen aus dessen eigener
`conftest.py`.

Zwei Punkte sind beim Anwenden von Regel 4 wesentlich. Die Allow-List ist auf
einem Nicht-Loopback-Bind ohne Konfiguration **fail-open**. Das ist Absicht, weil
eine geratene Liste genau das Deployment abweist, das sie schützen soll — es
heisst aber, dass ein unkonfigurierter Server auf `0.0.0.0` keine eingehende
Host-Prüfung hat. Die Startwarnung ist das Signal, dass dieser Zustand vorliegt.
Und die eingehende Allow-List ersetzt weder Authentifizierung noch eine
Egress-Allow-List — sie beantwortet eine andere Frage, wie die Regel ausführt.

Regel 12 hält einen **Negativbefund** fest und keine Anleitung: Dieses Portfolio
ist read-only und löst keinen Authorization Code ein, damit sind RFC-9207-`iss`,
CIMD und issuer-gebundene Credentials derzeit nicht anwendbar. Die Bedingung, die
das aufhebt, steht in der Regel. Wer dieses Material für einen
authentifizierenden Server nachnutzt, hat Regel 12 ab der ersten
Zugangsberechtigung im Geltungsbereich.

Fehler in den Regeln gefunden, oder einen Fall, den sie falsch behandeln? Bitte
ein Issue eröffnen.

## Lizenz

MIT License — siehe [LICENSE](LICENSE)

## Autor

Hayal Oezkan · [malkreide](https://github.com/malkreide)
