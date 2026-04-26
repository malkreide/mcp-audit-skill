# Finding-Template

Pro fehlgeschlagenem Check (Status `fail` oder `partial`) wird ein Finding nach diesem Template erzeugt. Findings sind die Bausteine des Remediation-Plans.

---

## Finding: <CHECK-ID> — <CHECK-TITLE>

| Feld | Wert |
|---|---|
| **Severity** | critical / high / medium / low |
| **Status** | open / in-remediation / accepted-risk / closed |
| **Server** | `<server-name>` |
| **Check-Reference** | `<CHECK-ID>` |
| **PDF-Reference** | Sec X.Y |
| **Audit-Datum** | YYYY-MM-DD |
| **Auditor** | <Name> |

### Observed Behavior

Was wurde im Code, in der Konfiguration oder im Laufzeitverhalten beobachtet? Konkret, mit Datei-Referenzen.

```
Beispiel:
src/server.py:42 verwendet sys.environ["API_KEY"] direkt im Modul-Scope.
Der Schlüssel wird beim Import geladen und beim Logging-Setup
in den structured logs geleakt:

    logger.info(f"Server starting with config: {config}")
    # config enthält API_KEY im Klartext
```

### Expected Behavior

Was würde der Best-Practice-Katalog verlangen?

```
Beispiel:
- API-Keys werden über einen Secret Manager geladen, nicht über
  Umgebungsvariablen
- Falls Env-Vars unvermeidbar: maskiert in allen Log-Outputs
- Pydantic SecretStr für In-Memory-Repräsentation
```

### Evidence

Konkrete Belege, idealerweise mit Datei-Pfad und Zeilen-Nummer:

- File: `path/to/file.py:42`
- Excerpt:
  ```python
  api_key = os.environ["API_KEY"]  # ← unmasked
  ```
- Test output: `<output of grep / curl / runtime test>`
- Screenshot: (optional, nur wenn UI-relevant)

### Risk Description

Welcher konkrete Schaden kann entstehen? **Konkret, nicht theoretisch.**

```
Beispiel:
- Bei Server-Crash und Verbose-Logging landet der API-Key in
  Datadog/CloudWatch
- Wer Read-Zugriff auf Logs hat, hat Read-Zugriff auf den Schlüssel
- Bei Public Repos: Versehen-Push einer .env in Git macht den
  Schlüssel öffentlich (Secret-Scanning hilft, aber zu spät)
```

### Remediation

**Konkrete Schritte**, idealerweise mit Code-Diff:

```diff
- api_key = os.environ["API_KEY"]
+ from pydantic import SecretStr
+ api_key: SecretStr = SecretStr(os.environ["API_KEY"])
+
+ # Bei Logging:
+ logger.info(f"Config loaded, key: {api_key.get_secret_value()[:4]}***")
```

Plus textuelle Anleitung:
1. `pyproject.toml`: `pydantic >= 2.0` als Dependency
2. Migration aller `os.environ["X_KEY"]`-Stellen auf `SecretStr`
3. CI-Test, der nach Klartext-Pattern in Log-Outputs greppt

### Effort Estimate

| Stufe | Definition |
|---|---|
| **S** | < 1 Tag, lokaler Fix in einer Datei |
| **M** | 1–3 Tage, mehrere Dateien, ggf. Tests anpassen |
| **L** | 1–2 Wochen, architektureller Eingriff |
| **XL** | > 2 Wochen, ggf. Breaking Change für externe User |

### Dependencies / Blockers

Hängt das Finding von einem anderen Finding ab? Z.B. «kann erst nach SEC-002 gefixt werden, weil dort die Token-Validierung etabliert wird».

### Verification After Fix

Wie wird verifiziert, dass das Finding behoben ist?
- Re-Audit dieses Checks
- Pytest-Test, der das Anti-Pattern abprüft
- Manueller Code-Review mit Sign-Off

---

## Anhang: Severity-Eskalation

Wenn während der Remediation klar wird, dass das Risiko grösser ist als initial bewertet, kann die Severity hochgestuft werden. Down-Stufung dagegen erfordert Begründung im Finding (z.B. «Kontext-Faktor X reduziert Impact auf medium»).
