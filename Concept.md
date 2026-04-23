# Konzept: Nostr Webhook Bot/Client in der Alby-Hub-Integration

## Ziel

Ein eingebauter Nostr-Bot/Client in der Integration, der:

- mit festgelegten `npub`s kommuniziert (Whitelist/ACL),
- Nachrichten verschlüsselt per NIP-44 sendet,
- Webhook-basierte Steuerbefehle sicher entgegennimmt,
- die Kommunikation im Alby-Hub-Dashboard sichtbar macht,
- zusätzlich ein Testfenster für Kommunikation mit eigenem `nsec` bietet.

## Architektur (konkretisiert)

**Datenfluss A (Steuerung):**

1. Externe Nostr-Quelle/Gateway sendet Webhook an  
   `/api/alby_hub/nostr_webhook/{entry_id}`
2. Integration prüft `X-Alby-Nostr-Secret`
3. Integration prüft Sender-`npub` gegen Whitelist
4. Nachricht/Befehl wird protokolliert und als HA-Event weitergegeben  
   (`alby_hub_nostr_webhook_command`)

**Datenfluss B (Antwort/Benachrichtigung):**

1. Nutzer oder Automation ruft `alby_hub.nostr_send_bot_message` auf
2. Integration verschlüsselt Nachricht (NIP-44) und sendet DM über konfiguriertes Relay
3. Versand wird im Dashboard-Nachrichtenprotokoll sichtbar

**Datenfluss C (Testmodus):**

1. Nutzer trägt eigenes `nsec` im Dashboard-Nostr-Reiter ein
2. Integration sendet Test-DM an den Bot-`npub`  
   (`alby_hub.nostr_send_test_message`)
3. Versand wird im Dashboard-Protokoll angezeigt

## Sicherheitsmodell

- **Webhook-Schutz:** Secret im Header `X-Alby-Nostr-Secret`
- **ACL:** nur konfigurierte Whitelist-`npub`s sind erlaubt
- **Least privilege:** keine Weitergabe interner HA-Tokens über Nostr
- **Transparenz:** Ein-/Ausgänge werden mit Zeitstempel protokolliert

## Setup-/Config-Flow Felder

- Nostr Bot/Client aktivieren
- Nostr Relay URL
- Bot Private Key (`nsec` oder hex)
- Erlaubte `npub`s (Whitelist)
- Webhook Secret

## Dashboard-Umsetzung

Im eingebauten Alby-Hub-Panel gibt es einen eigenen **Nostr-Reiter** mit:

1. **Bot-Kommunikation**
   - Bot-`npub`
   - Webhook-URL
   - Versandfeld an Whitelist-`npub`
   - Kommunikationsprotokoll
2. **Testfenster**
   - Login/Test mit eigenem `nsec`
   - Testnachricht an Bot senden

## Zusätzliche sinnstiftende Ideen (Erweiterungen)

1. Rollenmodell pro `npub` (z. B. `admin`, `readonly`)
2. Command-Mapping (`command.light.on` → HA-Service)
3. Rückkanal-Bestätigungen mit strukturierter Statusmeldung (`ok/error`)
4. Optionales Persistenz-Backend für längeren Chatverlauf
5. Optionales Relay-Live-Listening für direkte DM-Empfangswege ohne externes Gateway
6. Audit-Export (CSV/JSON) für Compliance/Debugging
