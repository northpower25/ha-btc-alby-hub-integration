# Alby Hub Integration – Developer Handbuch (DE)

## Ziel und Verantwortung

Diese Integration verarbeitet keine Bitcoin-Funds selbst, kann aber über Konfigurationen, Automationen und API-Aufrufe indirekt Zahlungen auslösen. Änderungen müssen daher so entwickelt werden, dass Nutzer vor und nach Updates sicher arbeiten können.

Grundsatz: **Sicherheit zuerst, Guthaben zweitens, Features drittens**.

## Sicherheits- und Qualitätsprinzipien für Weiterentwicklung

- Keine Änderung ohne Betrachtung der Auswirkungen auf bestehende Konfigurationen, Secrets und Automationen.
- Breaking Changes nur mit klarer Migration und klarer Nutzerkommunikation.
- Defaults konservativ halten (kein stilles Aktivieren riskanter Funktionen).
- Berechtigungen/Scopes auf Minimalprinzip auslegen.
- Fehler müssen nachvollziehbar sein (klare Logs, keine irreführenden Erfolgsmeldungen).

## Pflicht bei jeder Änderung mit Nutzerwirkung

Wenn ein Release Konfiguration, Authentifizierung, Scopes, Verbindungsdaten, Services oder Recovery-Prozesse betrifft, muss die Dokumentation zwingend enthalten:

1. **Was sich ändert**
2. **Was der Anwender vor dem Update sichern muss**
3. **Welche Sicherheitsmaßnahmen vor dem Update nötig sind**
4. **Wie Recovery nach fehlgeschlagenem Update funktioniert**
5. **Wo Funds im jeweiligen Szenario liegen**

Diese Informationen müssen in:

- `README.md` (Kurzfassung mit Verweisen)
- `docs/handbook.de.md` (Anwenderdetails)
- Optional zusätzlich EN-Doku bei inhaltlicher Relevanz

## Release-Gate für Updates (verantwortungsvoll entwickeln)

Vor Veröffentlichung prüfen:

- Update-Hinweise enthalten eine konkrete Backup-Checkliste.
- Es ist dokumentiert, welche Daten für Neuinstallation/Wiederherstellung erforderlich sind.
- Es ist dokumentiert, dass Home Assistant und diese Integration **keine Wallet-Backups ersetzen**.
- Es ist dokumentiert, wie Nutzer nach Fehlschlag wieder auf Funds zugreifen (über Alby Hub/Wallet-Backend).
- Risiken automatisierter Zahlungen sind erwähnt (Limits, manuelle Freigaben, Scopes).

## Minimale Backup- und Recovery-Anforderungen für Anwenderkommunikation

Die Nutzerdokumentation muss bei relevanten Updates mindestens auf folgende Daten hinweisen:

- Home-Assistant-Backup/Snapshot (inkl. Integrationskonfiguration)
- NWC-Verbindungsdaten (URI/Secret) bzw. sichere Möglichkeit zur Neuerstellung
- Zugangsdaten/Recovery-Daten des Alby-Hub-Setups und des zugrunde liegenden Wallet-/Node-Backends
- Channel-/Node-/Seed-Backups je nach verwendetem Wallet-Backend

## Funds-Lage transparent machen (Pflichttext in Releases/Doku)

- Funds liegen **nicht** in dieser Integration.
- Funds liegen in der Wallet/Node-Umgebung, mit der Alby Hub verbunden ist (Cloud-Instanz, lokaler Hub, externes Node-/Wallet-Backend).
- Ohne Zugriff auf die Recovery-Daten dieser Wallet/Node-Umgebung kann eine Neuinstallation den Zugriff auf Funds verhindern.

## Change-Management-Empfehlung

- Kleine, nachvollziehbare Änderungen statt großer ungetrennter Umbauten.
- Für riskante Änderungen: erst Dokumentation und Migrationshinweise, dann Code-Release.
- Bei unklaren Recovery-Folgen: Release zurückstellen, bis die Wiederherstellung dokumentiert und testbar ist.
