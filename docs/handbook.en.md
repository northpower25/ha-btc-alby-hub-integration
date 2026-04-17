# Alby Hub Integration – Handbook (EN)

## Integration vs. Add-on (important)

- **This integration is required** to connect Alby Hub to Home Assistant and expose entities/services in HA.
- The add-on [`ha-btc-alby-hub-addon`](https://github.com/northpower25/ha-btc-alby-hub-addon/) is intended to run Alby Hub locally as a Supervisor add-on on Home Assistant OS.
- For cloud/NWC-only use of this integration, the add-on is not strictly required.
- For local expert features (local API/relay), the add-on can be required.

## Installation

1. Open HACS.
2. Add `northpower25/ha-btc-alby-hub-integration` as a custom integration repository.
3. Install the integration and restart Home Assistant.

## Beta, safety, and responsibility notice

⚠️ This integration and its related add-on are beta software. Under certain conditions, malfunctions, misconfiguration, or external failures can lead to financial loss. Use only small test amounts and do not use large amounts of money for testing.

Common user mistakes:

- Pasting an invalid NWC URI (missing scheme, relay, secret, or pubkey)
- Granting broader scopes/permissions than needed
- Automating payments without strict limits and review
- Trusting local API/relay availability even when connectivity is unstable

Systemic risks:

- Beta bugs, edge cases, or incomplete error handling
- Network, relay, or API outages
- Delayed/inconsistent state updates between Home Assistant and Alby Hub
- Security risks from weak network setup, exposed systems, or compromised keys/secrets

You are solely responsible for the safe and responsible use of the add-on and this integration.

## Configuration (NWC scopes)

- Create an NWC connection in Alby Hub with the required permissions.
- Paste the NWC URI into the integration config flow.
- Required MVP scopes: `get_info`, `get_balance`, `list_transactions`, `make_invoice`.
- Optional: `pay_invoice`.
- If checks warn, you can intentionally continue with \"Continue with warning\".

## Mode behavior

- **Cloud mode:** fully NWC-based, no local API required.
- **Expert mode:** combines NWC and optional local HTTP API.
- With relay preference enabled, `ws://<ha-host>:3334` is prioritized.

## Entities

Current baseline entities:

- Connection (`binary_sensor`)
- Lightning/On-chain balance (`sensor`)
- Lightning address, relay, hub version (`sensor`)

## Services

- `alby_hub.create_invoice` (expert mode, local API)
- `alby_hub.send_payment` (expert mode, local API)

## Troubleshooting

- Verify URI format and completeness.
- Verify permissions/scopes in Alby Hub.
- Check Home Assistant logs for integration errors.
