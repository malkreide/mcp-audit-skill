"""Die Pruef-Suiten, eine je Skill.

Jede Suite fuehrt ihre eigenen Pruefnummern — `audit/1` und `probe/1` sind
verschiedene Dinge, beide behalten die Nummer, unter der sie in ihrem
CHANGELOG steht. Das gemeinsame Geruest liegt unter `tools/harness/` und
kennt keine einzige Pruefung; es nimmt sie entgegen.

DER IMPORT UNTEN GESCHIEHT UM DER REGISTRIERUNG WILLEN. `@register` laeuft
beim Import. Fehlt eine Suite in dieser Zeile, verschwinden ALLE ihre
Pruefungen aus jedem Lauf, ohne dass etwas rot wird — der Runner meldete dann
«all passed» ueber weniger, als er glaubt. Deshalb haelt
`tests/test_audit_suite.py::test_jede_suite_steht_in_der_importzeile` diese
Zeile gegen den Verzeichnisinhalt.
"""

from . import mcp_audit, mcp_transport_hardening

__all__ = ["mcp_audit", "mcp_transport_hardening"]
