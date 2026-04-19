# ha-btc-alby-hub-integration

[![HACS Default](https://img.shields.io/badge/HACS-Default-blue.svg)](https://hacs.xyz/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.1+-41BDF5.svg)](https://www.home-assistant.io/)

Home Assistant Custom Integration für **Alby Hub** (Bitcoin Lightning).

Diese Integration ist für alle Home-Assistant-Installationsarten gedacht (HA OS, Container, Core), insbesondere dort, wo das Supervisor-Add-on nicht genutzt werden kann.

> ⚠️ **Beta-Warnung:** Diese Integration und das zugehörige Add-on sind Beta-Software. Unter bestimmten Bedingungen können Fehlfunktionen, Fehlkonfigurationen oder externe Störungen zu finanziellen Verlusten führen. Nutze zum Testen nur kleine Beträge und **keine größeren Geldbeträge**. Du bist selbst für die verantwortungsvolle und sichere Nutzung verantwortlich.

## Wofür ist was gedacht?

- **Diese Integration (`ha-btc-alby-hub-integration`) ist erforderlich**, damit Home Assistant mit Alby Hub verbunden wird und Entitäten/Services in Home Assistant bereitstellt (z. B. Balance, Verbindungsstatus, Rechnungen).
- Das **Add-on (`ha-btc-alby-hub-addon`)** ist dafür gedacht, Alby Hub lokal als Supervisor-Add-on auf **Home Assistant OS** zu betreiben.
- Für reine **Cloud-/NWC-Nutzung** der Integration ist das Add-on **nicht zwingend erforderlich**.
- Für lokale Expert-Funktionen (lokale API/Relay) kann das Add-on sinnvoll bzw. erforderlich sein.

## Status

MVP-Implementierung mit:

- Config-Flow für Cloud- und Expert-Modus
- NWC-Eingabefeld als geschütztes Passwortfeld
- Auswahl von Bitcoin-Preis-/Netzwerk-Datenanbietern im Config-Flow
- NWC-URI- und Scope-Prüfung inklusive „Continue with warning“-Verhalten
- Expert-Modus: optionaler lokaler API-Health-Check und Relay-Priorisierung (`ws://<host>:3334`)
- Basis-Entitäten für Verbindung, Balances, Bitcoin-Preis und Netzwerkdaten
- Basis-Services für Invoice-Erstellung und Payment (lokale API, Expert-Modus)
- Automatische Erstellung eines Alby-Hub-Dashboards mit vorgeschlagenen Karten für Empfang/Senden und Markt-/Netzwerkdaten

## Installation (HACS) – Kurzanleitung

1. HACS installieren und einrichten.
2. Dieses Repository in HACS als Custom Repository vom Typ **Integration** hinzufügen.
3. Integration **Alby Hub** installieren.
4. Home Assistant neu starten.
5. Integration über **Einstellungen → Geräte & Dienste → Integration hinzufügen** konfigurieren.

Für eine ausführliche Schritt-für-Schritt Anleitung (inkl. **HACS**, **manueller Installation** und **Konfiguration**) siehe:

- Deutsch: [`docs/handbook.de.md`](docs/handbook.de.md)
- English: [`docs/handbook.en.md`](docs/handbook.en.md)

Wenn du Alby Hub lokal als Supervisor Add-on auf Home Assistant OS betreiben möchtest, nutze zusätzlich das Add-on:

- [`ha-btc-alby-hub-addon`](https://github.com/northpower25/ha-btc-alby-hub-addon)

## NWC Quickstart

1. In Alby Hub eine NWC-Verbindung erstellen.
2. Verbindungs-URI kopieren.
3. In Home Assistant beim Einrichten der Integration einfügen.
4. Verbindung testen und speichern.

## Abgleich mit offiziellen Alby-Hub-Guides (relevant für diese Integration)

Offizielle Alby-Dokumentation:

- Hub Übersicht: https://guides.getalby.com/user-guide/alby-hub
- Getting Started: https://guides.getalby.com/user-guide/alby-hub/getting-started
- Flavors: https://guides.getalby.com/user-guide/alby-hub/alby-hub-flavors

Für diese Integration wichtig:

- Die Integration kann mit allen offiziellen Alby-Hub-Flavors genutzt werden (Alby Cloud, Desktop, Docker, Umbrel/Start9/etc., Linux), sofern eine passende NWC-Verbindung vorliegt.
- Auf Home Assistant OS/Supervised kann zusätzlich das Add-on genutzt werden, um Alby Hub lokal im HA-Umfeld zu betreiben.
- Ohne Add-on nutzt die Integration einen extern betriebenen Hub (z. B. Alby Cloud oder eigener Docker-/Linux-Host) via NWC.
- Ein Alby Account ist für viele Nutzer empfehlenswert (z. B. Lightning Address, einfachere App-Verknüpfung, Benachrichtigungen/Support), aber nicht in jedem Setup zwingend.

## Alby-Getting-Started: Was vor der Integration abgeschlossen sein sollte

1. Alby Hub-Grundeinrichtung abschließen (gewählten Flavor bereitstellen).
2. Bei selbst gehosteten Setups initiale Hub-Tasks erledigen (Channel/Spending-Balance/Backup-Recovery-Daten je nach Setup).
3. In Alby Hub unter **Apps → Add Connection** eine dedizierte NWC-Verbindung für Home Assistant anlegen.
4. Nur die benötigten Rechte/Scopes freigeben (Least Privilege).
5. NWC-Secret wie ein Passwort behandeln (nicht teilen, bei Verdacht rotieren).

## Risiken und Eigenverantwortung

Typische Benutzerfehler:

- Falscher oder unvollständiger NWC-URI
- Zu weitreichende Scopes/Berechtigungen in Alby Hub
- Testen mit zu hohen Beträgen
- Unbeabsichtigte Zahlungen durch fehlerhafte Automationen

Systemische Risiken:

- Beta-bedingte Bugs oder unerwartetes Verhalten
- Netzwerk-/Relay-/API-Ausfälle oder inkonsistente Zustände
- Verzögerte oder fehlgeschlagene Statusaktualisierungen in Home Assistant

Bitte prüfe jede Konfiguration sorgfältig und setze Betragsgrenzen. Die Verantwortung für die Nutzung des Add-ons und der Integration liegt beim Benutzer.

## Update-Sicherheit (wichtig)

Vor jedem Update sicherstellen:

- Home-Assistant-Backup/Snapshot vorhanden
- NWC-Verbindungsdaten (URI/Secret) oder ein sicherer Neuerstellungsprozess vorhanden
- Wallet-/Node-Recovery-Daten (z. B. Seed/Channel-Backups/Zugangsdaten je nach Setup) verfügbar

Diese Integration speichert keine Bitcoin-Funds. Funds liegen in der Alby-Hub-/Wallet-/Node-Umgebung des jeweiligen Setups.

## Kompatibilität

| Komponente | Version |
|---|---|
| Home Assistant | 2026.1+ |
| HACS | Aktuelle stabile Version |

## Zugehöriges Add-on-Repository

- [`ha-btc-alby-hub-addon`](https://github.com/northpower25/ha-btc-alby-hub-addon) – Supervisor Add-on für Home Assistant OS

## Dokumentation

- Deutsch: [`docs/handbook.de.md`](docs/handbook.de.md)
- Entwicklerhandbuch (DE): [`docs/developer-handbook.de.md`](docs/developer-handbook.de.md)
- English: [`docs/handbook.en.md`](docs/handbook.en.md)
