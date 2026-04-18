# Alby Hub Integration – Handbuch (DE)

## Integration vs. Add-on (wichtig)

- **Diese Integration ist erforderlich**, um Alby Hub in Home Assistant einzubinden und Entitäten/Services in HA zu nutzen.
- Das Add-on [`ha-btc-alby-hub-addon`](https://github.com/northpower25/ha-btc-alby-hub-addon/) ist dafür da, Alby Hub lokal als Supervisor-Add-on auf Home Assistant OS bereitzustellen.
- Bei reiner Cloud-/NWC-Nutzung der Integration ist das Add-on nicht zwingend notwendig.
- Für lokale Expert-Funktionen (lokale API/Relay) kann das Add-on erforderlich sein.

## Installation & Konfiguration (Schritt für Schritt)

### Voraussetzungen

1. Laufende Home-Assistant-Instanz.
2. Für HACS-Installation: HACS ist bereits installiert und eingerichtet.
3. Für lokale Alby-Hub-Nutzung auf HA OS optional das Add-on:
   [`ha-btc-alby-hub-addon`](https://github.com/northpower25/ha-btc-alby-hub-addon/).

### Option A: Installation über HACS (empfohlen)

1. Home Assistant öffnen.
2. **HACS → Integrationen** öffnen.
3. Menü (⋮) öffnen und **Custom repositories** wählen.
4. Repository-URL `https://github.com/northpower25/ha-btc-alby-hub-integration` einfügen.
5. Typ **Integration** auswählen und hinzufügen.
6. In HACS nach **Alby Hub** suchen.
7. Integration installieren.
8. Home Assistant neu starten.

### Option B: Manuelle Installation

1. Die aktuelle Integration aus dem Repository herunterladen (ZIP oder Git-Checkout).
2. Den Ordner `custom_components/alby_hub` in dein Home-Assistant-Konfigurationsverzeichnis nach  
   `/config/custom_components/alby_hub` kopieren.
3. Prüfen, dass mindestens folgende Datei vorhanden ist:  
   `/config/custom_components/alby_hub/manifest.json`.
4. Home Assistant neu starten.

### Konfiguration in Home Assistant

1. In Home Assistant zu **Einstellungen → Geräte & Dienste** wechseln.
2. **Integration hinzufügen** klicken.
3. Nach **Alby Hub** suchen und auswählen.
4. Modus wählen:
   - **Cloud-Modus** (NWC-basiert), oder
   - **Expert-Modus** (optional mit lokaler API/Relay).
5. NWC-Verbindungs-URI aus Alby Hub einfügen.
6. Verbindung prüfen und alle Warnungen sorgfältig prüfen, bevor du fortfährst.
7. Konfiguration speichern.
8. Danach Entitäten und Status in Home Assistant prüfen.

## Beta-, Sicherheits- und Haftungshinweis

⚠️ Diese Integration und das zugehörige Add-on befinden sich im Beta-Status. Unter bestimmten Bedingungen können Fehlfunktionen, Fehlkonfigurationen oder externe Störungen zu finanziellen Verlusten führen. Zum Testen nur kleine Beträge verwenden und keine größeren Geldbeträge einsetzen.

Typische Benutzerfehler:

- NWC-URI fehlerhaft einfügen (Schema, Relay, Secret oder Pubkey fehlen)
- Zu viele Rechte/Scopes für den vorgesehenen Zweck freigeben
- Zahlungen ohne ausreichende Limits/Prüfungen automatisieren
- Lokale API/Relay als vertrauenswürdig annehmen, obwohl die Erreichbarkeit instabil ist

Systemische Risiken:

- Beta-Bugs, Edge Cases und unvollständige Fehlerbehandlung
- Netzwerk-, Relay- oder API-Ausfälle
- Zeitverzögerte/inkonsistente Zustände zwischen Home Assistant und Alby Hub
- Sicherheitsrisiken durch unsichere Netzwerkkonfiguration, exponierte Systeme oder kompromittierte Schlüssel/Secrets

Du bist selbst für die verantwortungsvolle Verwendung des Add-ons und der zugehörigen Integration verantwortlich.

## Konfiguration (NWC Scopes)

- In Alby Hub eine NWC-Verbindung mit den benötigten Rechten anlegen.
- NWC-URI in den Config-Flow der Integration einfügen.
- Pflichtrechte für MVP: `get_info`, `get_balance`, `list_transactions`, `make_invoice`.
- Optional: `pay_invoice`.
- Bei Warnungen kann MVP-konform bewusst mit „Mit Warnung fortfahren“ weitergemacht werden.

## Modus-Logik

- **Cloud-Modus:** vollständig über NWC, ohne lokale Hub-API.
- **Expert-Modus:** kombiniert NWC mit optionaler lokaler Hub-API.
- Bei aktiviertem Expert-Flag wird das lokale Relay `ws://<ha-host>:3334` bevorzugt.

## Entitäten

Die Integration stellt aktuell Basis-Entitäten bereit:

- Verbindung (`binary_sensor`)
- Lightning-/On-Chain-Balance (`sensor`)
- Lightning-Adresse, Relay, Hub-Version (`sensor`)

## Services

- `alby_hub.create_invoice` (Expert-Modus, lokale API)
- `alby_hub.send_payment` (Expert-Modus, lokale API)

## Troubleshooting

- URI prüfen (vollständig, korrektes Schema).
- Rechte/Scopes in Alby Hub prüfen.
- Home-Assistant-Logs auf Integrationsfehler prüfen.

## Update-Sicherheit: Was vor jedem Update zu tun ist

Vor **jedem** Update von Integration, Add-on oder Alby-Hub-Umgebung:

1. **Home-Assistant-Backup/Snapshot erstellen** (inkl. Konfiguration).
2. Sicherstellen, dass NWC-Verbindungsdaten (URI/Secret) sicher verfügbar sind oder neu erstellt werden können.
3. Sicherstellen, dass Recovery-Daten des Wallet-/Node-Backends vorliegen (z. B. Seed, Channel-Backups, Zugangsdaten – abhängig vom Setup).
4. Prüfen, ob Automationen mit Zahlungen temporär deaktiviert werden sollten, bis das Update verifiziert ist.

Wichtig: Home Assistant und diese Integration ersetzen **kein** Wallet-/Node-Backup.

## Welche Daten du vor Update/Neuinstallation gesichert haben musst

- Home-Assistant-Backup/Snapshot
- NWC-Verbindungsdaten oder dokumentierter Neuerstellungsprozess
- Alby-Hub-Zugangsdaten/Recovery-Informationen
- Wallet-/Node-Recovery-Daten des tatsächlich guthabenführenden Backends

Ohne diese Daten kann nach fehlgeschlagenem Update oder Neuinstallation der Zugriff auf Funktionen und ggf. auf Funds verloren gehen (siehe Abschnitt „Recovery nach fehlgeschlagenem Update oder Neuinstallation“).

## Wo liegen die Bitcoin-Funds je nach Szenario?

- **Cloud-/NWC-Szenario:** Funds liegen in der Wallet/Node-Umgebung hinter der verwendeten Alby-Hub-/NWC-Verbindung, nicht in Home Assistant.
- **Lokales Add-on-/Expert-Szenario:** Funds liegen in der lokal betriebenen Alby-Hub-/Wallet-/Node-Umgebung bzw. deren angebundenem Backend, nicht in dieser Integration.

Die Integration stellt Steuerung/Anzeige bereit, hält aber keine Funds.

## Recovery nach fehlgeschlagenem Update oder Neuinstallation

1. Home Assistant bzw. Add-on/Umgebung stabil neu herstellen.
2. Gesicherte Konfigurations- und Verbindungsdaten wieder einspielen.
3. Integration neu konfigurieren (NWC/Expert-Einstellungen).
4. Zugriff auf die Wallet/Node-Umgebung über deren eigene Recovery-Prozesse wiederherstellen.
5. Erst danach Zahlungsautomationen wieder aktivieren.

Wenn die Wallet-/Node-Recovery-Daten fehlen, kann der Zugriff auf Funds dauerhaft verloren sein.
