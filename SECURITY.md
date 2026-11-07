# Sicherheit

Die sechs Keyword-Tools lesen Google Ads. Sie ändern keine Kampagnen. Der benötigte
OAuth-Scope `adwords` ist dennoch weiter gefasst als die angebotenen Lesefunktionen.
Der lokale Login verwendet Loopback-HTTP, PKCE, zufälligen State, einmalige
Callback-Verarbeitung und Ablauf nach zehn Minuten. Der manuelle Code-Austausch
bleibt verfügbar, hat aber nicht alle Schutzmassnahmen des empfohlenen lokalen Logins.

Der Server läuft über stdio. Der Statusaufruf startet keinen Browser, schreibt keine
Datei und führt keine Google-Abfrage aus. Tokens erscheinen nicht in seinen
Ergebnissen; ein vorhandenes Token beweist weder Gültigkeit noch Kontozugriff.
Zur Dateispeicherung und Löschung siehe [PRIVACY.md](PRIVACY.md).

## Updates und Prüfumfang

Starter ab 0.3.3 erlauben stabile Serverversionen `>=0.3.2,<0.4.0` mit Python 3.13.
Diese Grenze bezieht sich auf den unveränderten Programmeinstieg, die bestehenden
Credential-Felder, Token-Speicherung und die zehn bisherigen Tool-Eingabeschemas.
Regressionstests vergleichen diese Schemas. Die gezielte Ausnahme ab Server 0.3.4
ist die gewünschte Änderung der Standardausrichtung auf Deutsch/Schweiz. Abfragen
ohne Sprache und Region verwenden damit einen anderen Markt; explizite Zielwerte
bleiben wirksam. Tests prüfen beide Fälle sowie die Keyword-Ergebnisse.
Ein nächster Minor-Release erfordert eine neue Kompatibilitätsprüfung.
Die Grenze ist keine Garantie für beliebigen zukünftigen Code: Updates vertrauen
dem PyPI-Projekt und dessen Abhängigkeiten. Vorabversionen sind ausgeschlossen.

CI prüft Quellcode, Secrets, gesperrte Entwicklungsabhängigkeiten, Paketbau und
Manifest. Die Release-Pipeline startet das Paket ausserhalb des Quellverzeichnisses
auf einem als `arm64` überprüften Mac und kontrolliert nach der Veröffentlichung
die tatsächlich laufende PyPI-Version. Linux-Tests sind davon getrennt. Diese
Prüfungen ersetzen weder einen echten Google-Kontotest noch eine Installation über
Claudes Oberfläche. Ein Scan ohne Befund ist keine Garantie vollständiger Sicherheit.

Das `.mcpb` ist nicht signiert oder von Anthropic geprüft. SHA-256-Dateien bestätigen
die Download-Integrität gegenüber dem Release; sie decken keine späteren PyPI-
Updates ab. Die mitgelieferte Lockdatei ist ein Entwicklungs-/Prüfstand und wird
beim dynamischen Serverstart nicht als feste Versionsbindung verwendet.

## Sicherheitsproblem melden

Keine Secrets, Tokens oder Kundendaten in öffentliche Issues kopieren. Wenn GitHub
unter **Security → Advisories → Report a vulnerability** eine private Meldung
anbietet, diese nutzen. Andernfalls zunächst einen Maintainer über dessen öffentlich
angegebenen Kontaktweg um einen privaten Kanal bitten; sensible Details nicht
öffentlich veröffentlichen. Für nicht vertrauliche Fehler siehe [SUPPORT.md](SUPPORT.md).

Bisherige Berichte: [Audit 30.10.2026](docs/audit-2026-10-30.md),
[Review 06.11.2026](docs/audit-2026-11-06.md).
