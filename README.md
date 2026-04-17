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
- NWC-URI- und Scope-Prüfung inklusive „Continue with warning“-Verhalten
- Expert-Modus: optionaler lokaler API-Health-Check und Relay-Priorisierung (`ws://<host>:3334`)
- Basis-Entitäten für Verbindung, Balances und Metadaten
- Basis-Services für Invoice-Erstellung und Payment (lokale API, Expert-Modus)

## Installation (HACS)

1. HACS installieren und einrichten.
2. Dieses Repository in HACS als Custom Repository vom Typ **Integration** hinzufügen.
3. Integration **Alby Hub** installieren.
4. Home Assistant neu starten.
5. Integration über **Einstellungen → Geräte & Dienste → Integration hinzufügen** konfigurieren.

## NWC Quickstart

1. In Alby Hub eine NWC-Verbindung erstellen.
2. Verbindungs-URI kopieren.
3. In Home Assistant beim Einrichten der Integration einfügen.
4. Verbindung testen und speichern.

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

## Kompatibilität

| Komponente | Version |
|---|---|
| Home Assistant | 2026.1+ |
| HACS | Aktuelle stabile Version |

## Zugehöriges Add-on-Repository

- [`ha-btc-alby-hub-addon`](https://github.com/northpower25/ha-btc-alby-hub-addon) – Supervisor Add-on für Home Assistant OS

## Dokumentation

- Deutsch: [`docs/handbook.de.md`](docs/handbook.de.md)
- English: [`docs/handbook.en.md`](docs/handbook.en.md)
