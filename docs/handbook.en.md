# Alby Hub Integration – Handbook (EN)

## Installation

1. Open HACS.
2. Add `northpower25/ha-btc-alby-hub-integration` as a custom integration repository.
3. Install the integration and restart Home Assistant.

## Configuration (NWC scopes)

- Create an NWC connection in Alby Hub with the required permissions.
- Paste the NWC URI into the integration config flow.
- Grant only the scopes that are actually needed.

## Entities

The integration exposes Alby Hub related entities (depending on granted permissions and available hub data).

## Services

Service calls depend on the granted NWC capabilities. Missing permissions will reject actions.

## Troubleshooting

- Verify URI format and completeness.
- Verify permissions/scopes in Alby Hub.
- Check Home Assistant logs for integration errors.
