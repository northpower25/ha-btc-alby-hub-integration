# Alby Hub Integration – Developer Handbuch (DE)

> **Dieses Dokument ist das verbindliche Referenzdokument für jeden Entwickler (Mensch oder KI-Agent),
> der an dieser Integration arbeitet. Es muss nach jeder relevanten Änderung aktualisiert werden.**

---

## 1. Übergeordnete Grundsätze

Grundsatz: **Sicherheit zuerst, Guthaben zweitens, Features drittens.**

Diese Integration verarbeitet keine Bitcoin-Funds selbst, kann aber über Konfigurationen, Automationen
und API-Aufrufe indirekt Zahlungen auslösen. Jede Änderung muss so entwickelt werden, dass Nutzer
vor und nach Updates sicher arbeiten können.

---

## 2. Immer-Beachten-Checkliste (für jede Änderung)

Vor jeder Code-Änderung:

- [ ] Betrifft die Änderung Konfigurationsdaten, NWC-URIs, Secrets oder Verbindungsdaten?
      → Migration dokumentieren, kein stilles Überschreiben vorhandener Daten.
- [ ] Betrifft die Änderung Services (create_invoice, send_payment)?
      → Validierungslogik + Fehlerbehandlung vollständig prüfen.
- [ ] Betrifft die Änderung die Coordinator-Logik oder Update-Intervalle?
      → Sicherstellen, dass fehlerhafte Antworten keine falschen Entitätszustände erzeugen.
- [ ] Werden neue Entitäten oder Plattformen hinzugefügt?
      → `PLATFORMS` in `__init__.py` ergänzen, translation_key in `strings.json` + allen
         `translations/*.json` eintragen, entity_description vollständig befüllen.
- [ ] Änderungen an `services.py`, `services.yaml` oder dem Datenschema?
      → `strings.json`, `translations/de.json`, `translations/en.json` und `docs/handbook.de.md`
         + `docs/handbook.en.md` synchron halten.
- [ ] Werden externe APIs aufgerufen (Preis- oder Netzwerk-Provider)?
      → Timeout, Fehlerbehandlung und Fallback auf `None` sicherstellen.
- [ ] Dashboard-Config in `_default_dashboard_config()` geändert?
      → Nur bei Neuinstallation angewendet. Bestehende Installationen werden nicht automatisch
         aktualisiert. Migration manuell dokumentieren.
- [ ] Neue Abhängigkeiten hinzugefügt?
      → `manifest.json` aktualisieren.
- [ ] Tests vorhanden? Syntax validiert?
      → `python -m compileall custom_components/alby_hub` ausführen.

Nach jeder Änderung mit Nutzerauswirkung:

- [ ] `docs/handbook.de.md` und `docs/handbook.en.md` aktualisiert.
- [ ] `docs/developer-handbook.de.md` (dieses Dokument) aktualisiert.
- [ ] `README.md` Kurzübersicht aktualisiert.

---

## 3. Sprache & Übersetzungen – Automatischer Mechanismus

**Kein Sprachfeld im Config-Flow nötig und korrekt.**

Home Assistant wählt automatisch die passende Übersetzungsdatei aus `translations/` auf Basis von
`hass.config.language` (eingestellt unter HA → Profil → Sprache). Unterstützte Sprachen werden durch
Dateien im Format `translations/<lang-code>.json` bereitgestellt.

Regeln:
- Jede neue `translation_key`-Verwendung in Entitäten muss in **allen** vorhandenen
  `translations/*.json`-Dateien eingetragen werden (nicht nur de oder en).
- Fallback ist immer `strings.json` (Basis-Englisch), das als Quelle für alle anderen Sprachen dient.
- Der Nutzer ändert die Anzeigesprache über **Profil → Sprache** in Home Assistant – kein Setup-Flow-Feld.

---

## 4. Architektur-Übersicht

```
custom_components/alby_hub/
├── __init__.py          # Entry point, Platform-Setup, Dashboard-Bootstrap
├── config_flow.py       # Setup-Wizard (Cloud/Expert) mit allen Feldern
├── const.py             # Alle Konstanten, Config-Keys, Provider-Namen
├── coordinator.py       # Datenabruf (Balances, Bitcoin-Preis, Netzwerkdaten)
├── api.py               # Lokale Alby Hub HTTP API (nur Expert-Modus)
├── nwc.py               # NWC-URI-Parsing und Scope-Validierung
├── entity.py            # Basis-Entity-Klasse mit Device-Info
├── helpers.py           # AlbyHubRuntime (Datencontainer pro Entry)
├── sensor.py            # Alle Sensor-Entitäten
├── binary_sensor.py     # Verbindungsstatus
├── text.py              # Text-Entitäten (invoice_input, last_invoice)
├── services.py          # Service-Handler (create_invoice, send_payment)
├── services.yaml        # Service-Deklarationen für HA-UI
├── strings.json         # Basis-Übersetzung (Englisch/Fallback)
├── manifest.json        # Integration-Metadaten, Abhängigkeiten
└── translations/
    ├── de.json          # Deutsche Übersetzung
    └── en.json          # Englische Übersetzung
```

### AlbyHubRuntime (pro Config-Entry)

```python
@dataclass
class AlbyHubRuntime:
    coordinator: AlbyHubDataUpdateCoordinator  # Entitätsdaten, Polling
    api_client: AlbyHubApiClient | None        # HTTP-Client (nur Expert)
    nwc_info: NwcConnectionInfo                # Geparste NWC-Daten
    text_entities: dict[str, AlbyHubTextEntity]  # invoice_input, last_invoice
```

---

## 5. Entitäten-Referenz

### Sensoren

| key | Einheit | Quelle |
|---|---|---|
| `balance_lightning` | sat | Lokale API (Expert) |
| `balance_onchain` | sat | Lokale API (Expert) |
| `lightning_address` | – | NWC lud16-Parameter |
| `relay` | – | NWC relay-Parameter |
| `version` | – | Lokale API (Expert) |
| `bitcoin_price` | Dynamisch (Währung aus Config) | Preis-Provider |
| `bitcoin_block_height` | – | Netzwerk-Provider |
| `bitcoin_hashrate` | EH/s | Netzwerk-Provider |
| `blocks_until_halving` | blocks | Berechnet |
| `next_halving_eta` | Timestamp | Berechnet |

### Text-Entitäten

| key | Beschreibung | Schreibbar von |
|---|---|---|
| `invoice_input` | BOLT11 Eingabe (Senden) | Nutzer / Companion App QR |
| `last_invoice` | Zuletzt erzeugter Invoice (Empfangen) | Service create_invoice |

### Binary Sensoren

| key | Beschreibung |
|---|---|
| `node_online` | Verbindungsstatus (True = erreichbar) |

---

## 6. Services-Referenz

### `alby_hub.create_invoice` (Expert-Modus, lokale API)

Erstellt eine BOLT11-Rechnung. Genau **einen** Betrag angeben:

| Parameter | Typ | Beschreibung |
|---|---|---|
| `amount_sat` | int | Betrag in Satoshi |
| `amount_btc` | float | Betrag in BTC (automatische Umrechnung) |
| `amount_fiat` + `fiat_currency` | float + str | Betrag in Fiat (EUR, USD …), erfordert aktiven Preis-Sensor |
| `memo` | str | Optional: Beschreibung |
| `expiry_seconds` | int | Optional: Ablaufzeit |

Response enthält: `payment_request`, `amount_sat`, `qr_url`.
Der erstellte Invoice wird automatisch in `text.alby_hub_last_invoice` gespeichert.

### `alby_hub.send_payment` (Expert-Modus, lokale API)

Sendet eine BOLT11-Zahlung.

| Parameter | Typ | Beschreibung |
|---|---|---|
| `payment_request` | str | Optional: BOLT11-String. Wird automatisch aus `text.alby_hub_invoice_input` gelesen, wenn leer. |

Nach Erfolg: `text.alby_hub_invoice_input` wird geleert.

---

## 7. Dashboard-Bootstrap

Das Dashboard `alby-hub` wird **einmalig bei der ersten Setup-Ausführung** erstellt (URL-Pfad `alby-hub`,
gespeichert in `.storage/lovelace.alby-hub`). Es enthält drei Views:

- **Receive**: Lightning-Adresse, letzter Invoice + QR-Code-Link (Template-Markdown), Balance
- **Send**: Text-Entität für Invoice-Input, Anleitung (Companion App QR / Paste), Button
- **Network**: Bitcoin-Preis, Blockhöhe, Hashrate, Halving-Daten

**Wichtig:** Nachträgliche Änderungen an `_default_dashboard_config()` betreffen **keine bestehenden**
Installationen. Bestehende Nutzer müssen das Dashboard manuell anpassen oder es löschen und die
Integration neu starten.

---

## 8. Preis- und Netzwerk-Provider

### Preis-Provider (coordinator.py `_fetch_bitcoin_price`)

| Konstante | API-Basis |
|---|---|
| `PRICE_PROVIDER_COINGECKO` | api.coingecko.com |
| `PRICE_PROVIDER_COINBASE` | api.coinbase.com |
| `PRICE_PROVIDER_BINANCE` | api.binance.com |
| `PRICE_PROVIDER_BLOCKCHAIN` | blockchain.info/ticker |
| `PRICE_PROVIDER_COINDESK` | api.coindesk.com |
| `PRICE_PROVIDER_MEMPOOL` | mempool.space/api/v1/prices |
| `PRICE_PROVIDER_BITCOIN_DE` | (noch nicht implementiert) |
| `PRICE_PROVIDER_BITQUERY` | (noch nicht implementiert) |

### Netzwerk-Provider (coordinator.py `_fetch_network_stats`)

| Konstante | Quelle |
|---|---|
| `NETWORK_PROVIDER_MEMPOOL` | mempool.space (Standard) |
| `NETWORK_PROVIDER_CUSTOM_NODE` | Eigene URL (CONF_NETWORK_API_BASE) |

---

## 9. Sicherheits- und Release-Gate

Vor Veröffentlichung/Merge prüfen:

- [ ] NWC-URI / -Secret wird niemals geloggt (nicht in DEBUG-Level).
- [ ] Service-Fehler werden als `HomeAssistantError` oder `ServiceValidationError` geworfen, nie ignoriert.
- [ ] Alle externen API-Aufrufe haben Timeout (aktuell `_API_REQUEST_TIMEOUT_SECONDS = 5`).
- [ ] `CONF_NWC_URI` bleibt in `config_flow.py` als `TextSelectorType.PASSWORD` deklariert.
- [ ] Neue Config-Flow-Felder sind in **allen** translation-JSON-Dateien und `strings.json` eingetragen.
- [ ] Update-Dokumentation enthält konkrete Backup-Checkliste (Abschnitt 10 dieses Dokuments).

---

## 10. Pflicht-Dokumentation bei nutzerrelevanten Änderungen

Wenn ein Release Konfiguration, Authentifizierung, Scopes, Verbindungsdaten, Services oder
Recovery-Prozesse betrifft, muss die Dokumentation enthalten:

1. **Was sich ändert**
2. **Was der Anwender vor dem Update sichern muss**
3. **Welche Sicherheitsmaßnahmen vor dem Update nötig sind**
4. **Wie Recovery nach fehlgeschlagenem Update funktioniert**
5. **Wo Funds im jeweiligen Szenario liegen**

Diese Informationen in diese Dateien eintragen:

- `README.md` (Kurzfassung mit Verweisen)
- `docs/handbook.de.md` (Anwenderdetails Deutsch)
- `docs/handbook.en.md` (Anwenderdetails Englisch)
- Dieses Dokument, Abschnitt 2 (Checkliste aktualisieren)

---

## 11. Minimale Backup- und Recovery-Anforderungen

Die Nutzerdokumentation muss bei relevanten Updates mindestens auf folgende Daten hinweisen:

- Home-Assistant-Backup/Snapshot (inkl. Integrationskonfiguration und `.storage/`-Dateien)
- NWC-Verbindungsdaten (URI/Secret) oder dokumentierter Neuerstellungsprozess
- Zugangsdaten/Recovery-Daten des Alby-Hub-Setups und des zugrunde liegenden Wallet-/Node-Backends
- Channel-/Node-/Seed-Backups je nach verwendetem Wallet-Backend

**Pflichttext:** „Home Assistant und diese Integration ersetzen kein Wallet-/Node-Backup."

---

## 12. Wo liegen die Funds?

- Funds liegen **nicht** in dieser Integration.
- Funds liegen in der Wallet/Node-Umgebung, mit der Alby Hub verbunden ist.
- Ohne Zugriff auf die Recovery-Daten dieser Umgebung kann ein fehlgeschlagenes Update den
  Zugriff auf Funds dauerhaft verhindern.

---

## 13. Change-Management

- Kleine, nachvollziehbare Commits statt großer monolithischer Umbauten.
- Breaking Changes nur mit klarer Migration und Kommunikation.
- Für riskante Änderungen: erst Dokumentation und Migrationshinweise schreiben, dann Code-Release.
- Bei unklaren Recovery-Folgen: Release zurückstellen, bis Wiederherstellung dokumentiert und
  testbar ist.
