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
├── SKILL.md                    # DER mcp-audit-Skill selbst — bleibt in der
│                               #   Wurzel, das Paket spiegelt den Baum (4.2c)
├── checks/                     # KATALOG, 121 Dateien — bleibt, wo er ist
├── templates/                  # was das Audit nach draussen schreibt
├── skills/                     # die drei Companions  ← Phase 3a, steht
│   ├── mcp-data-source-probe/  # SKILL.md, READMEs, CHANGELOG, reference/
│   ├── mcp-data-fidelity/      # dito
│   └── mcp-transport-hardening/# dito
├── tools/
│   ├── harness/                # das EINE Geruest  ← Phase 0, steht
│   │   ├── _core.py            #   Registry, Ausfuehrung, CheckFailed
│   │   └── __main__.py         #   Runner + die eine Stelle, die die Suiten kennt
│   ├── gates/                  # die 16 GENERISCHEN Pruefungen  ← Phase 2
│   ├── suites/mcp_audit/       # Suite «audit», 5 Pruefungen  ← Phase 1, steht
│   ├── suites/<skill>/         # je Skill die eigenen Pruefungen ← Phase 2/3
│   └── …                       # Audit-Werkzeuge, unveraendert
└── tests/
```

`checks/` wird **nicht** umbenannt. Der Katalog wird von aussen unter
`raw.githubusercontent.com/malkreide/mcp-audit-skill/main/checks/…` zitiert;
ein Umzug braeche diese Verweise ohne Gegenwert. Das Pruefgeruest liegt unter
`tools/`, es kollidiert nicht.

## 3. Die Nummernfrage — entschieden

Die vier Registries numerieren jede ab 1, und die Registry-Pruefung dieses
Repos (damals `tests/test_checks_registry.py`, heute `tests/test_audit_suite.py`)
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

| # | Familie | audit | probe | fidelity | transport | Stand |
|---|---|---|---|---|---|---|
| G1 | ruff-Pin-Sync CI ↔ pre-commit | 1 | 16 | 12 | 7 | **erledigt** |
| G2 | laufende ruff == Pin | 2 | 18 | 18 | 8 | **erledigt** |
| G3 | `ruff check` | 3 | 13 | 10 | – | **erledigt** |
| G4 | `ruff format --check` | 4 | 14 | 11 | – | **erledigt** |
| G5 | das ruff-Gate beisst noch | – | 12 | 9 | – | **erledigt** |
| G6 | Zeilenbreite wirksam | – | – | 17 | – | **erledigt** |
| G7 | kein Bytecode getrackt | – | 4 | 3 | 11 | Phase 2b |
| G8 | referenzierte Dateien existieren | – | 7 | 2 | 10 | Phase 2b |
| G9 | Python-Referenzen syntaktisch gueltig | – | 2 | 1 | – | Phase 2b |
| G10 | `SKILL.md`-Frontmatter wohlgeformt | – | 5 | 4 | 1 | Phase 2b |
| G11 | Version-Badge == CHANGELOG | – | 9 | 7 | 5 | Phase 2b |
| G12 | Quality-Chain-Tabelle vollstaendig | – | 10 | 8 | 4 | Phase 2b |
| G13 | GitHub-Description == Zaehlwert | – | 15 | 15 | 9 | Phase 2b |
| G14 | Zaehlwert konsistent ueber alle Dateien | – | 11, 19 | 5 | 3 | Phase 2b |
| G15 | referenzierte Workflows existieren | – | – | 16 | – | Phase 2b |
| G16 | Tag == CHANGELOG | – | – | 13 | – | Phase 2b |

Drei Entscheide dazu:

* **G6 und G16 werden verallgemeinert.** Beide existieren heute nur in
  fidelity, gelten aber fuer jeden Skill. (Der urspruengliche Zusatz, G6 stehe
  hier bereits als pytest, war falsch — siehe 4.2d.)
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

### 4.2a Wo die Suiten verdrahtet werden (Entscheid aus Phase 1)

`@register` laeuft beim Import — die Suiten muessen also geladen sein, bevor
der Runner die Registry befragt. Die Frage ist, WER sie laedt.

Nicht `_core.py`: Es soll keine Pruefung kennen, sonst ist es nicht mehr
kopierbar. Nicht `tools/suites/__init__.py` allein: Damit importierte jeder
Zugriff auf irgendeine Suite alle anderen mit.

**Entscheid: `tools/harness/__main__.py` importiert `tools.suites`.** Der
Einstiegspunkt ist die eine Stelle, die weiss, welche Suiten es in DIESEM Baum
gibt; das Geruest darunter bleibt generisch. `tools/suites/__init__.py` fuehrt
die Liste der Suiten, `tools/suites/<name>/__init__.py` die Liste ihrer
Module — und `tests/test_audit_suite.py` haelt beide Listen statisch gegen den
Verzeichnisinhalt. Eine fehlende Zeile ist auf beiden Ebenen ein lautloser
Totalausfall, deshalb sind es zwei Pruefungen und nicht eine.

Der Suite-Name steht in `tools/suites/<name>/_suite.py` und nicht in dessen
`__init__.py`: Dort stehen die Modul-Importe, und die Pruefmodule brauchen den
Namen genau waehrend dieses Imports — beides in einer Datei waere ein Zyklus.

### 4.2b Was der erste Zusammenzug gezeigt hat (G1/G2, erledigt)

Die Toolchain-Familie ist zusammengelegt: `tools/gates/toolchain.py` traegt
jetzt eine Implementierung fuer alle vier Suiten. Drei Befunde daraus, die
fuer die uebrigen vierzehn Familien gelten:

**1. Der Unterschied war ein Dateiname.** Der ruff-Pin steht hier in
`lint.yml`, in den drei Schwesterrepos in `ci.yml`. Das war der einzige
inhaltliche Grund, warum vier Kopien existierten. Er ist jetzt Parameter
(`ci_workflow=`), und ein Test faehrt beide Schreibweisen gegen dieselbe
Implementierung.

**2. Verbesserungen sind in ihrer Kopie haengengeblieben.** Nur
`mcp-data-fidelity-skill` prueft, ob die Pre-Commit-Hooks ueberhaupt noch da
sind, und listet beschattende `ruff`-Binaries im Befund. Die anderen drei tun
es nicht — ohne dass jemand dagegen entschieden haette. Beides ist mit dem
Zusammenzug fuer alle da. Das ist der eigentliche Ertrag der Uebung, und er
ist groesser als die eingesparten Zeilen.

**3. Nicht jeder Unterschied ist Drift.** `mcp-transport-hardening-skill`
fuehrt nur `ruff-format` und keinen `ruff-check`-Hook. Das sah zunaechst nach
einer Luecke aus, ist aber begruendet: Dort steht `select = []` in `ruff.toml`
bewusst, damit ein `ruff check` im Clone nicht ueber Vorlagen-Code faellt, und
die CI prueft stattdessen gezielt mit `ruff check --extend-select …` auf
`reference/` und `tools/ tests/`. Deshalb ist `required_hooks` LEER per
Vorgabe und wird je Suite genannt: Eine Vorgabe waere keine gemeinsame
Zusage, sondern eine erfundene — und der erste, der sie «erfuellt», braeche
die Absicht des Repos, das sie nicht teilt.

**Wo die Logik hinkam, und warum das eine Entscheidung war.** Vorher trug
`tools/check_ruff_pin.py` die Vergleichsfunktion, weil der Pre-Commit-Hook sie
DIREKT aufruft (`entry: python3 tools/check_ruff_pin.py`, `language: system`),
und das Suite-Modul war der Adapter. Haette der generische Zusammenzug daneben
eine zweite Implementierung gestellt, waere aus der Entdopplung eine
Verdopplung geworden. Jetzt traegt `tools/gates/` die Logik, und beide
Einstiege sind Huellen darum — der Hook-Einstiegspunkt ist unveraendert, und
die Tests der reinen Funktionen laufen ueber ihre alten Importe weiter.

**Abnahme des Zusammenzugs:** Das Gate wurde gegen ALLE VIER echten Baeume
gefahren, jeder mit seinen eigenen Parametern — die Pruefungen nehmen `root`
entgegen, das geht auch, bevor ein Inhalt umzieht. Acht Laeufe, acht gruen.
Dieselbe Abnahme gilt fuer jede weitere Familie.

### 4.2c Was Phase 3a gezeigt hat

**Die Wurzel-`SKILL.md` bleibt, wo sie ist — begruendet.** Der Plan sah
`skills/mcp-audit/SKILL.md` vor. Beim Umsetzen stellte sich heraus, dass das
am Paketformat scheitert: `mcp-audit.skill` SPIEGELT den Repository-Baum, und
`SKILL.md` muss an der Paketwurzel liegen. Ein Umzug brauchte eine
Umsortierung statt einer Spiegelung — also genau den Bruch, gegen den
`skill-manifest.txt` geschrieben ist, samt Umbau von `build_skill.py` und
`skill_package.py`. Aufteilung deshalb: die Wurzel IST der `mcp-audit`-Skill,
`skills/` haelt die drei Companions. Begruendung ausfuehrlich in
`skills/README.md`.

**`ruff.toml` «audit gewinnt» reicht nicht — Vorlagen-Code braucht eine
Ausnahme.** Gemessen beim Einzug: 31 der 32 Befunde in
`skills/mcp-transport-hardening/reference/patterns.py` waren F821
(undefinierter Name), dazu einer in `skills/mcp-data-fidelity/`. Das ist kein
Maengel, sondern der Zweck: Vorlagen-Code zeigt Muster und referenziert Namen,
die erst im Zielserver existieren. Das Herkunftsrepo faehrt aus genau diesem
Grund `--ignore F821`. Geloest mit `[lint.per-file-ignores]` fuer
`skills/*/reference/*.py` — eng gefasst, damit der uebrige Baum streng bleibt.

**Der strengere Regelsatz hat sofort etwas gefunden.** Ein I001 (unsortierte
Importe) in `skills/mcp-transport-hardening/reference/patterns.py`, das
dessen engeres `ruff check --extend-select E4,E7,E9,F` nie geprueft hat. Eine
Zeile, mechanisch behoben. Das ist derselbe Ertrag wie in Phase 2a, aus der
anderen Richtung: Vier Konfigurationen pruefen vier verschiedene Teilmengen,
und keine davon ist die Vereinigung.

**Die READMEs der drei Skills nennen Pfade ihres alten Repos.** Gemessen 33
Verweise auf `scripts/`, `tools/checks/`, `ruff.toml`, `.pre-commit-config.yaml`
und Workflows. Ein Teil davon existiert in der neuen Wurzel, ein Teil kommt
erst mit Phase 2b. Sie jetzt umzuschreiben hiesse, sie nach 2b ein zweites Mal
umzuschreiben; sie unkommentiert stehen zu lassen hiesse, falsche Pfade zu
dokumentieren. Zwischenloesung: ein Hinweis am Kopf beider READMEs je Skill,
der den Stand nennt und auf diesen Plan zeigt. Die Neufassung gehoert zu 2b.

**`sdk-drift.yml` ist NICHT mitgezogen und muss vor Phase 5 umziehen.** Der
Workflow misst `reference/patterns.py` gegen die jeweils neueste `mcp`-SDK und
bleibt noetig (Abschnitt 6). Er laeuft weiter im Herkunftsrepo, solange das
existiert — vor dem Archivieren gehoert er nach `.github/workflows/` dieses
Repos, mit angepasstem Pfad. `weekly-drift.yml` dagegen entfaellt ersatzlos,
das ist Phase 4.

### 4.2d Was 2b-i gezeigt hat (G3–G6)

**Zum zweiten Mal: nicht jeder Unterschied ist Drift.** `line_length_effective`
misst beide Haelften — ob das Lint-Gate bei genau der deklarierten Breite E501
meldet, und ob der Formatter dort umbricht. Die erste Haelfte hat in DIESEM
Repo keinen Gegenstand: `ruff.toml` fuehrt E501 ausdruecklich nicht im
`select` («das entscheidet der Formatter»). Mit der Fassung aus
`mcp-data-fidelity-skill` waere jeder Lauf hier rot geworden — aus einem
Grund, der eine Zeile weiter oben als Entscheidung dokumentiert steht.

`lint_enforces_e501` hat deshalb **keine Vorgabe** und ist ein Pflichtargument.
Anders als bei `required_hooks` in 2a gibt es hier keine harmlose Seite:
`True` erfaende einen Befund, `False` naehme der Pruefung stillschweigend ihre
Lint-Haelfte. Wer sie bindet, muss es sagen.

**Die Zusammenfuehrung bringt diesem Repo zwei Pruefungen, die es nicht
hatte** — `audit/6` (beisst das Gate noch?) und `audit/7` (wirkt die Breite?).
Beide gab es nur in den Schwesterrepos. `audit/6` ist dabei kein Luxus,
sondern faellig geworden: Phase 3a hat `ruff.toml` um
`[lint.per-file-ignores]` fuer `skills/*/reference/*.py` erweitert, und genau
diese Sorte Schalter schaltet ein Gate stillschweigend ab, wenn ihn jemand
weitet.

**Eine Plan-Annahme war falsch.** Unter 4.2 stand, G6 existiere in diesem Repo
bereits als pytest (`tests/test_ruff_line_length.py`) und werde durch den
Merge zu «eine Implementierung, zwei Einstiege». Das stimmt nicht: Jener Test
prueft, ob die Zahl die RICHTIGE ist (der schmalste Wert im Portfolio), G6
misst, ob sie WIRKT. Zwei Fragen, keine Dublette — beide bleiben.

**Was aus welcher Fassung kam:** der aufgeloeste Binary-Pfad
(`shutil.which`) aus audit, `--no-cache` und `--output-format=concise` aus
probe und fidelity, die Breiten-Sonde aus fidelity allein. Jedes davon war in
seiner Kopie haengengeblieben.

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
* **Die Quality-Chain-Pruefung (G12) aendert ihren Gegenstand** — entschieden,
  siehe 6.1. Der Umbau ist keine Ersparnis, sondern Folgearbeit.

### 6.1 Die Kette zaehlt kuenftig SKILLS, nicht Repos (entschieden)

**Entscheid:** Mitglied der Qualitaetskette ist ein SKILL. Damit hat die Kette
**vier** Mitglieder statt fuenf.

Was daraus folgt, und was daran unbequem ist:

`mcp-continuous-auditor` faellt als Mitglied heraus — es ist kein Skill. Damit
verliert die Stufe «im Betrieb / Haelt er morgen noch?» ihren Traeger. Das ist
kein Verlust der Sache, sondern ihre richtige Einordnung, und sie deckt sich
mit dem Schnitt aus Abschnitt 1: Der Auditor ist die **Laufzeit, die die Kette
faehrt**, kein Glied in ihr. Er steht kuenftig in der Prosa beider READMEs als
Motor daneben, nicht als fuenfte Zeile in der Tabelle.

**Zielzustand von `docs/quality-chain.json`:** `members` traegt vier Eintraege,
je Skill statt je Repo — Schluessel `skill` (`mcp-audit`,
`mcp-data-source-probe`, `mcp-data-fidelity`, `mcp-transport-hardening`) statt
`repo`. Die Stufen bleiben: vor dem Bau, im Bau (zweimal), nach dem Bau.

**Umgestellt wird in Phase 3, nicht frueher.** Der Grund ist messbar:

1. `tools/check_quality_chain.py` prueft die GitHub-Metadaten (Topic,
   Homepage) JE MITGLIED. Solange die Mitglieder Skills sind, die noch in
   eigenen Repos liegen, braucht der Waechter weiterhin deren Repo-Namen —
   erst nach dem Umzug faellt die Unterscheidung Skill/Repo zusammen.
2. Die drei Companion-Repos fuehren die fuenf Namen HART in ihren eigenen
   Pruefungen (`readmes.py`, `CHAIN_SECTIONS`) und halten ihre READMEs
   dagegen. Ein Wechsel allein hier ergaebe ein Repo, das vier zaehlt, und
   drei, die fuenf verlangen.

Bis dahin bleibt das Manifest bei fuenf Repo-Eintraegen. Die Zahl ist damit
nicht falsch, sondern noch nicht umgestellt — und G12 zieht erst nach
`tools/gates/`, wenn sie es ist.

**Umgesetzt in Phase 3b** — und dabei kam eine Aufteilung dazu, die im Plan
noch nicht stand:

| Stelle | vorher | jetzt |
|---|---|---|
| `docs/quality-chain.json` | 5 `members` mit `repo` | 4 `members` mit `skill` + `path`, dazu `repos` mit 2 Eintraegen |
| `tools/check_quality_chain.py` | iteriert `members`, liest `m["repo"]` | iteriert `repos` |
| `tests/test_quality_chain.py` | `assert len(members) == 5` | `== 4`, plus vier neue Anker |
| beide READMEs, Abschnitt Kette | 5 Repo-Zeilen | 4 Skill-Zeilen + Auditor in der Prosa |
| `readmes.py` der drei Companions | 5 harte Namen | unveraendert, entfaellt mit Phase 2b |

**ZWEI LISTEN, WEIL ES ZWEI FRAGEN SIND.** Der Plan hatte `members` einfach
von Repos auf Skills umgestellt — beim Umsetzen zeigte sich, dass das dem
Waechter den Gegenstand nimmt: Topic und Homepage sind Eigenschaften eines
REPOSITORIES, und drei der vier Skills haben seit Phase 3a keins mehr. Das
Manifest fuehrt deshalb beides getrennt: `members` ist die Kette (welche Frage
an welcher Stelle), `repos` sagt dem Waechter, wessen Metadaten er prueft.
Solange Skill und Repo dasselbe waren, fiel das nicht auf.

`path` je Mitglied ist dabei neu und traegt eine eigene Pruefung: Sie haelt
das Manifest gegen den BAUM statt gegen eine Annahme — jedes Mitglied zeigt
auf eine echte `SKILL.md`, deren Frontmatter-`name` mit dem Manifest
uebereinstimmt. Ein Mitglied, dessen Verzeichnis niemand mehr pflegt, faellt
damit hier auf und nicht erst, wenn jemand den Skill installieren will.

## 7. Phasen

| Phase | Inhalt | Abnahme |
|---|---|---|
| **0** | Geruest `tools/harness/` + Suite-Skopierung + `skills/`-Scaffold | **erledigt** — 15 neue Tests gruen, 1290 bestehende unveraendert gruen |
| **1** | Die 5 eigenen Gates dieses Repos auf `tools/harness/` heben; `tools/checks/` faellt weg | **erledigt** — `validate.sh` meldet 5 Pruefungen als `audit/1…5`, alle gruen |
| **2a** | G1 und G2 nach `tools/gates/toolchain.py`, Einstiegspunkte als Huellen | **erledigt** — gegen alle vier Baeume gruen, 1315 Tests |
| **2b-i** | G3–G6 nach `tools/gates/ruff.py` | **erledigt** — gegen drei Baeume gruen, audit bekommt zwei Pruefungen dazu |
| **2b-ii** | G7–G9, G15 (Dateien und Hygiene) | |
| **2b-iii** | G10–G14, G16 (Doku und Zaehlwerte) | |
| **2b-iv** | die 10 skill-eigenen Pruefungen, READMEs neu fassen | 26 Implementierungen tragen 53 Registrierungen; jede Suite lueckenlos |
| **3a** | Die drei Companions per `git subtree` nach `skills/<name>/`, Historie erhalten | **erledigt** — drei `SKILL.md` am Platz, Frontmatter-`name` unveraendert, 1315 Tests gruen |
| **3b** | Kette auf vier Skills umstellen (6.1), beide READMEs nachziehen | **erledigt** — `quality-chain.json` fuehrt vier Skills und zwei Repos, 1319 Tests gruen |
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
