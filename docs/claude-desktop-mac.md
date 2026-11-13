# Claude Desktop auf macOS installieren

1. Lade das [Desktop-Paket](https://github.com/flin-agency/flin-google-keyword-planner-mcp/releases/latest/download/flin-google-keyword-planner-mcp.mcpb) herunter.
   Empfohlener Einstieg: Apple Silicon (M1 oder neuer). Versionierte Downloads bleiben verfügbar.
2. Aktualisiere Claude Desktop. Öffne **Settings → Desktop app → Extensions →
   Manage → Advanced settings → Install Extension…**. In älteren Oberflächen
   findest du den Bereich direkt unter **Settings → Extensions**.
3. Wähle die `.mcpb`-Datei aus und bestätige die Installation.
4. Trage die Werte vom zuständigen Administrator/Passwortmanager ein: OAuth Client ID, OAuth Client Secret und Google Ads
   Customer ID ein. Bei einem Managerkonto zusätzlich die Login Customer ID.
   Die Anmeldung erfolgt anschliessend im Browser; alte Tokens werden nicht übernommen.
5. Bitte Claude: «Starte `google_ads_start_local_oauth_flow` für Google Ads.»
   Öffne den ausgegebenen Google-Link, melde dich an und genehmige den Zugriff.
   Danach zeigt `connection_status` die lokale Einrichtung und laufende Serverversion.
   `google_ads_oauth_status` bleibt als bisheriger OAuth-Status erhalten; keines
   dieser Tools bestätigt die aktuellen Google-Ads-Kontoberechtigungen.

Empfohlen ist ein Google Cloud OAuth-Client vom Typ **Desktop app**. Bei einem
Web-Client muss die verwendete Redirect URI (standardmässig
`http://localhost:8080/`) exakt hinterlegt sein. Ein freier lokaler Port ist nötig.
Falls Port 8080 belegt ist, kann ein Desktop-Client
`redirect_uri="http://127.0.0.1:0/"` verwenden; der Server wählt dann einen freien Port.

## Umstieg von 0.3

Das neue 0.4-Paket einmal importieren und den Browser-Login erneut durchführen.
Alte Token-Dateien und importierte Refresh Tokens werden nicht übernommen.
Neue Anmeldungen bleiben anschliessend über Neustarts erhalten.
Das Desktop-Paket funktioniert erst nach Veröffentlichung von 0.4.0 auf PyPI.

## Voraussetzungen

- Aktuelles Claude Desktop für macOS mit MCPB-0.4-/UV-Runtime-Unterstützung;
  gegebenenfalls müssen Unternehmensrichtlinien eigene Erweiterungen erlauben.
- Internet bei jedem Serverstart: Claude/UV stellt Python 3.13 bereit. Der Starter
  lädt die neueste stabile Version im Bereich `>=0.4.0,<0.5.0` von PyPI.
  Das Paket enthält keine native
  Mac-Binärdatei und verwendet passende Abhängigkeiten für Apple Silicon bzw. Intel.
- OAuth-Client aus einem Google-Cloud-Projekt mit Basic- oder Standardzugriff
  auf die Google Ads API sowie Zugriff auf das Ads-Konto.
  Einschränkungen oder Freigaben seitens Google gelten weiterhin.

## Sicherheit und Daten

- Das Client Secret ist als sensible Einstellung markiert.
  Seine Speicherung übernimmt Claude; dies ist keine
  pauschale Verschlüsselungszusage. Gib sie in den Einstellungen ein, nicht im Chat.
- Bei der Browser-Anmeldung speichert der Server den Refresh Token separat unter
  `~/.config/flin-google-keyword-planner-mcp/oauth-token.json`, atomar und mit
  Dateirechten `0600`. Diese Datei ist **nicht verschlüsselt**; Programme unter
  deinem Benutzerkonto können sie lesen. Sie bleibt nach der Deinstallation
  erhalten und kann zum Abmelden gelöscht werden; Google-Zugriff zusätzlich im
  Google-Konto widerrufen.
- Die Keyword-Tools lesen Daten von Google Ads. Sie verändern keine Kampagnen.
  Googles OAuth-Scope `adwords` ist dennoch weiter gefasst als diese Lesefunktionen.
- Keyword- und URL-Anfragen gehen an Google, Ergebnisse an den MCP-Client.
  Es gibt keinen eigenen Telemetriedienst. Der Callback lauscht nur lokal und
  endet nach Abschluss oder spätestens nach zehn Minuten.
- Das Paket ist eine eigene, nicht von Anthropic geprüfte oder signierte
  Erweiterung. Eine SHA-256-Prüfsumme liegt beim Release. Sie erkennt Änderungen
  gegenüber dem Release-Download, ersetzt aber keine Herausgebersignatur.

## Erster Test

«Prüfe historische Suchvolumen für `Wandern Schweiz` und `Wandern Zürich`,
Sprache Deutsch (`1001`), Schweiz (`2756`), nur Google Search.»

Ab Server 0.3.4 sind Deutsch (`1001`) und Schweiz (`2756`) voreingestellt.
Für andere Märkte Sprache und Region ausdrücklich setzen. Wettbewerb meint Anzeigenwettbewerb,
nicht organische SEO-Schwierigkeit.

## Updates und Fehler

**Normale Serverupdates werden weiterhin automatisch von PyPI übernommen.**
Ab Starter 0.4.0 gilt die ausdrücklich geprüfte 0.4-Schnittstelle: `>=0.4.0,<0.5.0`.
Die ausdrückliche Cache-Aktualisierung wählt bei jedem Start die neueste stabile
Version innerhalb dieser Grenze. Vorabversionen werden ausgeschlossen. Der Test
prüft sowohl neue Patch-Releases als auch den Ausschluss von 0.5 und 1.0.
Die Erweiterungsversion in Claude bezeichnet den Starter; `connection_status`
zeigt dagegen die tatsächlich laufende Serverversion.
Die mitgelieferten Quellen und `uv.lock` sind ein Referenzstand für Entwicklung und
Prüfung; der Starter führt ausschliesslich das aktuelle PyPI-Paket aus.

Ein bereits laufender Server wird nicht während einer Anfrage ausgetauscht. Nach
Veröffentlichung eines Updates genügt ein Serverneustart oder das vollständige
Beenden und erneute Öffnen von Claude. Ohne erreichbaren Paketindex kann der Start
fehlschlagen; es gibt keinen stillen Rückfall auf eine alte Version.

**Einmalige Umstellung:** Wer einen 0.3-Starter verwendet, muss das neue
`.mcpb` importieren und sich neu anmelden. Die Erweiterungs-ID und der Token-Pfad
bleiben gleich; die alten Token-Eingabefelder entfallen. Nur eine erfolgreiche
neue Anmeldung ersetzt die alte Token-Datei.
Danach benötigen normale PyPI-Serverupdates keine neue `.mcpb`-Installation.
Änderungen am Starter selbst, an Pflichtfeldern oder an der unterstützten Python-
Laufzeit können weiterhin eine neue Erweiterung erfordern.

Automatische Updates führen künftig veröffentlichten Code dieses PyPI-Projekts
und dessen Abhängigkeiten aus. Die Prüfsumme der `.mcpb` gilt für den Starter und
den enthaltenen Referenzstand, nicht für alle zukünftigen PyPI-Versionen.
Bei fehlenden Tools Claude neu starten und die Pflichtfelder prüfen. Wenn Claude
den Servertyp `uv` nicht erkennt, Claude aktualisieren; die manuelle
[uvx-Konfiguration im README](../README.md#claude-integration) bleibt verfügbar.

[Offizielle Installationshilfe](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop)
und [MCPB-Spezifikation](https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md).

[UV-Dokumentation](https://docs.astral.sh/uv/reference/cli/#uv-tool-run) ·
[Manueller Fallback bei PyPI-Störungen](../SUPPORT.md#pypi-vorübergehend-nicht-erreichbar) ·
[Datenschutz und lokale Bereinigung](../PRIVACY.md).
