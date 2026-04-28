# Alby Hub Integration – Handbook (EN)

> **As of:** April 2026 · Home Assistant ≥ 2026.1 · Integration v1.1.0

## Integration vs. Add-on (important)

- **This integration is required** to connect Alby Hub to Home Assistant and expose entities/services in HA.
- The add-on [`ha-btc-alby-hub-addon`](https://github.com/northpower25/ha-btc-alby-hub-addon/) is intended to run Alby Hub locally as a Supervisor add-on on Home Assistant OS.
- For cloud/NWC-only use of this integration, the add-on is not strictly required.
- For local expert features (local API/relay), the add-on can be required.

## Nostr basics (short)

- **Nostr is decentralized:** there is no single provider controlling all communication.
- **Centralized bot/messenger providers** usually bind users to one operator and infrastructure.
- With Nostr, identity and transport are open standards (keys + relays), giving users more client and infrastructure choice.

Why this matters here:

- **NWC (Nostr Wallet Connect)** already uses Nostr as the communication layer to Alby Hub.
- The built-in Nostr bot/client in this integration extends this model with secure webhook-based command routing.

## Nostr apps for smartphones (examples)

Examples (non-exhaustive):

- **iOS:** Damus, Primal
- **Android:** Amethyst, Primal
- **iOS/Android (depending on current releases):** additional clients such as Nos

Always verify key handling, backup strategy, and trust model before production use.

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
6. Optionally enable the Nostr bot:
   - If you do not yet have bot `NSEC`/`NPUB`, leave **Bot private key** empty.
   - The next step (**Save your Nostr bot identity**) displays the generated `npub` and `nsec` — copy and save them securely now (password manager, paper backup). The `nsec` will **not** be shown again after this step.
   - Copy/paste your own client `NPUB` (whitelist) from your Nostr app.
   - For local relay/key setup on HA OS, the add-on can help: https://github.com/northpower25/ha-btc-alby-hub-addon
7. Run the connection check and carefully review all warnings before proceeding.
8. Save the configuration.
9. Verify entities and status in Home Assistant.

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
- **Last invoice** (`sensor`) – BOLT11 string in attribute `bolt11`, including `amount_sat` and `memo`
- **NWC budget total** (`sensor`) – total NWC spending budget in sat
- **NWC budget used** (`sensor`) – already spent budget in sat
- **NWC budget remaining** (`sensor`) – remaining budget in sat
- **NWC budget renewal period** (`sensor`) – e.g. daily/weekly/monthly

### Number and select entities (invoice workflow)

- **`number.alby_hub_invoice_amount`** – invoice amount (input for create_invoice)
- **`select.alby_hub_invoice_amount_unit`** – unit: SAT / BTC / Fiat

### Text entities (payment workflow)

- **`text.alby_hub_invoice_input`** – paste or scan a BOLT11 invoice here before sending

### Button entities

- **`button.alby_hub_create_invoice`** – create invoice (calls create_invoice with the current number/select values)

### Notify entity

- **`notify.alby_hub_nostr_bot`** – Sends a Nostr DM to **all** whitelisted NPubs (only active when the Nostr bot is enabled). Uses the configured encryption mode. Optional `title` is prepended as "title: message".

### Diagnostic sensor

- **`sensor.alby_hub_api_debug_status`** (diagnostic category) – Current API connection status with detailed debug attributes (e.g. last error, response time).

## Services

### Payment services (expert mode, local API)

- **`alby_hub.create_invoice`**
  - Creates a BOLT11 invoice.
  - Amount can be given in **satoshis** (`amount_sat`), **BTC** (`amount_btc`),
    or **fiat** (`amount_fiat` + `fiat_currency` – uses the Bitcoin price sensor).
  - Optional fields: `memo` (description), `expiry_seconds` (expiry time).
  - The created invoice is saved to `sensor.alby_hub_last_invoice` for display.
  - Returns `payment_request`, `amount_sat`, and `qr_url` as service response.
- **`alby_hub.send_payment`**
  - Sends a BOLT11 payment or a payment to a Lightning address (`user@domain.com`).
  - `payment_request` is optional: if omitted, the value from `text.alby_hub_invoice_input` is used.
  - For Lightning address payments, additionally provide `amount_sat`, `amount_btc`, or `amount_fiat`+`fiat_currency`.
  - Optional field: `memo` (payment purpose).
  - After successful payment, `text.alby_hub_invoice_input` is cleared automatically.
- **`alby_hub.list_transactions`**
  - Returns recent Lightning transactions (incoming and outgoing).
  - Parameter: `limit` (default 50, max 500).

### Recurring payments

- **`alby_hub.schedule_payment`** – Creates a recurring payment (Lightning address or BOLT11).
  - Required fields: `recipient`, `amount_sat`, `frequency` (daily/weekly/monthly/quarterly).
  - Optional fields: `label`, `memo`, `hour`, `minute`, `day_of_week`, `day_of_month`, `start_date`, `end_date`.
- **`alby_hub.list_scheduled_payments`** – Lists all configured recurring payment schedules.
- **`alby_hub.update_scheduled_payment`** – Updates a recurring payment schedule (via `schedule_id`).
- **`alby_hub.delete_scheduled_payment`** – Deletes a recurring payment schedule (via `schedule_id`).
- **`alby_hub.run_scheduled_payment_now`** – Executes a schedule immediately.

## Nostr bot

### Configuration

The Nostr bot is enabled in the config flow. Key fields:

- **Bot private key (NSEC):** Leave empty to auto-generate a new key pair on first start. The generated `nsec` is displayed **once** in the config flow – **copy and save it securely** (password manager, paper backup). It will **not** be shown again.
- **Allowed NPubs (whitelist):** Comma-separated Nostr public keys (`npub…` or 64-char hex) the bot will accept.
- **Webhook secret:** Any string used to protect the webhook endpoint.
- **Nostr relays:** List of relay URLs the bot communicates through (default: several public relays).
- **Encryption mode:** `nip04` (default, maximum compatibility with Damus, Primal, WhiteNoise, Oxchat), `nip44`, `both`, or `plaintext`.

### Encryption modes

| Mode | Description |
|---|---|
| `nip04` | Default. Broadest compatibility with most Nostr clients. |
| `nip44` | Modern encryption (ChaCha20-Poly1305). Not all clients support NIP-44. |
| `both` | Sends both NIP-04 and NIP-44 – maximum reach. |
| `plaintext` | Unencrypted. For testing only, not for production. |

### Nostr services

- **`alby_hub.nostr_send_bot_message`** – Sends an encrypted DM from the bot to a specific NPub (must be whitelisted).
  - Required fields: `target_npub`, `message`.
  - Optional field: `config_entry_id` (when multiple Alby Hub entries exist).
- **`alby_hub.nostr_send_test_message`** – Sends a NIP-44 test DM from a custom `nsec` to the configured bot NPub. Useful for testing bot communication.
  - Required fields: `nsec`, `message`.
- **`alby_hub.nostr_list_messages`** – Returns current bot status and recent inbound/outbound messages.
  - Optional field: `limit` (default 100, max 250).

### Notify entity

Use `notify.alby_hub_nostr_bot` in automations to send Nostr DMs to **all** whitelisted NPubs:

```yaml
action:
  - action: notify.alby_hub_nostr_bot
    data:
      message: "⚡ Payment received!"
      title: "Alby Hub"   # Optional – prepended as "Alby Hub: Payment received!"
```

### Relay listener

When the bot is enabled and valid relays are configured, a **relay listener** starts automatically in the background. It receives incoming Nostr DMs sent to the bot NPub in real time and forwards commands as Home Assistant events (`alby_hub_nostr_webhook_command`).

### Webhook endpoint

The bot exposes an HTTP webhook at `/api/alby_hub/nostr_webhook/{entry_id}`. Incoming requests are verified using the `X-Alby-Nostr-Secret` header and the NPub whitelist.

---

## Address book

The address book allows managing contacts directly in Home Assistant. Each contact can store: first/last name, Lightning address, Bitcoin address, Nostr public key and alias, notes, tags, and more.

### Address book services

- **`alby_hub.address_book_create_contact`** – Creates a new contact.
  - Optional fields: `first_name`, `last_name`, `lightning_address`, `bitcoin_address`, `nostr_pubkey`, `nostr_alias`, `notes`, `tags`.
- **`alby_hub.address_book_list_contacts`** – Returns all contacts (sorted by last name, first name).
- **`alby_hub.address_book_get_contact`** – Returns a single contact by `contact_id`.
- **`alby_hub.address_book_update_contact`** – Updates fields of an existing contact (via `contact_id`).
- **`alby_hub.address_book_delete_contact`** – Permanently deletes a contact (via `contact_id`).

Contact IDs (UUIDs) are obtained via `address_book_list_contacts` or `address_book_get_contact`.

---

## Automations with Alby Hub

The integration exposes entities and services that you can use directly in Home Assistant automations. The panel (tabs **Receive** and **Send**) includes ready-to-use YAML examples with a copy button, plus an automation generator.

### Direction 1 – Payment received → control entity

**When useful:** You want HA to automatically do something when a payment arrives (e.g. open a door, send a notification, turn on a light).

**How it works:** The sensor `sensor.alby_hub_lightning_balance` changes its value when the balance increases (= payment received). Use this as the trigger in your automation.

**Example 1 – Notification on incoming payment:**

```yaml
alias: "Alby Hub – Payment received, send notification"
description: >
  Sends a notification when the Lightning balance increases
  (= a payment was received).
trigger:
  - platform: state
    entity_id: sensor.alby_hub_lightning_balance
condition:
  - condition: template
    value_template: >
      {{ trigger.to_state.state | int(0) >
         trigger.from_state.state | int(0) }}
action:
  - service: notify.notify
    data:
      message: >
        ⚡ Payment received!
        New balance: {{ states('sensor.alby_hub_lightning_balance') }} sat
mode: single
```

**How to use this example:**
1. Open **Settings → Automations → + Create Automation**.
2. Click ⋮ (three dots, top right) → **Edit in YAML**.
3. Paste the YAML (replace the existing content).
4. Replace `notify.notify` with your actual notification service (e.g. `notify.mobile_app_my_phone`).
5. Save – done.

---

**Example 2 – Turn on a switch when a payment is received:**

```yaml
alias: "Alby Hub – Payment received, grant access"
description: >
  Turns switch.example_access on when a payment is received.
  Replace 'switch.example_access' with your target entity.
trigger:
  - platform: state
    entity_id: sensor.alby_hub_lightning_balance
condition:
  - condition: template
    value_template: >
      {{ trigger.to_state.state | int(0) >
         trigger.from_state.state | int(0) }}
action:
  - service: switch.turn_on
    target:
      entity_id: switch.example_access
mode: single
```

**Adapt:** Replace `switch.example_access` with the entity you want to control (e.g. `switch.front_door`, `light.entrance`, `input_boolean.payment_confirmed`).

---

### Direction 2 – Entity / sensor → trigger payment

**When useful:** You want to automatically send a Lightning payment when a certain condition is met (e.g. a button is pressed, a sensor value crosses a threshold, or a scheduled billing should occur).

**Prerequisite:** Expert mode + local API active; service `alby_hub.send_payment` available.

**Example 3 – Switch turned on → send Lightning payment:**

```yaml
alias: "Alby Hub – Switch → trigger payment"
description: >
  Triggers a Lightning payment when switch.payment_trigger is turned on.
  Replace recipient address, amount, and switch ID.
trigger:
  - platform: state
    entity_id: switch.payment_trigger
    to: "on"
action:
  - service: alby_hub.send_payment
    data:
      payment_request: "recipient@lightning.address"
      amount_sat: 1000
      memo: "Automatic payment from Home Assistant"
mode: single
```

**Adapt:**
- `switch.payment_trigger` → entity ID of your trigger (any HA entity)
- `recipient@lightning.address` → Lightning address of the recipient
- `amount_sat: 1000` → amount in satoshis

---

**Example 4 – Sensor threshold exceeded → send Lightning payment:**

```yaml
alias: "Alby Hub – Threshold exceeded → payment"
description: >
  Triggers a payment when sensor.example_sensor exceeds the value 100.
  Replace sensor ID, threshold, recipient, and amount.
trigger:
  - platform: numeric_state
    entity_id: sensor.example_sensor
    above: 100
action:
  - service: alby_hub.send_payment
    data:
      payment_request: "recipient@lightning.address"
      amount_sat: 5000
      memo: "Billing {{ now().strftime('%Y-%m-%d') }}"
mode: single
```

**Adapt:**
- `sensor.example_sensor` → sensor ID (e.g. `sensor.energy_meter`, `sensor.temperature_outside`)
- `above: 100` → your threshold (also `below:` is possible)
- `amount_sat: 5000` → amount in satoshis

---

### Automation generator in the panel

The Alby Hub panel (**Send** and **Receive** tabs) includes an **Automation Generator**:

1. Choose a direction (trigger payment or react to payment).
2. Enter entity IDs, threshold, recipient, and amount.
3. Click **⚡ Generate YAML**.
4. Copy the generated YAML using **📋 Copy**.
5. In HA: **Settings → Automations → + Create Automation → ⋮ → Edit in YAML** → paste → save.

You can further edit the generated automation in the HA editor at any time.

---

## Camera & QR code scanning

### Option 1 – Device camera (browser)

In the Alby Hub panel (tab **Send**) you can use a device camera to scan QR codes:

1. Click **📱 Start device camera** in the "Scan QR code" section.
2. Allow the browser to access the camera.
3. Hold the QR code of the invoice up to the camera.
4. The detected BOLT11 code is automatically transferred to the payment field.
5. Click **➤ Send Payment**.

**Note:** This feature primarily uses the browser's native BarcodeDetector API (available in Chrome/Edge ≥ 83 and the HA Companion App on Android). If it is unavailable or unreliable, the panel now automatically falls back to `html5-qrcode` for improved scan reliability (camera and image scan).

### Option 2 – Upload image / photo

A universal alternative is available for all browsers and devices:

1. Click **🖼 Choose image**.
2. Select a photo of the QR code (on mobile, the camera app opens directly).
3. The QR code is automatically extracted from the image and filled into the payment field.

### Option 3 – HA camera entity scan

If you have a surveillance camera (e.g. doorbell, access control) integrated in Home Assistant, you can use its snapshot for QR code scanning:

1. Select the desired camera from the "HA camera entity" dropdown.
2. Click **📷 Scan snapshot**.
3. A current snapshot of the camera is retrieved and checked for QR codes.
4. If a BOLT11 code is detected, it is transferred to the payment field.

**Use case:** QR code is held up to a door camera → integration reads the code → payment is triggered.

### Option 4 – HA Companion App

In the official Home Assistant Companion App (Android/iOS) you can also scan QR codes directly via the **Lovelace dashboard** (not the custom panel):

1. Open the Alby Hub dashboard in the Companion App.
2. Tap the camera icon next to the `text.alby_hub_invoice_input` field.
3. Scan the QR code.
4. The value is written directly to the text entity.
5. Call `alby_hub.send_payment` (no parameters needed).

## Lightning receive workflow

1. Call `alby_hub.create_invoice` with the desired amount (sat / BTC / fiat).
2. The BOLT11 invoice is stored in `sensor.alby_hub_last_invoice` (attribute `bolt11`).
3. Open the Alby Hub panel → Receive tab to see the invoice text and QR code.
4. Share the invoice string or let the payer scan the QR code.

Alternatively, share your Lightning address (`sensor.alby_hub_lightning_address`) directly for
push payments without creating an invoice.

## Lightning send workflow

1. Get a BOLT11 invoice from the payee (via their QR code or copy).
2. Paste it into `text.alby_hub_invoice_input` from the Alby Hub panel → Send tab,
   or scan the QR code (device camera, HA camera entity, file upload, or Companion App – see "Camera & QR code scanning").
3. Call `alby_hub.send_payment` (no parameters needed if you filled the entity).

## Troubleshooting

- Verify the NWC URI (complete, correct scheme `nostr+walletconnect://`).
- Check scopes/permissions in Alby Hub.
- Review Home Assistant logs for integration errors.
- If the Nostr bot does not connect, verify relay URLs and that the bot NSEC is set.
- For expert mode issues, check that the local API URL (`http://<host>:8080`) is reachable from Home Assistant.

## Language / display language

Home Assistant automatically displays all entities and the config flow in the language configured under
**Profile → Language**. No additional setup required.
Available translations: English (`en`), German (`de`).

## Dashboard

After setup, an **Alby Hub** panel is automatically created in the sidebar. The panel contains eight tabs:

- **⚡ Overview** – connection status, balances (sat / BTC / fiat), Bitcoin price, block height, connection info
- **↙ Receive** – create invoice (amount + unit + memo), BOLT11 display with QR code, Lightning address with QR code, automation examples
- **↗ Send** – invoice input, QR code scan (device camera / HA camera entity / file), send payment, automation examples
- **💰 Budget** – NWC spending limits (total / used / remaining / renewal period)
- **₿ Network** – Bitcoin price, block height, hashrate, halving countdown
- **📋 Activity** – recent transactions (incoming and outgoing, filterable)
- **🔁 Scheduled** – create, edit, delete, and immediately run recurring payments
- **🔒 Nostr** – bot NPub, webhook URL, message log, test window for custom NSEC

A Lovelace template is also available at `dashboards/alby-hub-dashboard.yaml` for manual import.

## Update security: what to do before every update

Before **every** update to the integration, add-on, or Alby Hub environment:

1. **Create a Home Assistant backup/snapshot** (including configuration).
2. Ensure NWC connection data (URI/secret) is securely available or can be recreated.
3. Ensure recovery data for the wallet/node backend is available (e.g. seed, channel backups, credentials – depending on setup).
4. Consider temporarily disabling automations that trigger payments until the update is verified.

Important: Home Assistant and this integration do **not** replace a wallet/node backup.

## What data you must have backed up before an update or reinstallation

- Home Assistant backup/snapshot
- NWC connection data or a documented recreation process
- Alby Hub credentials/recovery information
- Wallet/node recovery data of the actual fund-holding backend

Without this data, access to features and potentially to funds may be lost after a failed update or reinstallation (see "Recovery after a failed update or reinstallation").

## Where Bitcoin funds are stored per scenario

- **Cloud/NWC scenario:** Funds are in the wallet/node environment behind the NWC connection, not in Home Assistant.
- **Local add-on/expert scenario:** Funds are in the locally operated Alby Hub/wallet/node environment or its connected backend, not in this integration.

The integration provides control/display only and holds no funds.

## Recovery after a failed update or reinstallation

1. Restore Home Assistant and the add-on/environment to a stable state.
2. Re-import backed-up configuration and connection data.
3. Reconfigure the integration (NWC/expert settings).
4. Restore access to the wallet/node environment using its own recovery procedures.
5. Only then re-enable payment automations.

If wallet/node recovery data is missing, access to funds may be permanently lost.
