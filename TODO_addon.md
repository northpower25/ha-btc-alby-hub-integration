# TODO für das Add-on aus Sicht der Integration

> ⚠️ **Beta-Hinweis:** Add-on und Integration sind Beta-Software. Tests nur mit kleinen Beträgen durchführen. Für verantwortungsvolle Nutzung und Risikomanagement ist der Benutzer selbst verantwortlich.

1. **Scopes serverseitig abfragbar machen**  
   Für verlässliche Pflicht-Checks im Integration-Config-Flow sollte das Add-on (bzw. lokaler Hub) einen Endpoint liefern, der die effektiven NWC-Rechte einer Verbindung ausgibt.

2. **Lokales Relay explizit über Health/Status endpoint ausweisen**  
   Damit die Integration `ws://<ha-host>:3334` nur bei tatsächlicher Verfügbarkeit priorisiert, braucht es eine maschinenlesbare Relay-Statusabfrage.

3. **App-Token/Session-Flow für lokale REST-Nutzung dokumentieren**  
   Für Expert-Modus-Services (Invoice/Payment) sollte der unterstützte Auth-Flow inkl. notwendigen Headern/Cookies stabil dokumentiert oder als Add-on-Hilfsendpoint bereitgestellt werden.
