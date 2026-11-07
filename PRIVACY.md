# Datenschutz

Der MCP-Server läuft lokal im MCP-Client. Keyword- und URL-Anfragen sowie Konto-
und Zielgebietsangaben gehen an die Google Ads API. Die Ergebnisse gelangen zurück
an Claude bzw. den verwendeten MCP-Client; dessen eigene Speicherung und
Datenschutzbedingungen gelten zusätzlich. Der Server betreibt keinen eigenen
Analyse- oder Telemetriedienst. Automatische Updates kontaktieren PyPI; die
Bereitstellung der Python-Laufzeit kann zusätzliche Downloads durch Claude/UV auslösen.

Developer Token, OAuth Client ID und Client Secret werden als Prozessumgebung
übergeben. Die drei vertraulichen Manifestfelder (Developer Token, Client Secret,
optionaler Refresh Token) sind als `sensitive` markiert. Ihre Speicherung übernimmt
Claude. Daraus folgt keine pauschale Verschlüsselungszusage für alle Zugangsdaten.

Ein über den Browser erzeugter Refresh Token wird zusätzlich lokal unter
`~/.config/flin-google-keyword-planner-mcp/oauth-token.json` atomar mit Rechten
`0600` gespeichert. `FLIN_GOOGLE_ADS_TOKEN_FILE` kann einen anderen Pfad festlegen.
**Diese Datei ist nicht verschlüsselt und liegt nicht im macOS-Schlüsselbund.**
Programme unter demselben Benutzerkonto können sie lesen. Der Server bevorzugt
sein Laufzeit-/Datei-Token vor einem Token aus der Umgebung.

`connection_status` liest nur lokale Konfiguration und Token-Verfügbarkeit. Es gibt
keine Secrets, Konto-IDs oder Token-Dateipfade zurück und überprüft keine Google-
Berechtigungen. Keyword-Ergebnisse können die verwendete Konto-ID enthalten.

## Zugriff widerrufen und lokal bereinigen

1. Den OAuth-Zugriff in den Verbindungen deines Google-Kontos widerrufen.
2. Den MCP-Server stoppen; Refresh Token und übrige Werte aus der Erweiterung bzw.
   manuellen Konfiguration entfernen und die lokale Token-Datei löschen. Bei einem
   abweichenden Token-Pfad auch diesen berücksichtigen.
3. Die Erweiterung bei Bedarf deinstallieren. Deinstallation allein widerruft keine
   Google-Berechtigung und entfernt die separate Token-Datei nicht automatisch.
4. Bei offengelegten Zugangsdaten den zuständigen Administrator um Rotation bzw.
   Widerruf der betroffenen OAuth-/Developer-Zugangsdaten bitten. Chat-/Logverläufe
   und Sicherungskopien unterliegen der jeweiligen Client- und Systemverwaltung.

[Google-Datenschutz](https://policies.google.com/privacy) ·
[Sicherheit](SECURITY.md) · [Support](SUPPORT.md)
