# Zusammenfuehrung: fuenf Repositories auf zwei

Stand der Messungen: 10. August 2026, gegen die damaligen `main`-Staende.
Alle Zahlen unten sind nachgemessen, nicht geschaetzt; wo eine Zahl altert,
steht dabei, wie sie neu zu erheben ist.

## 1. Der Schnitt

Heute fuenf Repositories, jedes referenziert jedes andere — 20 gerichtete
Kanten, jede ein Sync-Punkt von Hand.

**Ziel: zwei Repositories, entlang der Trennlinie Inhalt / Laufzeit.**

| Repo | Inhalt | Warum getrennt |
|---|---|---|
| **`mcp-audit`** (dieses) | Katalog + vier Skills + EIN Pruefgeruest | Dokumentation und Vorlagen. Aendert sich mit dem Katalog. |
| **`mcp-continuous-auditor`** | Engine: `deploy/microvm/`, `tensorzero/`, Probes, 7 Workflows | Deploybare Anwendung mit eigenem Release-Rad und anderem Blast Radius. Konsumiert `mcp-audit` auf gepinntem Tag. |

Nicht alles in eines: Sonst zieht jeder Katalog-Typo die MicroVM- und
TensorZero-Pipeline hinter sich her, und die Skills erben ein Release-Rad, das
sie nicht brauchen. Der Ertrag der Zusammenfuehrung liegt fast vollstaendig im
Zusammenlegen der vier Pruefgerueste — den holt Repo A allein ein.

## 2. Zielstruktur

```
mcp-audit/
├── checks/                     # KATALOG, 121 Dateien — bleibt, wo er ist
├── skills/
│   ├── mcp-audit/              # SKILL.md, templates/, docs/
│   ├── mcp-data-source-probe/  # SKILL.md, reference/
│   ├── mcp-data-fidelity/      # SKILL.md, reference/
│   └── mcp-transport-hardening/# SKILL.md, reference/
├── tools/
│   ├── harness/                # das EINE Geruest  ← Phase 0, steht
│   │   ├── _core.py            #   Registry, Ausfuehrung, CheckFailed
│   │   └── __main__.py         #   Runner ueber alle Suiten
│   ├── gates/                  # die 16 GENERISCHEN Pruefungen  ← Phase 2
│   ├── suites/<skill>/         # die 10 SKILL-EIGENEN Pruefungen ← Phase 2
│   └── …                       # Audit-Werkzeuge, unveraendert
└── tests/
```

`checks/` wird **nicht** umbenannt. Der Katalog wird von aussen unter
`raw.githubusercontent.com/malkreide/mcp-audit-skill/main/checks/…` zitiert;
ein Umzug braeche diese Verweise ohne Gegenwert. Das Pruefgeruest liegt unter
`tools/`, es kollidiert nicht.

## 3. Die Nummernfrage — entschieden

Die vier Registries numerieren jede ab 1, und `tests/test_checks_registry.py`
verlangt woertlich:

```python
assert numbers == list(range(1, len(numbers) + 1))   # lueckenlos 1..N
```

Zugleich sind diese Nummern zugesichert: Sie stehen in vier CHANGELOGs und in
Befunden («Check 7 meldet dasselbe»). Ein flacher Nummernraum haette **48 von
53 Registrierungen umnumeriert** und jede dieser Referenzen stillschweigend
falsch gemacht.

**Entscheid: die Suite traegt die Nummer mit.** `audit/1` und `probe/1` sind
verschiedene Pruefungen, beide behalten ihre Nummer, und die Lueckenlosigkeit
wird je Suite geprueft statt ueber alles. Die Invariante der Herkunftsrepos
bleibt woertlich erhalten, ohne dass es vier Registries braucht.

Umgesetzt in `tools/harness/_core.py`, abgesichert durch
`tests/test_harness_core.py::test_ANKER_dieselbe_nummer_darf_in_zwei_suiten_stehen`.

## 4. Datei-fuer-Datei-Entscheid

### 4.1 Das Geruest — vier Kopien, drei Zeilen Unterschied

Gemessen ueber die vier `tools/checks/_core.py`:

| Was | audit | probe | fidelity | transport |
|---|---|---|---|---|
| `pycache_to_temp` | ja | ja | **fehlt** | ja |
| `python_version()` | – | – | **nur hier** | – |
| Temp-Praefix | `audit-` | `audit-` | – | `transport-` |

Alles Uebrige ist identisch bis auf Docstring-Prosa und Umlaut-Schreibweise.

Die frueher gezaehlten 66–93 abweichenden Zeilen je Paar sind zu ~95 %
Docstrings. **Entscheid: Superset.** `pycache_to_temp` mit parametrisiertem
Praefix, `python_version()` uebernommen, Prosa aus der ausfuehrlichsten
Fassung. Status: **erledigt** (Phase 0).

Dasselbe fuer `__main__.py`: identisch bis auf den Repo-Namen im Kopf und
fidelitys Flag `--include-context-bound` statt `--include-network`. **Beide
Schreibweisen bleiben gueltig** — was in fremden READMEs dokumentiert ist,
muss weiter laufen. Abgesichert durch
`test_ANKER_der_alte_flag_name_aus_fidelity_gilt_weiter`.

Dabei aufgefallen und gleich geschlossen: Ein Lauf ohne ausgewaehlte Pruefung
meldete `0 checks, all passed`. Eine leere Registry war damit von einem
bestandenen Lauf nicht unterscheidbar. Ein leerer Lauf ist jetzt rot.

### 4.2 Die Pruefmodule — 53 Registrierungen auf 26 Implementierungen

Gezaehlt ueber alle vier `tools/checks/`. `–` heisst: in diesem Repo nicht
vorhanden.

**Generisch — 16 Familien, die heute 43 Registrierungen tragen** → `tools/gates/`

| # | Familie | audit | probe | fidelity | transport |
|---|---|---|---|---|---|
| G1 | ruff-Pin-Sync CI ↔ pre-commit | 1 | 16 | 12 | 7 |
| G2 | laufende ruff == Pin | 2 | 18 | 18 | 8 |
| G3 | `ruff check` | 3 | 13 | 10 | – |
| G4 | `ruff format --check` | 4 | 14 | 11 | – |
| G5 | das ruff-Gate beisst noch | – | 12 | 9 | – |
| G6 | Zeilenbreite wirksam | – | – | 17 | – |
| G7 | kein Bytecode getrackt | – | 4 | 3 | 11 |
| G8 | referenzierte Dateien existieren | – | 7 | 2 | 10 |
| G9 | Python-Referenzen syntaktisch gueltig | – | 2 | 1 | – |
| G10 | `SKILL.md`-Frontmatter wohlgeformt | – | 5 | 4 | 1 |
| G11 | Version-Badge == CHANGELOG | – | 9 | 7 | 5 |
| G12 | Quality-Chain-Tabelle vollstaendig | – | 10 | 8 | 4 |
| G13 | GitHub-Description == Zaehlwert | – | 15 | 15 | 9 |
| G14 | Zaehlwert konsistent ueber alle Dateien | – | 11, 19 | 5 | 3 |
| G15 | referenzierte Workflows existieren | – | – | 16 | – |
| G16 | Tag == CHANGELOG | – | – | 13 | – |

Drei Entscheide dazu:

* **G6 und G16 werden verallgemeinert.** Beide existieren heute nur in
  fidelity, gelten aber fuer jeden Skill. In diesem Repo steht G6 zudem als
  pytest (`tests/test_ruff_line_length.py`) statt als Check — nach dem Merge
  eine Implementierung, zwei Einstiege.
* **G13 und G14 werden parametrisiert.** Sie zaehlen dasselbe unter anderem
  Namen: probe zaehlt Schritte, fidelity und transport zaehlen Regeln. Die
  Einheit wird Parameter, die Logik ist eine.
* **G2:** fidelity nennt die Funktion `ruff_binary_matches_pin`, die anderen
  `ruff_version_matches_pin`. Gleiche Sache, Name wird angeglichen.

**Skill-eigen — 10 Pruefungen, ziehen unveraendert um** → `tools/suites/<skill>/`

| Pruefung | Herkunft | Nr. |
|---|---|---|
| Skill-Archiv `mcp-audit.skill` aktuell | audit | 5 |
| Shell-Referenz syntaktisch gueltig | probe | 1 |
| Referenz-Importe laufen wirklich | probe | 3 |
| Querverweise loesen auf echte Abschnitte auf | probe | 6 |
| Companion-Zeiger zeigt noch irgendwohin | probe | 8 |
| Adoption-Templates halten ihre Zusagen | probe | 17 |
| Regel ↔ Check-Tabelle vollstaendig | fidelity | 6 |
| Katalog-Drift gegen `mcp-audit-skill` | fidelity | 14 |
| Regel-Abschnitte tragen Gegenbeispiel + Nachweis | transport | 2 |
| offene Namen in `patterns.py` sind auf der Liste | transport | 6 |

53 Registrierungen → 26 Implementierungen. Der Rest ist Kopie.

### 4.3 Konfiguration

| Datei | Entscheid |
|---|---|
| `ruff.toml` | **audit gewinnt**, ohne Abwaegung: `line-length = 88` ist der schmalste Wert im Portfolio, und die Regel dort lautet «der schmalste Wert schreibt den Code». Die drei anderen ziehen nach. Diff pruefen: `ruff format --diff` ueber die einziehenden Baeume. |
| `.pre-commit-config.yaml` | eine Datei; ruff-`rev` == Pin in `lint.yml`, G1 haelt das. |
| `pytest.ini` | audit hat keine — die drei anderen schon. Deren Inhalt uebernehmen, sonst faellt `tests/`-Konfiguration lautlos weg. |
| `.gitattributes` | in allen drei Companions **identisch** (`ec2f696a`), audit hat eine eigene. Vereinigen. |
| `scripts/validate.sh` | eine Datei, ruft `python -m tools.harness`. |
| `.github/workflows/` | `lint.yml` + `test.yml` mit **Path-Filter je Suite**, damit ein Katalog-Typo nicht vier Suiten faehrt. `weekly-drift.yml` entfaellt (siehe 5.), `sdk-drift.yml` bleibt (siehe 6.). |

### 4.4 Inhalte

| Was | Entscheid |
|---|---|
| `SKILL.md` (4×) | nach `skills/<name>/SKILL.md`. Der Frontmatter-`name` bleibt unveraendert — daran haengt das Triggering. |
| `README.md` / `README.de.md` (4×) | je Skill mitziehen; dazu **ein** Repo-README, das die vier vorstellt. |
| `CHANGELOG.md` (4×) | **getrennt lassen**, je Skill. Zusammengelegt waeren die Versionsstaende nicht mehr auseinanderzuhalten, und G11/G16 haengen daran. |
| `reference/` (3×) | nach `skills/<name>/reference/`. Keine Ueberschneidung: probe hat `response_envelope.py`/`retry_backoff.py`, fidelity und transport je eigene `patterns.py`. |
| `tests/` (4×) | Mutationstests bleiben je Suite (`tests/suites/<name>/`), Geruest-Tests einmal. `tests/mutations.py` ist mit 759–1085 abweichenden Zeilen die teuerste Datei des ganzen Umzugs — sie wird **nicht** vereinigt, nur umgehaengt. |

## 5. Was die Zusammenfuehrung nachweislich einspart

**Der Katalog-Drift-Apparat entfaellt — 640 Zeilen.** `mcp-data-fidelity-skill`
haelt seine Regel↔Check-Tabelle gegen den echten Katalog dieses Repos. Weil
der Katalog heute hinter einer Repo-Grenze liegt, braucht das:

* `tools/checks/catalogue.py` (409 Zeilen),
* `scripts/linked_checks.py` (52 Zeilen),
* `.github/workflows/weekly-drift.yml` (179 Zeilen), der die Dateien per
  `raw.githubusercontent.com` an einem gepinnten `$CATALOGUE_COMMIT` ablegt,
* und die Unterscheidung «nicht erreichbar» vs. «abgewichen», damit ein
  Netzaussetzer nicht wie ein Befund aussieht.

Die Begruendung dort sagt es selbst: *«Ein zeitbasierter Fehler gehoert an
einen Zeitplan, nicht an einen Diff.»* Das stimmt — **solange Tabelle und
Katalog in verschiedenen Repos liegen.** Im selben Commit ist die Abweichung
keine Eigenschaft der verstrichenen Zeit mehr, sondern des Diffs. Die Pruefung
wird ein gewoehnliches PR-Gate: `offline=True`, kein Netz, kein Pin, kein
Wochenplan.

**Die dokumentierte Begruendung fuer die Duplizierung faellt weg.** In
`mcp-data-fidelity-skill/tools/checks/_core.py` steht:

> «Zwei Kopien statt eines geteilten Pakets, mit Absicht: Beide Repositories
> sind Dokumentation plus Vorlagen, keines installiert etwas, und eine
> gemeinsame Abhaengigkeit zwischen ihnen waere mehr Maschinerie als die Sache
> traegt.»

Das Argument zielt auf eine Abhaengigkeit **zwischen Repos**. Innerhalb eines
Repos ist ein gemeinsames Modul keine Maschinerie, sondern ein Import.

**Und der Rest der Zahlen:** ~8'800 Zeilen `tools/` + `tests/` + `scripts/`
ueber die drei Companions, in denen keine einzige gemeinsame Datei denselben
Hash hat.

## 6. Was sie NICHT einspart — damit der Plan ehrlich bleibt

* **`sdk-drift.yml` in transport bleibt.** Es misst `reference/patterns.py`
  gegen die jeweils neueste `mcp`-SDK — eine *externe* Abhaengigkeit. Die
  Repo-Grenze ist dort nicht das Problem, und der wochentliche Lauf bleibt
  richtig.
* **`tests/mutations.py` wird nicht billiger.** Die Mutationen sind je Skill
  verschieden, weil die Pruefungen es sind. Der Umzug haengt sie um, er legt
  sie nicht zusammen.
* **Die Quality-Chain-Pruefung (G12) aendert ihren Gegenstand.** Sie prueft
  heute, dass eine Tabelle «alle fuenf Mitglieder» nennt. Nach der
  Zusammenfuehrung sind es zwei Repos mit vier Skills. **Offen:** ob die
  Kette kuenftig Repos oder Skills zaehlt. Zu entscheiden, bevor G12 nach
  `tools/gates/` zieht — sonst zementiert der Merge eine falsche Zahl.

## 7. Phasen

| Phase | Inhalt | Abnahme |
|---|---|---|
| **0** | Geruest `tools/harness/` + Suite-Skopierung + `skills/`-Scaffold | **erledigt** — 15 neue Tests gruen, 1290 bestehende unveraendert gruen |
| **1** | Die 5 eigenen Gates dieses Repos auf `tools/harness/` heben; `tools/checks/` faellt weg | `validate.sh` meldet weiterhin 5 Pruefungen, jetzt als `audit/1…5` |
| **2** | Die 16 generischen Gates nach `tools/gates/` (aus je der besten Fassung), die 10 skill-eigenen nach `tools/suites/` | 26 Implementierungen tragen 53 Registrierungen; jede Suite lueckenlos |
| **3** | Inhalte per `git subtree` nach `skills/<name>/`, Historie erhalten | vier `SKILL.md` am Platz, Frontmatter-`name` unveraendert |
| **4** | Katalog-Drift auf lokal umstellen; `weekly-drift.yml` + `linked_checks.py` loeschen | Pruefung laeuft im PR, `offline=True` |
| **5** | Herkunftsrepos archivieren mit Zeiger-README; `mcp-continuous-auditor` auf den neuen Tag pinnen | keine offenen Verweise mehr |

Phase 1 und 2 sind unabhaengig von 3 — das Geruest laesst sich umstellen,
bevor ein einziger Inhalt umzieht. Das ist Absicht: Die beiden teuren Schritte
sollen nicht am selben Tag stattfinden.

## 8. Migration mit erhaltener Historie

```bash
# je Companion, aus der Wurzel von mcp-audit:
git remote add probe https://github.com/malkreide/mcp-data-source-probe-skill
git fetch probe main
git subtree add --prefix=skills/mcp-data-source-probe probe main
# danach die Dateien innerhalb des Prefix an ihren Zielort schieben
```

`git subtree` statt Submodule: Die Skills sollen im Klon liegen, nicht daneben
haengen. Statt `subtree` geht auch `merge --allow-unrelated-histories` mit
vorherigem `filter-repo`; das Ergebnis ist dasselbe, der Weg laenger.

## 9. Bruchstellen

| Was | Risiko | Abfederung |
|---|---|---|
| `raw.githubusercontent.com/.../mcp-audit-skill/main/checks/…` | Umbenennung des Repos | GitHub leitet Git- und Raw-Zugriffe nach einer **Umbenennung** automatisch weiter — also umbenennen, nicht neu anlegen. `checks/` bleibt am Platz. |
| 110 `github.com/malkreide/mcp-audit-skill`-Links portfolioweit | zeigen ins Leere | dieselbe Weiterleitung; danach in Ruhe nachziehen |
| Skill-Pfade `$SKILL_BASE/tools/…` in `.claude/commands/` | Werkzeuge ziehen um | Phase 1 fasst `tools/` an — die Kommandos im selben PR nachziehen |
| `mcp-continuous-auditor` referenziert alle vier | Pins veralten | Phase 5, gegen einen Tag statt gegen `main` |
| ~20 `*-mcp`-Server-Repos | **ungeprueft** | vor Phase 5 einmal erheben, ob dort Skill-Pfade gepinnt sind. In diesen fuenf Repos gibt es nur vier Raw-Pins, alle auf den Katalog. |
