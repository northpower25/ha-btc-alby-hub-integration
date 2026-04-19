# Alby Hub Integration – Handbook (EN)

## Integration vs. Add-on (important)

- **This integration is required** to connect Alby Hub to Home Assistant and expose entities/services in HA.
- The add-on [`ha-btc-alby-hub-addon`](https://github.com/northpower25/ha-btc-alby-hub-addon/) is intended to run Alby Hub locally as a Supervisor add-on on Home Assistant OS.
- For cloud/NWC-only use of this integration, the add-on is not strictly required.
- For local expert features (local API/relay), the add-on can be required.

## Alignment with official Alby Hub guides

Official sources:

- Hub overview: https://guides.getalby.com/user-guide/alby-hub
- Getting started: https://guides.getalby.com/user-guide/alby-hub/getting-started
- Flavors: https://guides.getalby.com/user-guide/alby-hub/alby-hub-flavors

Official Alby Hub flavors describe **where** your Hub runs:
Alby Cloud, Desktop, Docker, Umbrel/Start9/etc., Linux.

How this integration maps to those flavors:

| Scenario | Meaning for this integration |
|---|---|
| External Hub (Alby Cloud/Desktop/Docker/Linux/Umbrel/Start9/etc.) | Integration connects directly via NWC URI to the existing Hub |
| Hub running locally in the HA add-on (expert mode) | Integration connects via NWC and can optionally use local expert features |

Alby-side note: An Alby account is often recommended (for example lightning address, easier app linking, notifications/support), but it is not technically mandatory in every setup.

## What should be completed before integration setup (from Alby getting-started)

1. Choose your Alby Hub flavor and complete initial Hub deployment.
2. Finish first-run Hub tasks (for example account linking, channel/spending balance, backup/recovery data depending on setup).
3. In Alby Hub, create a dedicated Home Assistant NWC app connection via **Apps → Add Connection**.
4. Grant only required scopes (least privilege).
5. Treat the NWC secret like a password and rotate it if compromise is suspected.

## Installation & Configuration (step by step)

### Prerequisites

1. A running Home Assistant instance.
2. For HACS installation: HACS is already installed and set up.
3. For local Alby Hub usage on HA OS, optionally use the add-on:  
   [`ha-btc-alby-hub-addon`](https://github.com/northpower25/ha-btc-alby-hub-addon/).

### Option A: Install via HACS (recommended)

1. Open Home Assistant.
2. Go to **HACS → Integrations**.
3. Open the menu (⋮) and select **Custom repositories**.
4. Add repository URL `https://github.com/northpower25/ha-btc-alby-hub-integration`.
5. Select type **Integration** and confirm.
6. Search for **Alby Hub** in HACS.
7. Install the integration.
8. Restart Home Assistant.

### Option B: Manual installation

1. Download the current integration from this repository (ZIP or Git checkout).
2. Copy folder `custom_components/alby_hub` into your Home Assistant config directory at  
   `/config/custom_components/alby_hub`.
3. Verify at least this file exists:  
   `/config/custom_components/alby_hub/manifest.json`.
4. Restart Home Assistant.

### Configure in Home Assistant

1. Go to **Settings → Devices & Services** in Home Assistant.
2. Click **Add Integration**.
3. Search for and select **Alby Hub**.
4. Choose mode:
   - **Cloud mode** (NWC-based), or
   - **Expert mode** (optional local API/relay).
5. Paste the NWC connection URI from Alby Hub.
6. Run the connection check and carefully review all warnings before proceeding.
7. Save the configuration.
8. Verify entities and status in Home Assistant.

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

Current entities:

### Sensors

- Connection (`binary_sensor`) – node online status
- Lightning balance / On-chain balance (`sensor`) – in satoshis
- Lightning address, NWC relay, hub version (`sensor`)
- **Bitcoin price** (`sensor`) – in the configured fiat currency (e.g. EUR, USD)
- **Bitcoin block height** (`sensor`)
- **Bitcoin hashrate** (`sensor`) – in EH/s
- **Blocks until halving** (`sensor`)
- **Next halving estimate** (`sensor`) – timestamp

### Text entities (invoice workflow)

- **`text.alby_hub_invoice_input`** – paste or scan a BOLT11 invoice here before sending
- **`text.alby_hub_last_invoice`** – displays the last created invoice (BOLT11 string)

## Services

- `alby_hub.create_invoice` (expert mode, local API)
  - Amount can be given in **satoshis** (`amount_sat`), **BTC** (`amount_btc`),
    or **fiat** (`amount_fiat` + `fiat_currency` – uses the Bitcoin price sensor).
  - The created invoice is saved to `text.alby_hub_last_invoice` for display.
  - Returns `payment_request`, `amount_sat`, and `qr_url` as service response.
- `alby_hub.send_payment` (expert mode, local API)
  - `payment_request` is optional: if omitted, the value from `text.alby_hub_invoice_input` is used.
  - After successful payment, `text.alby_hub_invoice_input` is cleared automatically.

## Lightning receive workflow

1. Call `alby_hub.create_invoice` with the desired amount (sat / BTC / fiat).
2. The BOLT11 invoice is stored in `text.alby_hub_last_invoice`.
3. Open the Alby Hub dashboard → Receive view to see the invoice text and a QR code link.
4. Share the invoice string or let the payer scan the QR code.

Alternatively, share your Lightning address (`sensor.alby_hub_lightning_address`) directly for
push payments without creating an invoice.

## Lightning send workflow

1. Get a BOLT11 invoice from the payee (via their QR code or copy).
2. Paste it into `text.alby_hub_invoice_input` from the Alby Hub dashboard → Send view,
   or scan the QR code with the Home Assistant Companion App camera.
3. Call `alby_hub.send_payment` (no parameters needed if you pasted into the entity).

## Language / Display language

Home Assistant automatically shows all entities and the config flow in the language configured
under **Profile → Language** in Home Assistant. No additional setup is needed.
Translation files exist for: English (`en`), German (`de`).

## Dashboard

After setup, an **Alby Hub** dashboard is automatically created with three views:

- **Receive** – Lightning address, last invoice with QR code link, balance
- **Send** – Invoice input entity, instructions, send button
- **Network** – Bitcoin price, block height, hashrate, halving countdown

## Troubleshooting

- Verify URI format and completeness.
- Verify permissions/scopes in Alby Hub.
- Check Home Assistant logs for integration errors.
