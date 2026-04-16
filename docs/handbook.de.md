# Alby Hub Integration – Handbuch (DE)

## Installation

1. HACS öffnen.
2. Repository `northpower25/ha-btc-alby-hub-integration` als Custom Integration hinzufügen.
3. Integration installieren und Home Assistant neu starten.

## Konfiguration (NWC Scopes)

- In Alby Hub eine NWC-Verbindung mit den benötigten Rechten anlegen.
- NWC-URI in den Config-Flow der Integration einfügen.
- Nur die tatsächlich benötigten Scopes freigeben.

## Entitäten

Die Integration stellt Alby-Hub-bezogene Entitäten bereit (abhängig von den freigegebenen Rechten und verfügbaren Daten im Hub).

## Services

Service-Aufrufe basieren auf den freigegebenen NWC-Funktionen. Fehlende Rechte führen zu abgelehnten Aktionen.

## Troubleshooting

- URI prüfen (vollständig, korrektes Schema).
- Rechte/Scopes in Alby Hub prüfen.
- Home-Assistant-Logs auf Integrationsfehler prüfen.
