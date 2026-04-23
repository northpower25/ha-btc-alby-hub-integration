# TODO für das Add-on aus Sicht der Integration

> ⚠️ **Beta-Hinweis:** Add-on und Integration sind Beta-Software. Tests nur mit kleinen Beträgen durchführen. Für verantwortungsvolle Nutzung und Risikomanagement ist der Benutzer selbst verantwortlich.

1. **Scopes serverseitig abfragbar machen**  
   Für verlässliche Pflicht-Checks im Integration-Config-Flow sollte das Add-on (bzw. lokaler Hub) einen Endpoint liefern, der die effektiven NWC-Rechte einer Verbindung ausgibt.

2. **Lokales Relay explizit über Health/Status endpoint ausweisen**  
   Damit die Integration `ws://<ha-host>:3334` nur bei tatsächlicher Verfügbarkeit priorisiert, braucht es eine maschinenlesbare Relay-Statusabfrage.

3. **App-Token/Session-Flow für lokale REST-Nutzung dokumentieren**  
   Für Expert-Modus-Services (Invoice/Payment) sollte der unterstützte Auth-Flow inkl. notwendigen Headern/Cookies stabil dokumentiert oder als Add-on-Hilfsendpoint bereitgestellt werden.

---

## Nostr Webhook Bot/Client (Integration)

- [x] Nostr-Konfigurationsfelder im Setup-/Options-Flow ergänzt (Relay, Bot-NSEC, NPUB-Whitelist, Webhook-Secret, Aktivierung)
- [x] Eigener Nostr-Reiter im eingebauten Dashboard-Panel ergänzt (Bot-Kommunikation + Testfenster mit NSEC-Eingabe)
- [x] Neue Services ergänzt: Bot-Nachricht senden, Testnachricht senden, Nostr-Nachrichten/Status abrufen
- [x] Gesicherter Webhook-Endpunkt für Steuerbefehle ergänzt (`/api/alby_hub/nostr_webhook/{entry_id}` + `X-Alby-Nostr-Secret`)
- [x] Nachrichtenprotokoll für einsehbare Bot-Kommunikation (Dashboard) ergänzt
- [ ] Optional: Vollständige NIP-44-Testvektoren und Interop-Tests gegen mehrere Nostr-Clients ergänzen
- [ ] Optional: Bidirektionales Relay-Listening (nicht nur Webhook-Ingress) für Live-Empfang aus Relays ergänzen
- [ ] Optional: Rollenbasierte ACL (admin/read-only je NPUB) erweitern
