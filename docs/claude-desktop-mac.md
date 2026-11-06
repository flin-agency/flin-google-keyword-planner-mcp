# Claude Desktop auf macOS installieren

1. Lade `flin-google-keyword-planner-mcp-0.3.2-mac.mcpb` aus dem
   [GitHub-Release v0.3.2](https://github.com/flin-agency/flin-google-keyword-planner-mcp/releases/tag/v0.3.2).
2. Aktualisiere Claude Desktop. Öffne **Settings → Desktop app → Extensions →
   Manage → Advanced settings → Install Extension…**. In älteren Oberflächen
   findest du den Bereich direkt unter **Settings → Extensions**.
3. Wähle die `.mcpb`-Datei aus und bestätige die Installation.
4. Trage Developer Token, OAuth Client ID, OAuth Client Secret und Google Ads
   Customer ID ein. Bei einem Managerkonto zusätzlich die Login Customer ID.
   Ein vorhandener Refresh Token ist optional.
5. Bitte Claude: «Starte `google_ads_start_local_oauth_flow` für Google Ads.»
   Öffne den ausgegebenen Google-Link, melde dich an und genehmige den Zugriff.
   Danach kann Claude mit `google_ads_oauth_status` die Verbindung prüfen.

Empfohlen ist ein Google Cloud OAuth-Client vom Typ **Desktop app**. Bei einem
Web-Client muss die verwendete Redirect URI (standardmässig
`http://localhost:8080/`) exakt hinterlegt sein. Ein freier lokaler Port ist nötig.
Falls Port 8080 belegt ist, kann ein Desktop-Client
`redirect_uri="http://127.0.0.1:0/"` verwenden; der Server wählt dann einen freien Port.

## Voraussetzungen

- Aktuelles Claude Desktop für macOS mit MCPB-0.4-/UV-Runtime-Unterstützung;
  gegebenenfalls müssen Unternehmensrichtlinien eigene Erweiterungen erlauben.
- Internet bei jedem Serverstart: Claude/UV stellt Python 3.13 bereit. Der Starter
  lädt die neueste stabile, mit dieser Laufzeit kompatible Version von PyPI. Das Paket enthält keine native
  Mac-Binärdatei und verwendet passende Abhängigkeiten für Apple Silicon bzw. Intel.
- Google Ads API Developer Token, OAuth-Client und Zugriff auf das Ads-Konto.
  Einschränkungen oder Freigaben seitens Google gelten weiterhin.

## Sicherheit und Daten

- Developer Token, Client Secret und optionaler Refresh Token sind als sensible
  Einstellungen markiert. Claude verwaltet diese über den sicheren Speicher des
  Betriebssystems. Gib sie in den Einstellungen ein, nicht im Chat.
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

Die Standardwerte des Servers sind Englisch und USA; Schweizer Auswertungen
müssen das Zielgebiet ausdrücklich setzen. Wettbewerb meint Anzeigenwettbewerb,
nicht organische SEO-Schwierigkeit.

## Updates und Fehler

**Ab Starter-Version 0.3.2 werden Serverupdates automatisch von PyPI übernommen.**
Bei jedem Start wird mit `@latest` und Cache-Aktualisierung neu geprüft; eine lokal
installierte ältere Version wird nicht bevorzugt. Vorabversionen werden ausgeschlossen.
Die mitgelieferten Quellen und `uv.lock` sind ein Referenzstand für Entwicklung und
Prüfung; der Starter führt ausschliesslich das aktuelle PyPI-Paket aus.

Ein bereits laufender Server wird nicht während einer Anfrage ausgetauscht. Nach
Veröffentlichung eines Updates genügt ein Serverneustart oder das vollständige
Beenden und erneute Öffnen von Claude. Ohne erreichbaren Paketindex kann der Start
fehlschlagen; es gibt keinen stillen Rückfall auf eine alte Version.

**Einmalige Umstellung:** Wer 0.3.1 installiert hat, muss das neue `.mcpb` einmal
installieren. Die alte Installation kann diese Änderung nicht selbst übernehmen.
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

[UV-Dokumentation zur Aktualisierung mit `@latest`](https://docs.astral.sh/uv/concepts/tools/#tool-versions).
