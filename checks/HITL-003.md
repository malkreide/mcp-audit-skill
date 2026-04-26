---
id: HITL-003
title: "Data Redaction: PII-Filter vor LLM-Send"
category: HITL
severity: critical
applies_when: 'data_class != "Public Open Data" and uses_sampling == true'
pdf_ref: "Sec 7.2"
evidence_required: 3
---

# HITL-003 — Data Redaction vor LLM-Send

## Description

Wenn ein Server Sampling verwendet **und** Verwaltungsdaten/PII verarbeitet, fliessen diese Daten via Sampling-Prompt an den LLM-Provider (z.B. Anthropic, OpenAI). Das ist nicht nur ein Daten-Leak-Risiko, sondern bei DSG-relevanten Daten ein direkter Compliance-Bruch (siehe CH-001 Datenresidenz und CH-002 Personendaten-Verarbeitung).

Der Best-Practice-Standard verlangt: **Vor jedem Sampling-Call** durchläuft der Prompt einen Redaction-Filter, der bekannte PII-Pattern entfernt oder anonymisiert. Beispiele für PII-Pattern im Schweizer Kontext:

- AHV-Nummer (Format `756.XXXX.XXXX.XX`)
- IBAN (Format `CH...`)
- E-Mail-Adressen
- Telefonnummern (Schweizer Format)
- Vollständige Namen (heuristisch — Vorsicht: schwer 100% korrekt)
- Adressen
- Geburtsdaten

Bei Schulamt-Kontext zusätzlich: Schüler-Namen, Klassen-Identifikatoren, Eltern-Daten, IF/IS-Klassifikation.

Dieser Check ist `critical`, weil er sowohl rechtlich (DSG) als auch operativ (Vertrauen in Verwaltungs-KI) entscheidend ist.

## Verification

### Modus 1: code_review (Redaction-Filter implementiert)

```bash
grep -rE 'redact|anonymi[sz]e|pii_filter|sanitize.*pii' src/
```

**Pass-Pattern:**

```python
import re

# Schweiz-spezifische PII-Patterns
PII_PATTERNS = [
    # AHV-Nummer
    (re.compile(r"\b756\.\d{4}\.\d{4}\.\d{2}\b"), "[AHV-NR]"),
    # IBAN CH
    (re.compile(r"\bCH\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{1}\b"), "[IBAN]"),
    # E-Mail
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[EMAIL]"),
    # CH-Telefon (vereinfacht)
    (re.compile(r"\b(?:\+41|0041|0)\s?[1-9]\d(?:\s?\d{2,3}){2,3}\b"), "[PHONE]"),
    # Geburtsdatum DD.MM.YYYY
    (re.compile(r"\b\d{2}\.\d{2}\.(?:19|20)\d{2}\b"), "[BIRTHDATE]"),
    # PLZ + Ort (heuristisch — entfernt nur, nicht 100% sicher)
    (re.compile(r"\b\d{4}\s+[A-ZÄÖÜ][a-zäöü]+\b"), "[PLZ-ORT]"),
]

# Schulamt-spezifisch
SCHULAMT_PATTERNS = [
    # Klassen-Bezeichnung (z.B. "Schulhaus Limmat 5b")
    (re.compile(r"\bSchulhaus\s+[A-ZÄÖÜ]\w+\s+\d[a-z]?\b"), "[KLASSE]"),
]

def redact_pii(text: str, additional_patterns: list = None) -> str:
    """Entfernt bekannte PII-Pattern aus Text. Fehlt: NER für Namen."""
    patterns = PII_PATTERNS + (additional_patterns or [])
    for pattern, replacement in patterns:
        text = pattern.sub(replacement, text)
    return text


@mcp.tool()
async def summarize_dossier(dossier_id: str, ctx: Context) -> dict:
    raw_dossier = await api.get_dossier(dossier_id)
    redacted = redact_pii(
        raw_dossier["text"],
        additional_patterns=SCHULAMT_PATTERNS,
    )

    # Audit-Log: dass Redaction stattfand
    audit_logger.info(
        "sampling_with_redaction",
        dossier_id=dossier_id,
        redaction_count=len(re.findall(r"\[\w+\]", redacted)),
        original_len=len(raw_dossier["text"]),
        redacted_len=len(redacted),
    )

    result = await ctx.sample(
        messages=[{"role": "user", "content": f"Fasse zusammen:\n{redacted}"}],
        max_tokens=300,
    )
    return {"summary": result.content, "redacted": True}
```

### Modus 2: runtime_test (Redaction wirksam)

```python
def test_pii_redaction():
    text = "Anna Müller, AHV 756.1234.5678.90, anna@beispiel.ch, geb. 15.03.1985"
    redacted = redact_pii(text)
    assert "756.1234.5678.90" not in redacted
    assert "anna@beispiel.ch" not in redacted
    assert "15.03.1985" not in redacted
    assert "[AHV-NR]" in redacted
    assert "[EMAIL]" in redacted
    assert "[BIRTHDATE]" in redacted
```

### Modus 3: documentation_check (Redaction-Policy dokumentiert)

Im Repo prüfen:

```bash
find . -iname 'redaction*' -o -iname 'pii*' -o -iname 'data-handling*'
```

**Pass:** Dokument vorhanden mit Liste aller verwendeten Pattern, Begründung, Update-Verfahren bei neuen Pattern-Anforderungen.

## Pass Criteria

- [ ] Redaction-Funktion implementiert mit Schweiz-spezifischen PII-Patterns
- [ ] Redaction wird vor **jedem** Sampling-Call angewandt (nicht selektiv)
- [ ] Redaction-Pattern abgedeckt: AHV, IBAN, E-Mail, Telefon, Geburtsdatum
- [ ] Bei Schulamt-Kontext: zusätzliche Pattern für Klassen-/Schulhaus-Bezeichner
- [ ] Audit-Log dokumentiert Redaction-Aktivität (Anzahl entfernter Pattern)
- [ ] Tests decken Redaction-Edge-Cases ab
- [ ] Redaction-Policy in `docs/`-Verzeichnis dokumentiert

## Common Failures

| Anti-Pattern | Risiko |
|---|---|
| Sampling ohne Redaction | DSG-Verstoss bei PII-Verarbeitung |
| Nur englische PII-Pattern | CH-spezifische Daten (AHV, IBAN-CH) bleiben unredacted |
| Regex zu eng (kein Unicode) | Namen mit Umlauten werden nicht erkannt |
| Redaction nur bei einigen Tools | Inkonsistenter Schutz |
| Names-NER-Erkennung fehlt | Vornamen/Nachnamen bleiben durch (akzeptabel als bekannte Lücke, dokumentieren) |

## Remediation

### Schritt 1: Redaction-Modul erstellen

```python
# src/redaction.py
import re
from dataclasses import dataclass
from typing import Pattern


@dataclass(frozen=True)
class RedactionRule:
    pattern: Pattern[str]
    replacement: str
    description: str


CH_PII_RULES = [
    RedactionRule(
        re.compile(r"\b756\.\d{4}\.\d{4}\.\d{2}\b"),
        "[AHV-NR]",
        "Schweizer AHV-Nummer",
    ),
    RedactionRule(
        re.compile(r"\bCH\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{1}\b"),
        "[IBAN]",
        "IBAN Schweiz",
    ),
    RedactionRule(
        re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
        "[EMAIL]",
        "E-Mail-Adresse",
    ),
    RedactionRule(
        re.compile(r"\b(?:\+41|0041|0)\s?[1-9]\d(?:\s?\d{2,3}){2,3}\b"),
        "[PHONE]",
        "Schweizer Telefonnummer",
    ),
    RedactionRule(
        re.compile(r"\b\d{2}\.\d{2}\.(?:19|20)\d{2}\b"),
        "[BIRTHDATE]",
        "Geburtsdatum DD.MM.YYYY",
    ),
]


def redact(text: str, rules: list[RedactionRule] = CH_PII_RULES) -> tuple[str, dict[str, int]]:
    """Returns redacted text and counts per rule."""
    counts: dict[str, int] = {}
    for rule in rules:
        new_text, count = rule.pattern.subn(rule.replacement, text)
        if count > 0:
            counts[rule.description] = count
        text = new_text
    return text, counts
```

### Schritt 2: Wrapper für Sampling

```python
async def sample_with_redaction(ctx: Context, prompt: str, **kwargs):
    redacted, counts = redact(prompt)
    if counts:
        audit_logger.info("sampling_redaction_applied", counts=counts)
    return await ctx.sample(
        messages=[{"role": "user", "content": redacted}],
        **kwargs,
    )
```

### Schritt 3: Pre-Commit Hook (optional)

```yaml
- repo: local
  hooks:
    - id: pii-test
      name: PII redaction test must pass
      entry: pytest tests/test_redaction.py -v
      language: system
      pass_filenames: false
```

## Effort

M — 1–3 Tage. Pattern-Sammlung + Tests + Wrapper + Doku.

## References

- PDF Sec 7.2 — Data Redaction
- CH-001 — Datenresidenz
- CH-002 — DSG-konforme Personendaten-Verarbeitung
- [revDSG Art. 31](https://www.fedlex.admin.ch/eli/cc/2022/491/de)
