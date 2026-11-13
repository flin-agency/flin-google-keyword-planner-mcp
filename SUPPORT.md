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

Fehlende Daten (`null`) sind nicht null Suchanfragen. Ab Server 0.3.4 sind die Standardwerte Deutsch,
Schweiz und Search mit Partnern. Für andere Märkte Sprache und Region ausdrücklich setzen.
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
"args": ["tool", "run", "--offline", "--from", "flin-google-keyword-planner-mcp==0.4.0", "flin-google-keyword-planner-mcp"]
```

Die vorhandenen Credential-Felder beibehalten. Das funktioniert nur, wenn diese
Version, Python und sämtliche Abhängigkeiten bereits vollständig im UV-Cache liegen;
es kann sonst ebenfalls fehlschlagen. Dieser Modus aktualisiert **nicht** automatisch
und muss sichtbar als manueller Fallback behandelt werden. Mit `connection_status`
die gewählte Serverversion prüfen und nach der Störung zur normalen Erweiterung
zurückkehren. Google-Abfragen brauchen weiterhin Zugriff auf Google.

## OAuth-Diagnose ab 0.3.6

1. Claude vollständig beenden und neu öffnen. In `connection_status` muss
   `server_version` mindestens `0.3.6` sein.
2. `google_ads_start_local_oauth_flow` aufrufen. Falls das Tool bereits einen Fehler
   meldet, dessen `error.code`, `error.stage` und `error.message` verwenden; es gibt
   dann keinen neuen Anmeldelink. Ein älterer OAuth-Status kann weiterhin vorhanden sein.
3. Andernfalls den neuen Link öffnen, bei Google anmelden und danach
   `google_ads_oauth_status` aufrufen. Bei einem Fehler `error_code`, `error_stage`
   und `error` weitergeben. Dieselbe bereinigte Meldung erscheint im Browser.

| Diagnose | Bedeutung / nächster Schritt |
| --- | --- |
| `TOKEN_STORAGE_PERMISSION` | Schreiben verweigert: Eigentümer, Ordnerrechte und App-/Firmenrichtlinien prüfen. |
| `TOKEN_STORAGE_FULL` | Speicherplatz oder Benutzerkontingent erschöpft. |
| `TOKEN_STORAGE_READ_ONLY` | Speicherort liegt auf einem schreibgeschützten Dateisystem. |
| `TOKEN_STORAGE_PATH` | Ungültiger Pfad oder Konflikt mit einer Datei/einem Ordner. |
| `TOKEN_STORAGE_IO` | Sonstiger Dateisystemfehler. |
| `TLS_CERTIFICATE_ERROR` | Zertifikatsprüfung fehlgeschlagen: Uhrzeit, Zertifikate und Firmenproxy prüfen. TLS-Prüfung nicht abschalten. |
| `TLS_ERROR` | Andere Störung beim Aufbau der verschlüsselten Verbindung. |
| `NETWORK_DNS` | Namensauflösung fehlgeschlagen. |
| `NETWORK_TIMEOUT` | Zeitüberschreitung beim Google-Aufruf. |
| `NETWORK_REFUSED` / `NETWORK_RESET` / `NETWORK_ERROR` | Verbindung abgelehnt, zurückgesetzt oder anderweitig fehlgeschlagen; Netzwerk, Proxy und Firewall prüfen. |
| `CALLBACK_PORT_IN_USE` | Lokaler Port belegt; andere Anmeldung schliessen oder bei einem Desktop-OAuth-Client `http://127.0.0.1:0/` verwenden. |
| `CALLBACK_PERMISSION` / `CALLBACK_LISTENER_ERROR` | Lokaler Listener darf nicht starten oder Adresse/Port sind nicht verfügbar. |
| `GOOGLE_INVALID_CLIENT` / `GOOGLE_INVALID_GRANT` | Google lehnt Client oder Code ab; die Meldung nennt die passenden Prüfschritte. |
| `GOOGLE_HTTP_ERROR` / `GOOGLE_TOKEN_ERROR` | Google meldet einen sonstigen HTTP-/Tokenfehler. Bei HTTP-Antworten wird der Status mitgeteilt. |
| `REFRESH_TOKEN_MISSING` / `TOKEN_RESPONSE_INVALID` | Kein Refresh Token oder unerwartete Antwort. |
| `GOOGLE_AUTHORIZATION_DENIED` / `CALLBACK_CODE_MISSING` | Zustimmung fehlgeschlagen/abgelehnt oder kein Code im Callback. |
| `OAUTH_EXPIRED` | Anmeldung nach zehn Minuten abgelaufen. |
| `OAUTH_INTERNAL_ERROR` | Nicht klassifizierter Fehler; Serverversion, Diagnosecode und Phase melden. |

`storage_check` ist die Prüfung vor dem Google-Code-Austausch, `token_exchange`
der Austausch und `token_save` das Speichern nach erfolgreichem Austausch.
Weitere Phasen sind `callback_start`, `authorization` und `callback`.
Rohmeldungen von Bibliotheken, private Pfade, Codes, Tokens und Secrets werden
nicht ausgegeben. `token_available=true` kann sich auf einen älteren Token beziehen
und bedeutet nicht, dass der aktuelle Anmeldeversuch erfolgreich war.

## Fehler melden

[GitHub-Issue erstellen](https://github.com/flin-agency/flin-google-keyword-planner-mcp/issues).
Hilfreich sind macOS-/Claude-Version, Erweiterungsversion, `server_version`, die fünf
Felder aus `connection_status` und eine bereinigte Fehlermeldung. Keine Zugangsdaten,
OAuth-URLs mit Codes, Konto-/Kundendaten oder vollständige private Logs veröffentlichen.
Sicherheitsmeldungen gehören in einen privaten Kanal: [SECURITY.md](SECURITY.md).
