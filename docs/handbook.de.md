# Alby Hub Integration – Handbuch (DE)

> **Stand:** April 2026 · Home Assistant ≥ 2026.1 · Integration v1.1.0

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
- **letzter Invoice** (`sensor`) – BOLT11-String als Attribut `bolt11`, inklusive `amount_sat` und `memo`
- **NWC Budget gesamt** (`sensor`) – Gesamtbudget der NWC-Verbindung in sat
- **NWC Budget genutzt** (`sensor`) – bereits verbrauchtes Budget in sat
- **NWC Budget verfügbar** (`sensor`) – verbleibendes Budget in sat
- **NWC Budget Erneuerungszeitraum** (`sensor`) – z. B. daily/weekly/monthly

### Number- und Select-Entitäten (Rechnungsworkflow)

- **`number.alby_hub_invoice_amount`** – Rechnungsbetrag (Eingabe für create_invoice)
- **`select.alby_hub_invoice_amount_unit`** – Einheit: SAT / BTC / Fiat

### Text-Entitäten (Zahlungsworkflow)

- **`text.alby_hub_invoice_input`** – BOLT11-Rechnung hier einfügen oder per QR-Scan befüllen, bevor gesendet wird

### Button-Entitäten

- **`button.alby_hub_create_invoice`** – Rechnung erstellen (ruft create_invoice mit den aktuellen number/select-Werten auf)

## Services

### Zahlungs-Services (Expert-Modus, lokale API)

- **`alby_hub.create_invoice`**
  - Erstellt eine BOLT11-Rechnung.
  - Betrag kann in **Satoshi** (`amount_sat`), **BTC** (`amount_btc`) oder **Fiat** angegeben werden
    (`amount_fiat` + `fiat_currency` – verwendet den Bitcoin-Preis-Sensor für die Umrechnung).
  - Optionale Felder: `memo` (Beschreibung), `expiry_seconds` (Ablaufzeit).
  - Die erzeugte Rechnung wird automatisch in `sensor.alby_hub_last_invoice` gespeichert.
  - Antwort enthält `payment_request`, `amount_sat` und `qr_url`.
- **`alby_hub.send_payment`**
  - Sendet eine BOLT11-Zahlung oder Zahlung an eine Lightning-Adresse (`user@domain.com`).
  - `payment_request` ist optional: wenn nicht angegeben, wird `text.alby_hub_invoice_input` verwendet.
  - Bei Lightning-Adressen zusätzlich `amount_sat`, `amount_btc` oder `amount_fiat`+`fiat_currency` angeben.
  - Optionales Feld: `memo` (Zahlungszweck).
  - Nach erfolgreicher Zahlung wird `text.alby_hub_invoice_input` automatisch geleert.
- **`alby_hub.list_transactions`**
  - Gibt die letzten Lightning-Transaktionen zurück (ein- und ausgehend).
  - Parameter: `limit` (Standard 50, max. 500).

### Wiederkehrende Zahlungen

- **`alby_hub.schedule_payment`** – Erstellt einen Dauerauftrag (Lightning-Adresse oder BOLT11).
  - Pflichtfelder: `recipient`, `amount_sat`, `frequency` (daily/weekly/monthly/quarterly).
  - Optionale Felder: `label`, `memo`, `hour`, `minute`, `day_of_week`, `day_of_month`, `start_date`, `end_date`.
- **`alby_hub.list_scheduled_payments`** – Listet alle konfigurierten Daueraufträge.
- **`alby_hub.update_scheduled_payment`** – Ändert einen Dauerauftrag (via `schedule_id`).
- **`alby_hub.delete_scheduled_payment`** – Löscht einen Dauerauftrag (via `schedule_id`).
- **`alby_hub.run_scheduled_payment_now`** – Führt einen Dauerauftrag sofort aus.

## Automatisierungen mit Alby Hub

Die Integration stellt Entitäten und Services bereit, die du direkt in Home-Assistant-Automationen verwenden kannst. Im Panel (Reiter **Empfangen** und **Senden**) findest du fertige YAML-Beispiele mit einem Kopieren-Button sowie einen Automatisierungs-Generator.

### Richtung 1 – Zahlung empfangen → Entität steuern

**Wann sinnvoll:** Du möchtest, dass HA automatisch etwas tut, sobald eine Zahlung eingegangen ist (z. B. Tür öffnen, Benachrichtigung senden, Licht einschalten).

**Erkennungs-Mechanismus:** Der Sensor `sensor.alby_hub_lightning_balance` ändert seinen Wert, wenn das Guthaben steigt (Zahlung empfangen). Das verwendest du als Auslöser in der Automation.

**Beispiel 1 – Benachrichtigung bei Zahlungseingang:**

```yaml
alias: "Alby Hub – Zahlung empfangen, Benachrichtigung"
description: >
  Sendet eine Benachrichtigung, wenn die Lightning-Balance steigt
  (= eine Zahlung wurde empfangen).
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
        ⚡ Zahlung empfangen!
        Neue Balance: {{ states('sensor.alby_hub_lightning_balance') }} sat
mode: single
```

**So verwendest du dieses Beispiel:**
1. Öffne **Einstellungen → Automationen → + Automatisierung erstellen**.
2. Klicke auf ⋮ (drei Punkte oben rechts) → **YAML bearbeiten**.
3. Füge das YAML ein (ersetze dabei das Bestehende).
4. Ersetze `notify.notify` durch deinen tatsächlichen Benachrichtigungsservice (z. B. `notify.mobile_app_mein_handy`).
5. Speichern – fertig.

---

**Beispiel 2 – Schalter einschalten wenn Zahlung empfangen wird:**

```yaml
alias: "Alby Hub – Zahlung empfangen, Zugang freischalten"
description: >
  Schaltet switch.beispiel_zugang ein, wenn eine Zahlung empfangen wurde.
  Ersetze 'switch.beispiel_zugang' durch deine Ziel-Entität.
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
      entity_id: switch.beispiel_zugang
mode: single
```

**Anpassung:** Ersetze `switch.beispiel_zugang` durch die Entitäts-ID, die du steuern möchtest (z. B. `switch.haustuer`, `light.eingang`, `input_boolean.zahlung_bestaetigt`).

---

### Richtung 2 – Entität / Sensor → Zahlung auslösen

**Wann sinnvoll:** Du möchtest automatisch eine Lightning-Zahlung senden, wenn eine bestimmte Bedingung eintritt (z. B. wenn ein Knopf gedrückt wird, ein Messwert einen Schwellenwert erreicht, oder eine tägliche Abrechnung erfolgen soll).

**Voraussetzung:** Expert-Modus + lokale API aktiv; Service `alby_hub.send_payment` verfügbar.

**Beispiel 3 – Schalter einschalten → Zahlung senden:**

```yaml
alias: "Alby Hub – Schalter → Zahlung auslösen"
description: >
  Löst eine Lightning-Zahlung aus, wenn switch.zahlungs_schalter
  auf 'on' gesetzt wird.
  Ersetze Empfänger-Adresse, Betrag und Schalter-ID.
trigger:
  - platform: state
    entity_id: switch.zahlungs_schalter
    to: "on"
action:
  - service: alby_hub.send_payment
    data:
      payment_request: "empfaenger@lightning.address"
      amount_sat: 1000
      memo: "Automatische Zahlung von Home Assistant"
mode: single
```

**Anpassung:**
- `switch.zahlungs_schalter` → Entitäts-ID deines Auslösers (beliebige HA-Entität)
- `empfaenger@lightning.address` → Lightning-Adresse des Empfängers
- `amount_sat: 1000` → Betrag in Satoshi

---

**Beispiel 4 – Sensor-Grenzwert überschritten → Zahlung senden:**

```yaml
alias: "Alby Hub – Grenzwert überschritten → Zahlung"
description: >
  Löst eine Zahlung aus, wenn sensor.beispiel_sensor
  den Wert 100 überschreitet.
  Ersetze Sensor-ID, Grenzwert, Empfänger und Betrag.
trigger:
  - platform: numeric_state
    entity_id: sensor.beispiel_sensor
    above: 100
action:
  - service: alby_hub.send_payment
    data:
      payment_request: "empfaenger@lightning.address"
      amount_sat: 5000
      memo: "Abrechnung {{ now().strftime('%Y-%m-%d') }}"
mode: single
```

**Anpassung:**
- `sensor.beispiel_sensor` → Sensor-ID (z. B. `sensor.stromzaehler`, `sensor.temperatur_aussen`)
- `above: 100` → dein Grenzwert (auch `below:` möglich)
- `amount_sat: 5000` → Betrag in Satoshi

---

### Automatisierungs-Generator im Panel

Im Alby-Hub-Panel (Reiter **Senden** und **Empfangen**) gibt es einen **Automatisierungs-Generator**:

1. Richtung wählen (Zahlung senden oder auf Zahlung reagieren).
2. Entitäts-IDs, Grenzwert, Empfänger und Betrag eingeben.
3. Auf **⚡ YAML generieren** klicken.
4. Das erzeugte YAML mit **📋 Kopieren** in die Zwischenablage übernehmen.
5. In HA: **Einstellungen → Automationen → + Automatisierung erstellen → ⋮ → YAML bearbeiten** → Einfügen → Speichern.

Du kannst die generierte Automation anschließend im HA-Editor beliebig anpassen.

---

## Kamera & QR-Code-Scan

### Möglichkeit 1 – Browser-Kamera (Gerätekamera)

Im Alby-Hub-Panel (Reiter **Senden**) kannst du eine Gerätekamera für den QR-Code-Scan nutzen:

1. Klicke auf **📱 Gerätekamera starten** im Bereich „QR-Code scannen".
2. Erlaube dem Browser den Kamerazugriff.
3. Halte den QR-Code der zu zahlenden Rechnung vor die Kamera.
4. Der erkannte BOLT11-Code wird automatisch in das Zahlungsfeld übertragen.
5. Klicke auf **➤ Zahlung senden**.

**Hinweis:** Diese Funktion nutzt die Browser-eigene BarcodeDetector-API (verfügbar in Chrome/Edge ≥ 83 und der HA Companion App auf Android). Das Panel enthält zusätzlich einen Chrome/Edge-Kompatibilitäts-Fallback über Video-Frames. In Firefox oder Safari wird stattdessen der Datei-Upload angeboten.

### Möglichkeit 2 – Bild / Foto hochladen

Für alle Browser und Geräte steht eine universelle Alternative bereit:

1. Klicke auf **🖼 Bild wählen**.
2. Wähle ein Foto des QR-Codes aus (auf dem Handy öffnet sich direkt die Kamera).
3. Der QR-Code wird automatisch aus dem Bild extrahiert und ins Zahlungsfeld eingetragen.

### Möglichkeit 3 – HA Kamera-Entität scannen

Falls du eine Überwachungskamera (z. B. Türklingel, Zugangskontrolle) in Home Assistant integriert hast, kannst du deren Snapshot für den QR-Code-Scan verwenden:

1. Wähle im Dropdown „HA Kamera-Entität" die gewünschte Kamera aus.
2. Klicke auf **📷 Snapshot scannen**.
3. Ein aktueller Schnappschuss der Kamera wird abgerufen und auf QR-Codes untersucht.
4. Wird ein BOLT11-Code erkannt, wird er ins Zahlungsfeld übertragen.

**Anwendungsfall:** QR-Code wird vor eine Türkamera gehalten → Integration liest den Code → Zahlung wird ausgelöst.

### Möglichkeit 4 – HA Companion App

In der offiziellen Home-Assistant-Companion-App (Android/iOS) kannst du QR-Codes auch direkt über das **Lovelace-Dashboard** (nicht das Custom Panel) scannen:

1. Öffne das Alby-Hub-Dashboard in der Companion App.
2. Tippe auf das Kamera-Symbol neben dem Eingabefeld `text.alby_hub_invoice_input`.
3. Scanne den QR-Code.
4. Der Wert wird direkt in die Text-Entität geschrieben.
5. Rufe `alby_hub.send_payment` auf (ohne Parameter).

## Lightning empfangen

1. Service `alby_hub.create_invoice` mit gewünschtem Betrag (Satoshi / BTC / Fiat) aufrufen.
2. Die BOLT11-Rechnung wird in `sensor.alby_hub_last_invoice` (Attribut `bolt11`) gespeichert.
3. Alby-Hub-Panel → Reiter „Empfangen" öffnen: zeigt den Invoice-Text und einen QR-Code.
4. Rechnungs-String teilen oder den QR-Code vom Zahler scannen lassen.

Alternativ: Lightning-Adresse (`sensor.alby_hub_lightning_address`) direkt teilen – kein Invoice-Erstellen nötig.

## Lightning senden

1. BOLT11-Rechnung vom Zahlungsempfänger erhalten (per QR-Code oder Kopieren).
2. In `text.alby_hub_invoice_input` einfügen (Alby-Hub-Panel → Reiter „Senden"),
   oder QR-Code scannen (Browser-Kamera, HA Kamera-Entität, Datei-Upload oder Companion App – siehe Abschnitt „Kamera & QR-Code-Scan").
3. Service `alby_hub.send_payment` aufrufen (ohne Parameter, wenn die Entität befüllt ist).

## Sprache / Anzeigesprache

Home Assistant zeigt alle Entitäten und den Config-Flow automatisch in der Sprache an, die unter
**Profil → Sprache** in Home Assistant eingestellt ist. Kein zusätzliches Setup erforderlich.
Verfügbare Übersetzungen: Englisch (`en`), Deutsch (`de`).

## Dashboard

Nach der Einrichtung wird automatisch ein **Alby Hub**-Panel in der Seitenleiste erstellt. Das Panel enthält sieben Reiter:

- **⚡ Übersicht** – Verbindungsstatus, Balances (sat / BTC / Fiat), Bitcoin-Preis, Blockhöhe, Verbindungsinfos
- **↙ Empfangen** – Rechnung erstellen (Betrag + Einheit + Verwendungszweck), BOLT11-Anzeige mit QR-Code, Lightning-Adresse mit QR-Code, Automatisierungs-Beispiele
- **↗ Senden** – Invoice-Eingabe, QR-Code-Scan (Browser-Kamera / HA Kamera-Entität / Datei), Zahlung senden, Automatisierungs-Beispiele
- **💰 Budget** – NWC-Ausgabelimits (gesamt / genutzt / verfügbar / Erneuerungszeitraum)
- **₿ Netzwerk** – Bitcoin-Preis, Blockhöhe, Hashrate, Halving-Countdown
- **📋 Aktivität** – Letzte Transaktionen (ein- und ausgehend, filterbar)
- **🔁 Geplant** – Daueraufträge anlegen, bearbeiten, löschen und sofort ausführen

Alternativ steht unter `dashboards/alby-hub-dashboard.yaml` ein Lovelace-Template zum manuellen Import bereit.

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
