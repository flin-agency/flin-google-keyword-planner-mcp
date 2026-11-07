# Hilfe

1. Claude vollständig neu starten bzw. den MCP-Server neu verbinden.
2. `connection_status` aufrufen (ab Server 0.3.3). `server_version` ist die laufende
   PyPI-Version, nicht die in Claude angezeigte Erweiterungsversion.
3. Bei `configuration_status=incomplete` die Pflichtfelder und Konto-ID-Formate
   prüfen. Customer ID bezeichnet das Zielkonto; `login_customer_id` ist nur beim
   Zugriff über ein berechtigtes MCC erforderlich. Werte kommen vom zuständigen
   Administrator/Passwortmanager, nicht aus öffentlichen Beispielen.
4. Bei `auth_status=unauthenticated` den lokalen OAuth-Login starten. `unknown`
   bedeutet: Token vorhanden oder lokaler Zustand unklar, nicht live geprüft.
   Für echte Kontoberechtigungen ist eine ausdrücklich ausgelöste Keyword-Abfrage
   nötig. Der Standardstatus bleibt `live_access=not_checked`.

Fehlende Daten (`null`) sind nicht null Suchanfragen. Standardwerte sind Englisch,
USA und Search mit Partnern; Sprache und Region für deinen Test ausdrücklich setzen.
Google kontrolliert Datenverfügbarkeit, Konto-Zulassung, Kontingente und Gruppierung
ähnlicher Begriffe. Ein Fehler beim Zugriff kann trotz lokal vorhandener Tokens auftreten.

## PyPI vorübergehend nicht erreichbar

Der bisherige Ansatz bleibt bestehen: Der Starter aktualisiert bei jedem Start,
und es gibt **keinen automatischen Offline-/Cache-Fallback**. Eine laufende Sitzung
bleibt unberührt. Bei Startproblemen zuerst die Internetverbindung prüfen und nach
Ende der Störung erneut starten. Alte Einstellungen und Tokens werden nicht gelöscht.

Als bewusster manueller Fallback kann ein Administrator eine zuvor geprüfte Version
fest auswählen, zum Beispiel in der [manuellen Konfiguration](README.md#claude-integration):

```json
"command": "uv",
"args": ["tool", "run", "--offline", "--from", "flin-google-keyword-planner-mcp==0.3.3", "flin-google-keyword-planner-mcp"]
```

Die vorhandenen Credential-Felder beibehalten. Das funktioniert nur, wenn diese
Version, Python und sämtliche Abhängigkeiten bereits vollständig im UV-Cache liegen;
es kann sonst ebenfalls fehlschlagen. Dieser Modus aktualisiert **nicht** automatisch
und muss sichtbar als manueller Fallback behandelt werden. Mit `connection_status`
die gewählte Serverversion prüfen und nach der Störung zur normalen Erweiterung
zurückkehren. Google-Abfragen brauchen weiterhin Zugriff auf Google.

## Fehler melden

[GitHub-Issue erstellen](https://github.com/flin-agency/flin-google-keyword-planner-mcp/issues).
Hilfreich sind macOS-/Claude-Version, Erweiterungsversion, `server_version`, die fünf
Felder aus `connection_status` und eine bereinigte Fehlermeldung. Keine Zugangsdaten,
OAuth-URLs mit Codes, Konto-/Kundendaten oder vollständige private Logs veröffentlichen.
Sicherheitsmeldungen gehören in einen privaten Kanal: [SECURITY.md](SECURITY.md).
