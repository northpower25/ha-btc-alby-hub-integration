# Alby Hub Integration – Handbuch (DE)

## Integration vs. Add-on (wichtig)

- **Diese Integration ist erforderlich**, um Alby Hub in Home Assistant einzubinden und Entitäten/Services in HA zu nutzen.
- Das Add-on [`ha-btc-alby-hub-addon`](https://github.com/northpower25/ha-btc-alby-hub-addon/) ist dafür da, Alby Hub lokal als Supervisor-Add-on auf Home Assistant OS bereitzustellen.
- Bei reiner Cloud-/NWC-Nutzung der Integration ist das Add-on nicht zwingend notwendig.
- Für lokale Expert-Funktionen (lokale API/Relay) kann das Add-on erforderlich sein.

## Installation

1. HACS öffnen.
2. Repository `northpower25/ha-btc-alby-hub-integration` als Custom Integration hinzufügen.
3. Integration installieren und Home Assistant neu starten.

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
