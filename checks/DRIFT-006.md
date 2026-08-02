---
id: DRIFT-006
title: "Der CHANGELOG darf dem Code nicht widersprechen"
category: DRIFT
severity: medium
applies_when: 'always'
pdf_ref: "Custom (Portfolio-Fundstück swiss-energy-mcp, 2026-08-01)"
evidence_required: 2
---

# DRIFT-006 — Prosa, die dem Repo widerspricht, ist schlimmer als fehlende Prosa

## Description

Ein CHANGELOG ist kein Beiwerk, sondern eine Reihe von Behauptungen über den Code. Der Abschnitt `[Unreleased]` ist dabei die einzige Stelle im Repository, die in die **Zukunft** zeigt: Wer ihn liest — die Maintainerin nach zwei Wochen, die Auditorin beim Einstieg, die Nutzerin vor dem Upgrade —, liest ihn als Plan. Was dort steht, gilt als noch nicht getan.

**Der Fall** (`swiss-energy-mcp`): Im `[Unreleased]` stand, die Migration auf das 2.x-SDK bleibe

> a separate, deliberate piece of work

— sie war zu diesem Zeitpunkt längst gemergt. Der Satz war einmal richtig gewesen, hatte den PR überlebt, der ihn widerlegte, und stand nun als Absichtserklärung über einem Repo, das die Absicht bereits ausgeführt hatte.

**Warum das teurer ist als ein fehlender Satz.** Eine Lücke in der Doku führt dazu, dass jemand nachsieht. Ein falscher Satz führt dazu, dass niemand nachsieht — er beantwortet die Frage, bevor sie gestellt wird, und zwar plausibel. Im Fall oben lieferte er zusätzlich eine fertige Erklärung für einen Zustand, der dringend war: Ein Artefakt auf dem Index, das nicht mehr startete, sah aus wie die bekannte, bewusst zurückgestellte Migration — nicht wie ein Ausfall (`IDENT-007`). Die falsche Prosa war die Deckung, unter der ein Befund liegen blieb.

Das ist derselbe Mechanismus wie in `DRIFT-003`, eine Ebene höher: Dort erfüllt der Degradationspfad die Assertion, hier erfüllt die veraltete Absicht die Frage. Beide Male sieht der Ausfall aus wie der erwartete Fall.

### Abgrenzung

| Check | Frage |
|---|---|
| `IDENT-004` | Stimmt die **Zahl** in der Doku (Badge, dokumentierte Version)? Mechanisch vergleichbar, per Skript erzwingbar |
| `IDENT-006` | Ist `[Unreleased]` zu **alt** — steht dort Unveröffentlichtes, das längst hätte released sein müssen? |
| `DRIFT-006` | Ist der Inhalt **wahr** — beschreibt er den Code, wie er heute ist? |

Die drei sind unabhängig. Ein leeres `[Unreleased]` besteht `IDENT-006` und sagt hier nichts; ein aktuelles Badge sagt nichts über einen Satz drei Zeilen darunter. Und dieser Check ist der einzige der drei, für den kein Skript existiert: Zahlen lassen sich vergleichen, Sätze nicht. Deshalb überlebt genau diese Sorte Fehler am längsten — und deshalb ist die Severity `medium` und nicht niedriger: Es bricht nichts, aber es führt die Person in die Irre, die gerade hinsieht.

### Drei Familien, dieselbe Wurzel

1. **`[Unreleased]`-Einträge, die Arbeit als ausstehend beschreiben, die gemergt ist.** Der Fall oben. Entsteht typischerweise so: Der PR, der die Arbeit tat, fügte oben einen `### Added`-Eintrag hinzu — und liess den Satz weiter unten stehen, der sie als ausserhalb des Scopes bezeichnete.
2. **README oder Doku behauptet eine Einschränkung, die es nicht mehr gibt.** «Unterstützt derzeit nur stdio», nachdem HTTP-Transport ausgeliefert wurde. Kostet Nutzung, nicht Korrektheit — aber es kostet sie still.
3. **Kommentare und Docstrings mit «noch nicht».** Der lokalste Fall und der langlebigste, weil ihn nur liest, wer ohnehin schon im Code steht — und dann glaubt.

## Verification

### Modus 1: code_review — jede Behauptung gegen das Repo halten

Der Kern des Checks, und er ist nicht automatisierbar. Für jeden Eintrag in `[Unreleased]` und jeden «noch nicht»-Satz in README/Doku: Wo steht der Code, der ihn bestätigt oder widerlegt?

```bash
# Behauptet der Abschnitt etwas über eine Migration, ein Feature, ein Modul?
sed -n '/## \[Unreleased\]/,/^## \[/p' CHANGELOG.md

# Und ist es passiert? Stichwort aus der Behauptung, gegen die Historie:
git log --oneline -S'fastmcp' -- src/
git log --oneline --grep='2\.x' --since='6 months ago'
```

Ein Eintrag ist **falsch**, wenn der Commit, der ihn widerlegt, bereits auf `main` ist. Ein Eintrag ist **richtig**, wenn er Arbeit beschreibt, die auf `main` liegt und noch nicht publiziert ist — das ist der eigentliche Zweck des Abschnitts.

### Modus 2: automated — die Kandidaten einsammeln

Vorsortieren, nicht urteilen. Absichtsvokabular über die Prosa des Repos:

```bash
grep -rniE '(noch nicht|not yet|derzeit nicht|currently (does not|not)|separate.{0,20}work|geplant|planned|todo|kommt später|coming soon)' \
  CHANGELOG.md README*.md docs/ src/ --include='*.md' --include='*.py'
```

Jede Fundstelle ist eine Behauptung über den Zustand des Codes und wird nach Modus 1 einzeln beantwortet. **Eine leere Trefferliste ist kein Pass** — das Muster kennt nur die Formulierungen, die sein Autor bedacht hat, und ein Absichtssatz kommt ohne jedes Schlüsselwort aus. Ohne Modus 1 ist dieser Check `unverified`.

### Modus 3: config_check — hält der Prozess die Prosa nach?

Beim Release wandern `[Unreleased]`-Einträge in den Versionsabschnitt. Wer das von Hand macht, liest den Abschnitt mindestens einmal ganz — und genau dabei fällt ein widerlegter Satz auf. Wird der Abschnitt maschinell aus Commit-Messages erzeugt, fällt er nie auf: Ein Satz ohne Commit wird nicht mitgenommen, aber auch nicht gelöscht. Prüfen, ob der Release-Prozess einen Schritt kennt, der den Abschnitt **liest**, nicht nur verschiebt.

## Pass Criteria

- [ ] Jeder Eintrag in `[Unreleased]` beschreibt Arbeit, die **nicht** auf `main` ist oder noch nicht publiziert wurde
- [ ] Kein Satz in CHANGELOG, README oder Doku bezeichnet als ausstehend, geplant oder ausserhalb des Scopes, was bereits gemergt ist
- [ ] Keine dokumentierte Einschränkung, die der Code nicht mehr hat
- [ ] Keine Docstrings oder Kommentare mit «noch nicht», die der umgebende Code widerlegt
- [ ] Widersprüche wurden **gefunden, indem jede Behauptung geprüft wurde** (Modus 1) — eine leere `grep`-Trefferliste allein ist `unverified`, nicht Pass
- [ ] Der PR, der eine Absicht ausführt, korrigiert im selben Diff den Satz, der sie als Absicht führt

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| `[Unreleased]`-Satz überlebt den PR, der ihn widerlegt | Der Fall. Der neue Eintrag steht oben, der widersprechende Satz drei Zeilen tiefer |
| Prosa als «nur Doku» behandelt | Sie ist die Antwort, die jemand bekommt, statt nachzusehen — und deshalb wirksamer als der Code, den niemand liest |
| «Lieber ungenau als gar nichts» | Umgekehrt: Fehlende Prosa löst eine Frage aus, falsche beantwortet sie |
| CHANGELOG maschinell aus Commit-Messages erzeugt, Abschnitt nie gelesen | Ein Satz ohne Commit wird nie mitgenommen und nie gelöscht — er bleibt für immer |
| Widerlegter Satz beim Release mitverschoben statt gestrichen | Aus einer falschen Absicht wird eine falsche Release-Notiz, jetzt dauerhaft |
| Falsche Prosa als Erklärung für einen Befund akzeptiert | Genau der teure Fall: Ein toter Index-Stand sah aus wie eine bewusst zurückgestellte Migration (`IDENT-007`) |
| `grep`-Lauf ohne Treffer als Beleg genommen | Ein Absichtssatz braucht kein Schlüsselwort. «Nichts gefunden» ist nicht «nachgesehen» |

## Remediation

### Schritt 1: Den Satz korrigieren, wo er steht

Streichen oder umschreiben — und zwar in dem Zustand, den der Code heute hat, nicht im nächsten Release:

```diff
  ## [Unreleased]

  ### Added
  - Migration auf das 2.x-SDK

- Die Migration auf 2.x bleibt a separate, deliberate piece of work.
```

### Schritt 2: In denselben PR ziehen

Die Regel, die den Rückfall verhindert, ist eine Reihenfolge, kein Werkzeug: **Wer eine Absicht ausführt, streicht sie im selben Diff.** Das kostet dort dreissig Sekunden und ist der einzige Moment, in dem beide Textstellen jemandem gleichzeitig vor Augen stehen.

### Schritt 3: Beim Release den Abschnitt lesen, nicht verschieben

Ein Release ist der letzte Punkt, an dem `[Unreleased]` als Ganzes gelesen wird. Wer den Abschnitt dort einmal Zeile für Zeile gegen `git log` hält, findet die Sätze, die Schritt 2 durchgerutscht sind. Bei generierten CHANGELOGs gehört dieser Blick explizit in die Release-Checkliste, weil ihn sonst niemand tut.

## Effort

S — den einzelnen Satz zu korrigieren, kostet Minuten. Der Aufwand liegt im Durchgehen: Ein Repo mit langem `[Unreleased]` braucht eine halbe Stunde, in der jede Zeile gegen die Historie gehalten wird.

## References

- Portfolio-Fundstück `swiss-energy-mcp` — `[Unreleased]` führte die 2.x-Migration als «a separate, deliberate piece of work», während sie gemergt war
- `DRIFT-003` — derselbe Mechanismus im Test: Der Ausfall erfüllt die Assertion, hier erfüllt die veraltete Absicht die Frage
- `IDENT-004` — dokumentierte **Zahl** (Badge); mechanisch prüfbar, deshalb ein anderer Check
- `IDENT-006` — `[Unreleased]` zu alt (Release-Gap) statt inhaltlich falsch
- `IDENT-007` — der Befund, den die falsche Prosa im Fall oben gedeckt hat
- `OPS-004` — Audit-Redlichkeit: eine Vermutung, die einen unerklärten Rest schliesst, ist dieselbe Fehlerklasse im Report statt im Repo
