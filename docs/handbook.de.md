# Alby Hub Integration – Handbuch (DE)

## Integration vs. Add-on (wichtig)

- **Diese Integration ist erforderlich**, um Alby Hub in Home Assistant einzubinden und Entitäten/Services in HA zu nutzen.
- Das Add-on [`ha-btc-alby-hub-addon`](https://github.com/northpower25/ha-btc-alby-hub-addon/) ist dafür da, Alby Hub lokal als Supervisor-Add-on auf Home Assistant OS bereitzustellen.
- Bei reiner Cloud-/NWC-Nutzung der Integration ist das Add-on nicht zwingend notwendig.
- Für lokale Expert-Funktionen (lokale API/Relay) kann das Add-on erforderlich sein.

## Abgleich mit offiziellen Alby-Hub-Guides

Offizielle Quellen:

- Hub Übersicht: https://guides.getalby.com/user-guide/alby-hub
- Getting Started: https://guides.getalby.com/user-guide/alby-hub/getting-started
- Flavors: https://guides.getalby.com/user-guide/alby-hub/alby-hub-flavors

Die offiziellen Alby-Hub-Flavors beschreiben, **wo** dein Hub läuft:
Alby Cloud, Desktop, Docker, Umbrel/Start9/etc., Linux.

Einordnung für diese Integration:

| Szenario | Bedeutung für die Integration |
|---|---|
| Externer Hub (Alby Cloud/Desktop/Docker/Linux/Umbrel/Start9/etc.) | Integration verbindet sich per NWC-URI direkt mit dem vorhandenen Hub |
| Hub lokal im HA Add-on (Expert-Modus) | Integration verbindet sich per NWC und kann optional lokale Expert-Funktionen nutzen |

Hinweis aus Alby-Sicht: Ein Alby Account ist häufig empfehlenswert (z. B. Lightning Address, einfachere App-Verknüpfung, Benachrichtigungen/Support), aber je nach Setup nicht technisch zwingend.

## Was laut Alby-Getting-Started vor der Integration erledigt sein sollte

1. Gewünschten Alby-Hub-Flavor auswählen und Hub initial bereitstellen.
2. Ersteinrichtung im Hub abschließen (z. B. Account-Linking, Channel/Spending-Balance, Backup-/Recovery-Daten je nach Setup).
3. In Alby Hub unter **Apps → Add Connection** eine eigene NWC-Verbindung für Home Assistant anlegen.
4. Nur benötigte Scopes vergeben (Least Privilege).
5. NWC-Secret sicher speichern und bei Verdacht auf Kompromittierung erneuern.

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

Aktuelle Entitäten:

### Sensoren

- Verbindung (`binary_sensor`) – Node-Online-Status
- Lightning-Balance / On-Chain-Balance (`sensor`) – in Satoshi
- Lightning-Adresse, NWC-Relay, Hub-Version (`sensor`)
- **Bitcoin-Preis** (`sensor`) – in der konfigurierten Währung (z. B. EUR, USD)
- **Bitcoin-Blockhöhe** (`sensor`)
- **Bitcoin-Hashrate** (`sensor`) – in EH/s
- **Blöcke bis Halving** (`sensor`)
- **Nächstes Halving (Schätzung)** (`sensor`) – Zeitstempel

### Text-Entitäten (Zahlungsworkflow)

- **`text.alby_hub_invoice_input`** – BOLT11-Rechnung hier einfügen oder per QR-Scan befüllen, bevor gesendet wird
- **`text.alby_hub_last_invoice`** – zeigt die zuletzt erstellte Rechnung (BOLT11-String)

## Services

- `alby_hub.create_invoice` (Expert-Modus, lokale API)
  - Betrag kann in **Satoshi** (`amount_sat`), **BTC** (`amount_btc`) oder **Fiat** angegeben werden
    (`amount_fiat` + `fiat_currency` – verwendet den Bitcoin-Preis-Sensor für die Umrechnung).
  - Die erzeugte Rechnung wird automatisch in `text.alby_hub_last_invoice` gespeichert.
  - Antwort enthält `payment_request`, `amount_sat` und `qr_url`.
- `alby_hub.send_payment` (Expert-Modus, lokale API)
  - `payment_request` ist optional: wenn nicht angegeben, wird `text.alby_hub_invoice_input` verwendet.
  - Nach erfolgreicher Zahlung wird `text.alby_hub_invoice_input` automatisch geleert.

## Lightning empfangen

1. Service `alby_hub.create_invoice` mit gewünschtem Betrag (Satoshi / BTC / Fiat) aufrufen.
2. Die BOLT11-Rechnung wird in `text.alby_hub_last_invoice` gespeichert.
3. Alby-Hub-Dashboard → View „Empfangen" öffnen: zeigt den Invoice-Text und einen QR-Code-Link.
4. Rechnungs-String teilen oder den QR-Code vom Zahler scannen lassen.

Alternativ: Lightning-Adresse (`sensor.alby_hub_lightning_address`) direkt teilen – kein Invoice-Erstellen nötig.

## Lightning senden

1. BOLT11-Rechnung vom Zahlungsempfänger erhalten (per QR-Code oder Kopieren).
2. In `text.alby_hub_invoice_input` einfügen (Alby-Hub-Dashboard → View „Senden"),
   oder QR-Code mit der Home-Assistant-Companion-App (Android/iOS) scannen – der gescannte Wert
   wird über die App direkt in die Text-Entität geschrieben.
3. Service `alby_hub.send_payment` aufrufen (ohne Parameter, wenn die Entität befüllt ist).

## Sprache / Anzeigesprache

Home Assistant zeigt alle Entitäten und den Config-Flow automatisch in der Sprache an, die unter
**Profil → Sprache** in Home Assistant eingestellt ist. Kein zusätzliches Setup erforderlich.
Verfügbare Übersetzungen: Englisch (`en`), Deutsch (`de`).

## Dashboard

Nach der Einrichtung wird automatisch ein **Alby Hub**-Dashboard mit drei Views erstellt:

- **Empfangen** – Lightning-Adresse, letzter Invoice mit QR-Code-Link, Balance
- **Senden** – Invoice-Eingabefeld, Anleitung (Companion App QR / Einfügen), Sende-Button
- **Netzwerk** – Bitcoin-Preis, Blockhöhe, Hashrate, Halving-Countdown

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
