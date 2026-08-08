---
id: DRIFT-008
title: "Ein Live-Test muss die Quelle erreichen — «markiert» ist nicht «live»"
category: DRIFT
severity: high
applies_when: 'tools_make_external_requests == true'
adoption: advisory
pdf_ref: "Custom (Portfolio-Fundstück zh-education-mcp, 2026-08-08)"
evidence_required: 2
---

# DRIFT-008 — Ein Live-Test, der gegen einen Stub läuft

## Description

Ein Live-Test ist im Katalog kein gewöhnlicher Test. Er ist der **Beleg**: die einzige Stelle, an der eine Annahme über eine fremde Quelle widerlegt werden kann. Jeder andere Test prüft gegen eine Fixture, und die Fixture ist aus derselben Annahme geschrieben wie der Code — sie bestätigt sie, so lange es sie gibt. Deshalb verlangt [`SKILL.md` §2.6](../SKILL.md), dass ein Live-Test, der **nicht gelaufen** ist, `todo` ergibt und nicht `pass`.

Dieser Check ergänzt den zweiten Fall, der genauso aussieht und schlimmer ist: **Der Live-Test ist gelaufen — nur nicht gegen die Quelle.**

Eine Testsuite hält die Unit-Tests hermetisch, und das ist richtig. Sie stubbt Namensauflösung, Zeit, Zufall, Umgebung. Wird auch nur einer dieser Stubs für Live-Tests nicht ausgenommen, prüft der Beleg nichts mehr — und er sagt es nicht. Er wird rot oder grün aus Gründen, die mit der Quelle nichts zu tun haben.

### Der Belegfall

`zh-education-mcp`, 2026-08-08. `tests/test_server.py` trug:

```python
@pytest.fixture(autouse=True)
def _stub_dns(monkeypatch):
    """… damit Unit-Tests hermetisch bleiben (kein echtes DNS) …"""
    monkeypatch.setattr("zh_education_mcp.http_client.socket.getaddrinfo", fake_getaddrinfo)
```

`fake_getaddrinfo` liefert `8.8.8.8`. Die Fixture ist `autouse` für die ganze Datei und nimmt Live-Tests **nicht** aus — die Fixtures in `conftest.py` tun das, diese eine nicht. Der einzige Live-Test jener Datei verband sich also nach `8.8.8.8:443` und sandte SNI `www.bista.zh.ch`. Google antwortet mit einem Zertifikat für `dns.google`:

```
[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed:
Hostname mismatch, certificate is not valid for 'www.bista.zh.ch'
```

**Fünf Läufe lang sah das aus wie ein Befund über die Quelle.** Erst wie ein falsches Zertifikat des Kantons Zürich, dann wie ein flatternder Knoten in einem Pool, dann wie eine Reihenfolge-Abhängigkeit in der Suite. Es kostete einen Diagnoseschritt im Workflow, drei Sonden und zwei Korrekturen an einem bereits veröffentlichten Katalogeintrag, bis der Ausschluss vollständig war. Der Fehler war eine fehlende Zeile:

```python
if "live" in request.keywords:
    return
```

Verschärfend, und der Grund für die Reichweite: Der Stub sieht lokal aus und ist global. `http_client` macht `import socket`, also **ist** `http_client.socket` das stdlib-Modulobjekt. Wer dessen `getaddrinfo` ersetzt, ersetzt es prozessweit — auch für `anyio`, über das `httpx` verbindet. Gemessen:

```
http_client.socket is socket   ->  True
socket.getaddrinfo("www.bista.zh.ch", 443)  ->  ('8.8.8.8', 443)
anyio sieht dieselbe Funktion  ->  True
```

### Warum das ein eigener Check ist

Der **Mechanismus** steht bereits in `OPS-010 b)` — der globale Monkeypatch auf ein fremdes Modul, mit `modul.asyncio` als Belegfall. Das **Kriterium** dort ist ein anderes: `OPS-010` fragt, ob das Brechen einer Zusicherung einen Test rot macht. Diese Frage war hier grün beantwortet. Die Mutationstests von `_confirm_shape` fallen sauber; der Stub hatte mit Mutationsabdeckung nichts zu tun.

Und `DRIFT-005` fragt, ob die Live-Suite **läuft**. Sie lief — fünfmal, mit Issue und Benachrichtigung, genau wie verlangt.

Was keiner der beiden fragt: **ob dabei die Quelle angesprochen wurde.** Genau dort fällt dieser Fall hindurch, und deshalb steht er hier statt als Absatz in `OPS-010`.

`high`: Ein Live-Test, der gegen einen Stub läuft, prüft nichts und behauptet alles. Läuft er grün, ist der Vertrag mit der Quelle ungeprüft und gilt als geprüft. Läuft er rot, erzeugt er einen **Befund über einen Dritten**, den niemand verschuldet hat — im Belegfall beinahe eine Meldung an den Kanton Zürich über ein Zertifikat, das in Ordnung war.

**Zur Nummer:** `DRIFT-007` ist vergeben und zurückgezogen (2026-08-07, aufgegangen in `FID-006`). Die Nummer bleibt verbrannt, damit der Audit-Trail eindeutig bleibt.

## Verification

### Modus 1: code_review (welche Stubs greifen, und nehmen sie Live-Tests aus?)

```bash
# Alle autouse-Fixtures und was sie patchen
grep -rn -B3 -A12 'autouse=True' tests/ | grep -E 'def |setattr|monkeypatch'

# Die üblichen Verdächtigen: Auflösung, Transport, Zeit, Umgebung
grep -rn 'getaddrinfo\|create_connection\|respx\|freeze_time\|setenv\|AsyncHTTPTransport' tests/

# Und die Gegenfrage: Wer nimmt Live-Tests aus?
grep -rn 'request.keywords' tests/
```

Für jede `autouse`-Fixture, die eine Aussenwirkung ersetzt, muss eine der beiden Antworten gelten: Sie nimmt Live-Tests aus, **oder** in ihrem Geltungsbereich existiert kein Live-Test.

### Modus 2: runtime_test (der Wächter)

Ein Wächter, der jeden Live-Test abbricht, dessen Aussenwelt ersetzt wurde. Als Hook und **nicht** als Fixture — die Reihenfolge entscheidet:

```python
# tests/_resolver_guard.py — eigene Datei, damit ein Test sie importieren kann
import socket

_REAL_GETADDRINFO = socket.getaddrinfo          # vor jeder Fixture festhalten


def resolver_is_stubbed() -> bool:
    return socket.getaddrinfo is not _REAL_GETADDRINFO
```

```python
# conftest.py
@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item):
    if "live" in item.keywords and resolver_is_stubbed():
        pytest.fail(
            "Live-Test gegen gestubbten Namensauflöser — eine autouse-Fixture "
            "patcht getaddrinfo ohne `if 'live' in request.keywords: return`.",
            pytrace=False,
        )
    return (yield)
```

**Warum kein Fixture.** Eine Fixture aus `conftest.py` wird **vor** den Fixtures des Testmoduls aufgebaut und **nach** ihnen abgebaut. Beim Aufbau ist der Stub noch nicht gesetzt, beim Abbau hat `monkeypatch` ihn schon zurückgenommen — sie sähe ihn in keinem der beiden Momente und schwiege immer. `pytest_runtest_call` läuft dazwischen.

**Warum `_REAL_GETADDRINFO` ganz oben.** Wer die echte Funktion erst *innerhalb* eines Tests greift, greift die bereits gepatchte. Der Wächter vergliche dann einen Stub mit sich selbst und schwiege für immer.

### Modus 3: runtime_test (Gegenprobe — hat der Wächter Zähne?)

Ein synthetischer Live-Test mit stubbender `autouse`-Fixture, in einer **neuen** Datei. Er muss fallen. Derselbe Test ohne die Fixture muss grün bleiben — ein Wächter, der jeden Live-Test fällt, ist von einem funktionierenden nicht zu unterscheiden und wird nach dem zweiten Fehlalarm abgeschaltet.

## Pass Criteria

- [ ] Jede `autouse`-Fixture, die Auflösung, Transport, Zeit oder Umgebung ersetzt, nimmt Live-Tests aus — oder in ihrem Geltungsbereich existiert nachweislich kein Live-Test
- [ ] Ein Wächter bricht Live-Tests ab, deren Aussenwelt ersetzt wurde, und zwar **suiteweit**, nicht je Datei
- [ ] Der Wächter läuft zwischen Fixture-Aufbau und Testkörper (Hook), nicht als Fixture
- [ ] Der echte Referenzwert wird beim Import festgehalten, vor jeder Fixture
- [ ] Die Gegenprobe ist geführt und in beide Richtungen belegt: Rückfall fällt, ehrlicher Live-Test bleibt grün
- [ ] Die Fehlermeldung nennt die Behebung, nicht nur den Zustand — wer sie liest, sucht sonst zuerst bei der Quelle

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| `autouse`-DNS-Stub ohne Live-Ausnahme | Der Live-Test spricht mit einer fremden Adresse; deren Zertifikat erzeugt einen «Befund» über die eigene Quelle |
| Stub in einer Datei ohne Live-Test, «also unkritisch» | Latent. Der erste Live-Test, der dort dazukommt, läuft in dieselbe Falle |
| Patch auf `modul.socket` / `modul.asyncio` statt auf eine eigene Naht | Wirkt prozessweit, auch auf fremde Bibliotheken im selben Lauf (siehe `OPS-010 b`) |
| Wächter als Fixture statt als Hook | Sieht den Stub nie — weder beim Aufbau noch beim Abbau — und schweigt immer |
| Referenzwert erst im Test festgehalten | Vergleicht einen Stub mit sich selbst; der Wächter ist tot und sieht lebendig aus |
| Wächter ohne Umkehrprobe | Fällt womöglich jeden Live-Test; wird nach dem zweiten Fehlalarm abgeschaltet |
| Live-Marke ohne Aussenkontakt («live» heisst nur langsam) | Die Marke verliert ihre Bedeutung, und §2.6 stützt sich auf eine Marke, die nichts mehr trennt |

## Remediation

Die Ausnahme in jede betroffene Fixture, auch vorsorglich in Dateien ohne heutigen Live-Test:

```diff
 @pytest.fixture(autouse=True)
-def _stub_dns(monkeypatch):
+def _stub_dns(request, monkeypatch):
+    if "live" in request.keywords:
+        return
+
     monkeypatch.setattr("paket.http_client.socket.getaddrinfo", fake_getaddrinfo)
```

Dann der Wächter aus Modus 2. Die Ausnahme behebt den bekannten Fall, der Wächter den nächsten — und der nächste kommt aus einer Datei, die es heute noch nicht gibt.

## Effort

**S–M.** Die Ausnahme ist eine Zeile je Fixture. Der Wächter samt Gegenprobe ist eine halbe Stunde. Teuer ist ausschliesslich die Diagnose, wenn er fehlt: Im Belegfall fünf Läufe, drei Sonden und zwei Korrekturen an einem veröffentlichten Eintrag.

## References

- `SKILL.md` §2.6 — ein Live-Test, der nicht gelaufen ist, ergibt `todo`. Dieser Check ergänzt: einer, der gegen einen Stub lief, ebenfalls
- `DRIFT-005` — ob die Live-Suite läuft. Dieser Check: ob sie dabei die Quelle erreicht
- `OPS-010 b)` — derselbe Mechanismus (globaler Patch auf ein fremdes Modul), anderes Kriterium (Mutationsabdeckung statt Aussenkontakt)
- `FID-003`, `FID-006` — dieselbe Form eine Ebene tiefer: ein Ergebnis, das wie eine Antwort aussieht. Dort im Server, hier im Werkzeug, das ihn prüft
- Belegfall: `zh-education-mcp` PRs #45–#48, 2026-08-08
