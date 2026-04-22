/**
 * Alby Hub Panel
 *
 * A custom Home Assistant sidebar panel for the Alby Hub integration.
 * Rendered entirely by this Web Component using Shadow DOM – users
 * cannot edit entities or layout through the standard HA Lovelace UI.
 *
 * Features:
 * - Auto-discovers all configured Alby Hub instances
 * - Five tabs: Overview · Receive · Send · Budget · Network
 * - Interactive controls: create invoice, send payment
 * - Locked-down layout – tiles and entities are defined by the integration
 *
 * @version 1.0.0
 * @author northpower25
 * @license MIT
 */

const ALBY_HUB_VERSION = '1.1.0';
const PANEL_ELEMENT_NAME = 'alby-hub-panel';

// ──────────────────────────────────────────────────────────────────────────────
// Translations (DE / EN)
// ──────────────────────────────────────────────────────────────────────────────
const TRANSLATIONS = {
  de: {
    tabs: { overview: '⚡ Übersicht', receive: '↙ Empfangen', send: '↗ Senden', budget: '💰 Budget', network: '₿ Netzwerk', activity: '📋 Aktivität', scheduled: '🔁 Geplant' },
    noInstance: 'Keine Alby-Hub-Instanz gefunden',
    noInstanceHint: 'Konfiguriere die Alby-Hub-Integration unter <strong>Einstellungen → Geräte & Dienste</strong>.',
    overview: {
      title: 'Übersicht',
      connected: '✅ Verbunden', offline: '🔴 Offline',
      balance: 'Guthaben', connection: 'Verbindung',
      lightning: 'Lightning', onchain: 'On-Chain',
      btcPrice: 'Bitcoin-Preis', blockHeight: 'Blockhöhe',
      nodeOnline: 'Node online', nwcRelay: 'NWC-Relay',
      hubVersion: 'Hub-Version', lightningAddress: 'Lightning-Adresse',
    },
    receive: {
      createInvoice: 'Rechnung erstellen',
      amount: 'Betrag', unit: 'Einheit (SAT / BTC / Fiat)',
      purpose: 'Verwendungszweck (optional)',
      btn: 'Rechnung erstellen ⚡',
      invoiceTitle: 'BOLT11-Rechnung & QR-Code',
      noInvoice: 'Noch keine Rechnung. Betrag und Einheit oben eingeben, dann <b>Rechnung erstellen</b> drücken.',
      scanHint: 'Rechnung scannen oder kopieren',
      invoiceAmountSat: 'Betrag (sat)',
      invoicePurpose: 'Verwendungszweck',
      lnAddressTitle: 'Lightning-Adresse',
      lnAddressQrTitle: 'Lightning-Adresse QR (ohne festen Betrag empfangen)',
      lnAddressUnavail: 'Lightning-Adresse nicht verfügbar.',
      balanceTitle: 'Guthaben',
    },
    send: {
      paymentTitle: 'Zahlung',
      invoice: 'BOLT11-Rechnung / Lightning-Adresse',
      invoicePlaceholder: 'lnbc… oder user@domain.com',
      amountTitle: 'Betrag (optional – bei Lightning-Adresse erforderlich)',
      amount: 'Betrag',
      unit: 'Einheit (SAT / BTC / Fiat)',
      purpose: 'Verwendungszweck (optional)',
      howTitle: 'Zahlung durchführen',
      how1: '<b>Option 1 – Einfügen:</b><br>BOLT11-Rechnung oder Lightning-Adresse in das Feld oben einfügen.',
      how2: '<b>Option 2 – Kamera (HA Companion App):</b><br>QR-Code-Scan wird direkt im Lovelace-Dashboard unterstützt, nicht im benutzerdefinierten Panel.',
      how3: 'Dann <b>Zahlung senden</b> drücken.',
      sendBtn: '➤ Zahlung senden',
      balanceTitle: 'Guthaben',
    },
    budget: {
      usageTitle: 'Budget-Nutzung',
      used: 'genutzt',
      remaining: 'Verfügbar',
      renewal: 'Erneuerung',
      noBudget: 'Kein Budgetlimit konfiguriert oder Hub unterstützt get_budget nicht.',
      limitsTitle: 'NWC-Ausgabelimits',
      totalBudget: 'Gesamtbudget', usedBudget: 'Genutztes Budget',
      remainingBudget: 'Verfügbares Budget', renewalPeriod: 'Erneuerungszeitraum',
      aboutTitle: 'Über NWC-Budget',
      about: 'Diese Sensoren zeigen die Ausgabelimits dieser NWC-Verbindung.',
      aboutTotal: '<b>Gesamtbudget</b> – maximaler Betrag pro Erneuerungszeitraum',
      aboutUsed: '<b>Genutztes Budget</b> – bereits ausgegebener Betrag',
      aboutRemaining: '<b>Verfügbares Budget</b> – noch verfügbarer Betrag',
      aboutRenewal: '<b>Erneuerungszeitraum</b> – wie oft das Budget zurückgesetzt wird',
      aboutUnavail: "Sensoren zeigen 'nicht verfügbar', wenn kein Budgetlimit gesetzt ist.",
    },
    network: {
      marketTitle: 'Bitcoin-Markt & Netzwerk',
      btcPrice: 'Bitcoin-Preis', blockHeight: 'Blockhöhe',
      hashrate: 'Hashrate', blocksUntilHalving: 'Blöcke bis Halving',
      nextHalving: 'Nächste Halving-Schätzung',
      halvingTitle: 'Nächstes Halving',
      halvingBlocks: 'bis zum nächsten Halving.',
      halvingDate: 'Geschätztes Datum',
      halvingUnavail: 'Halving-Daten nicht verfügbar.',
    },
    activity: {
      title: 'Aktivität',
      refresh: '↺ Aktualisieren',
      loading: 'Lade Transaktionen…',
      noTx: 'Keine Transaktionen gefunden.',
      filterAll: 'Alle', filterIn: '↙ Eingang', filterOut: '↗ Ausgang',
      typeIn: '↙ Eingang', typeOut: '↗ Ausgang',
      amount: 'Betrag', fee: 'Gebühr', desc: 'Beschreibung',
      date: 'Datum', pending: '⏳ Ausstehend',
      colType: 'Typ', colAmount: 'Betrag (sat)', colFee: 'Gebühr', colDesc: 'Beschreibung', colDate: 'Datum',
    },
    scheduled: {
      title: 'Geplante Zahlungen',
      newTitle: 'Neue wiederkehrende Zahlung',
      listTitle: 'Aktive Aufträge',
      noSchedules: 'Keine geplanten Zahlungen vorhanden.',
      recipient: 'Empfänger (Lightning-Adresse oder BOLT11)',
      recipientPlaceholder: 'user@domain.com oder lnbc…',
      amount: 'Betrag (Satoshi)',
      label: 'Bezeichnung (optional)',
      labelPlaceholder: 'z. B. Taschengeld Lisa',
      memo: 'Zahlungsnotiz (optional)',
      frequency: 'Wiederholung',
      freqDaily: 'Täglich', freqWeekly: 'Wöchentlich', freqMonthly: 'Monatlich', freqQuarterly: 'Quartalsweise',
      time: 'Uhrzeit',
      dayOfWeek: 'Wochentag',
      dow0: 'Montag', dow1: 'Dienstag', dow2: 'Mittwoch', dow3: 'Donnerstag',
      dow4: 'Freitag', dow5: 'Samstag', dow6: 'Sonntag',
      dayOfMonth: 'Tag des Monats (1–28)',
      startDate: 'Startdatum',
      endDate: 'Enddatum (leer = kein Ende)',
      createBtn: '+ Auftrag erstellen',
      updateBtn: '💾 Auftrag speichern',
      cancelEditBtn: 'Abbrechen',
      editBtn: '✏️ Bearbeiten',
      runNowBtn: '▶ Jetzt ausführen',
      deleteBtn: '🗑 Löschen',
      colLabel: 'Bezeichnung', colRecipient: 'Empfänger', colAmount: 'Betrag', colFreq: 'Intervall', colNext: 'Nächste Ausführung', colLastRun: 'Letzte Ausführung',
      never: 'Noch nicht ausgeführt',
      refresh: '↺ Aktualisieren',
      creating: 'Wird erstellt…',
      deleting: 'Wird gelöscht…',
      errAmountMin: 'Betrag muss mindestens 1 sat sein.',
      errRecipient: 'Bitte Empfänger angeben.',
    },
    camera: {
      title: '📷 QR-Code scannen',
      selectEntity: 'HA Kamera-Entität (optional)',
      noCamera: '– keine –',
      scanEntityBtn: '📷 Snapshot scannen',
      deviceCameraBtn: '📱 Gerätekamera starten',
      fileInputBtn: '🖼 Bild wählen',
      stopBtn: '⏹ Scan stoppen',
      hint: 'Erkannter QR-Code wird automatisch ins Zahlungsfeld übertragen.',
      scanning: '⏳ Scanne…',
      found: '✅ QR-Code erkannt',
      notFound: '❌ Kein QR-Code erkannt. Bitte erneut versuchen.',
      error: '⚠️ Scan-Fehler',
      noBarcodeApiHint: '⚠️ BarcodeDetector nicht verfügbar (Firefox/Safari). Bitte "Bild wählen" nutzen.',
      companionHint: '💡 HA Companion App (Android/iOS): QR-Code direkt im Lovelace-Dashboard über das Kamera-Symbol scannen.',
    },
    autoExamples: {
      receiveTitle: '🤖 Automatisierungen – Empfangen (Beispiele)',
      sendTitle: '🤖 Automatisierungen – Senden (Beispiele)',
      intro: 'Beispiel auswählen → 📋 Kopieren → in HA unter <b>Einstellungen → Automationen → + Automatisierung erstellen → ⋮ → YAML bearbeiten</b> einfügen → anpassen → speichern.',
      copy: '📋 Kopieren',
      copied: '✅ Kopiert!',
    },
    autoBuilder: {
      title: '⚙️ Automatisierungs-Generator',
      intro: 'Felder ausfüllen → YAML generieren → kopieren → in HA-Automatisierungseditor einfügen.',
      direction: 'Richtung',
      dirSend: 'Zahlung auslösen (Senden)',
      dirReceive: 'Auf Zahlung reagieren (Empfangen)',
      triggerType: 'Auslöser-Typ',
      trigStateOn: 'Entität wird eingeschaltet (→ on)',
      trigThreshAbove: 'Sensorwert überschreitet Grenzwert',
      trigThreshBelow: 'Sensorwert unterschreitet Grenzwert',
      trigBalanceIncrease: 'Lightning-Balance steigt (Zahlung empfangen)',
      trigEntityId: 'Entitäts-ID des Auslösers',
      trigThreshold: 'Grenzwert',
      actionType: 'Aktion',
      actSendPayment: 'Lightning-Zahlung senden',
      actTurnOn: 'Entität einschalten',
      actTurnOff: 'Entität ausschalten',
      actNotify: 'Benachrichtigung senden',
      recipient: 'Empfänger (z.B. user@wallet.de)',
      amountSat: 'Betrag (sat)',
      memo: 'Zahlungsnotiz (optional)',
      targetEntityId: 'Ziel-Entität (z.B. switch.steckdose)',
      notifyMsg: 'Benachrichtigungstext',
      generateBtn: '⚡ YAML generieren',
      copyBtn: '📋 YAML kopieren',
      copied: '✅ Kopiert!',
      placeholder: 'Formular ausfüllen und auf "⚡ YAML generieren" klicken…',
      haHint: '💡 <b>Einstellungen → Automationen → + Automatisierung erstellen → ⋮ → YAML bearbeiten</b> → einfügen → speichern.',
    },
    unavailable: 'nicht verfügbar',
  },
  en: {
    tabs: { overview: '⚡ Overview', receive: '↙ Receive', send: '↗ Send', budget: '💰 Budget', network: '₿ Network', activity: '📋 Activity', scheduled: '🔁 Scheduled' },
    noInstance: 'No Alby Hub instance found',
    noInstanceHint: 'Configure the Alby Hub integration under <strong>Settings → Devices &amp; Services</strong>.',
    overview: {
      title: 'Overview',
      connected: '✅ Connected', offline: '🔴 Offline',
      balance: 'Balance', connection: 'Connection',
      lightning: 'Lightning', onchain: 'On-chain',
      btcPrice: 'Bitcoin Price', blockHeight: 'Block Height',
      nodeOnline: 'Node Online', nwcRelay: 'NWC Relay',
      hubVersion: 'Hub Version', lightningAddress: 'Lightning Address',
    },
    receive: {
      createInvoice: 'Create Invoice',
      amount: 'Amount', unit: 'Unit (SAT / BTC / Fiat)',
      purpose: 'Purpose (optional)',
      btn: 'Create Invoice ⚡',
      invoiceTitle: 'BOLT11 Invoice & QR Code',
      noInvoice: 'No invoice yet. Set the amount and unit above, then press <b>Create Invoice</b>.',
      scanHint: 'Scan or copy the invoice above',
      invoiceAmountSat: 'Amount (sat)',
      invoicePurpose: 'Purpose',
      lnAddressTitle: 'Lightning Address',
      lnAddressQrTitle: 'Lightning Address QR (receive without fixed amount)',
      lnAddressUnavail: 'Lightning address not available.',
      balanceTitle: 'Balance',
    },
    send: {
      paymentTitle: 'Payment',
      invoice: 'BOLT11 Invoice / Lightning Address',
      invoicePlaceholder: 'lnbc… or user@domain.com',
      amountTitle: 'Amount (optional – required when paying a Lightning address)',
      amount: 'Amount',
      unit: 'Unit (SAT / BTC / Fiat)',
      purpose: 'Purpose (optional)',
      howTitle: 'How to pay',
      how1: '<b>Option 1 – Paste:</b><br>Copy a BOLT11 invoice (or Lightning address) and paste it into the field above.',
      how2: '<b>Option 2 – Camera (HA Companion App):</b><br>QR-code scanning is supported in the native Lovelace dashboard, not in this custom panel.',
      how3: 'Then press <b>Send Payment</b> below.',
      sendBtn: '➤ Send Payment',
      balanceTitle: 'Balance',
    },
    budget: {
      usageTitle: 'Budget Usage',
      used: 'used',
      remaining: 'Remaining',
      renewal: 'Renewal',
      noBudget: 'No budget limit configured, or hub does not support get_budget.',
      limitsTitle: 'NWC Spending Limits',
      totalBudget: 'Total Budget', usedBudget: 'Used Budget',
      remainingBudget: 'Remaining Budget', renewalPeriod: 'Renewal Period',
      aboutTitle: 'About NWC Budget',
      about: 'These sensors show the spending limits configured for this NWC connection.',
      aboutTotal: '<b>Total budget</b> – maximum amount this connection may spend per renewal period',
      aboutUsed: '<b>Used budget</b> – amount already spent in the current period',
      aboutRemaining: '<b>Remaining budget</b> – amount still available to spend',
      aboutRenewal: '<b>Renewal period</b> – how often the budget resets (daily / weekly / monthly / …)',
      aboutUnavail: "Sensors show 'unavailable' if no budget limit is set or if your hub does not support get_budget.",
    },
    network: {
      marketTitle: 'Bitcoin Market & Network',
      btcPrice: 'Bitcoin Price', blockHeight: 'Block Height',
      hashrate: 'Hashrate', blocksUntilHalving: 'Blocks Until Halving',
      nextHalving: 'Next Halving Estimate',
      halvingTitle: 'Next Halving',
      halvingBlocks: 'remaining until the next halving.',
      halvingDate: 'Estimated date',
      halvingUnavail: 'Halving data not available.',
    },
    activity: {
      title: 'Activity',
      refresh: '↺ Refresh',
      loading: 'Loading transactions…',
      noTx: 'No transactions found.',
      filterAll: 'All', filterIn: '↙ Incoming', filterOut: '↗ Outgoing',
      typeIn: '↙ Incoming', typeOut: '↗ Outgoing',
      amount: 'Amount', fee: 'Fee', desc: 'Description',
      date: 'Date', pending: '⏳ Pending',
      colType: 'Type', colAmount: 'Amount (sat)', colFee: 'Fee', colDesc: 'Description', colDate: 'Date',
    },
    scheduled: {
      title: 'Scheduled Payments',
      newTitle: 'New Recurring Payment',
      listTitle: 'Active Schedules',
      noSchedules: 'No scheduled payments configured.',
      recipient: 'Recipient (Lightning address or BOLT11)',
      recipientPlaceholder: 'user@domain.com or lnbc…',
      amount: 'Amount (satoshi)',
      label: 'Label (optional)',
      labelPlaceholder: 'e.g. Pocket money Lisa',
      memo: 'Payment memo (optional)',
      frequency: 'Repeat',
      freqDaily: 'Daily', freqWeekly: 'Weekly', freqMonthly: 'Monthly', freqQuarterly: 'Quarterly',
      time: 'Time',
      dayOfWeek: 'Day of week',
      dow0: 'Monday', dow1: 'Tuesday', dow2: 'Wednesday', dow3: 'Thursday',
      dow4: 'Friday', dow5: 'Saturday', dow6: 'Sunday',
      dayOfMonth: 'Day of month (1–28)',
      startDate: 'Start date',
      endDate: 'End date (empty = no end)',
      createBtn: '+ Create schedule',
      updateBtn: '💾 Save schedule',
      cancelEditBtn: 'Cancel',
      editBtn: '✏️ Edit',
      runNowBtn: '▶ Run now',
      deleteBtn: '🗑 Delete',
      colLabel: 'Label', colRecipient: 'Recipient', colAmount: 'Amount', colFreq: 'Frequency', colNext: 'Next run', colLastRun: 'Last run',
      never: 'Never run',
      refresh: '↺ Refresh',
      creating: 'Creating…',
      deleting: 'Deleting…',
      errAmountMin: 'Amount must be at least 1 sat.',
      errRecipient: 'Please specify a recipient.',
    },
    camera: {
      title: '📷 Scan QR Code',
      selectEntity: 'HA camera entity (optional)',
      noCamera: '– none –',
      scanEntityBtn: '📷 Scan snapshot',
      deviceCameraBtn: '📱 Start device camera',
      fileInputBtn: '🖼 Choose image',
      stopBtn: '⏹ Stop scan',
      hint: 'Detected QR code will be automatically transferred to the payment field.',
      scanning: '⏳ Scanning…',
      found: '✅ QR code detected',
      notFound: '❌ No QR code found. Please try again.',
      error: '⚠️ Scan error',
      noBarcodeApiHint: '⚠️ BarcodeDetector not available (Firefox/Safari). Please use "Choose image".',
      companionHint: '💡 HA Companion App (Android/iOS): scan QR codes in the Lovelace dashboard via the camera icon.',
    },
    autoExamples: {
      receiveTitle: '🤖 Automation Examples (Receive)',
      sendTitle: '🤖 Automation Examples (Send)',
      intro: 'Choose an example → 📋 Copy → in HA go to <b>Settings → Automations → + Create Automation → ⋮ → Edit in YAML</b>, paste, adapt and save.',
      copy: '📋 Copy',
      copied: '✅ Copied!',
    },
    autoBuilder: {
      title: '⚙️ Automation Generator',
      intro: 'Fill in the fields → generate YAML → copy → paste into the HA automation editor.',
      direction: 'Direction',
      dirSend: 'Trigger a payment (Send)',
      dirReceive: 'React to payment (Receive)',
      triggerType: 'Trigger type',
      trigStateOn: 'Entity is turned on (→ on)',
      trigThreshAbove: 'Sensor value exceeds threshold',
      trigThreshBelow: 'Sensor value falls below threshold',
      trigBalanceIncrease: 'Lightning balance increases (payment received)',
      trigEntityId: 'Trigger entity ID',
      trigThreshold: 'Threshold value',
      actionType: 'Action',
      actSendPayment: 'Send Lightning payment',
      actTurnOn: 'Turn entity on',
      actTurnOff: 'Turn entity off',
      actNotify: 'Send notification',
      recipient: 'Recipient (e.g. user@wallet.com)',
      amountSat: 'Amount (sat)',
      memo: 'Payment memo (optional)',
      targetEntityId: 'Target entity (e.g. switch.socket)',
      notifyMsg: 'Notification message',
      generateBtn: '⚡ Generate YAML',
      copyBtn: '📋 Copy YAML',
      copied: '✅ Copied!',
      placeholder: 'Fill in the form and click "⚡ Generate YAML"…',
      haHint: '💡 <b>Settings → Automations → + Create Automation → ⋮ → Edit in YAML</b> → paste → save.',
    },
    unavailable: 'unavailable',
  },
};

// ──────────────────────────────────────────────────────────────────────────────
// Entity ID builders
//
// Entity IDs are derived from HA's slugified translation names:
//   {platform}.{device_slug}_{entity_name_slug}
// e.g. device "Alby Hub" → device_slug "alby_hub"
//      entity name "Lightning balance" → name_slug "lightning_balance"
//      → sensor.alby_hub_lightning_balance
// ──────────────────────────────────────────────────────────────────────────────
const ENTITY_IDS = {
  nodeOnline:          { domain: 'binary_sensor', suffixes: ['node_online'] },
  lightningBalance:    { domain: 'sensor',        suffixes: ['lightning_balance', 'balance_lightning'] },
  onChainBalance:      { domain: 'sensor',        suffixes: ['on_chain_balance', 'balance_onchain'] },
  lightningAddress:    { domain: 'sensor',        suffixes: ['lightning_address', 'lightning_adresse'] },
  nwcRelay:            { domain: 'sensor',        suffixes: ['nwc_relay', 'relay'] },
  hubVersion:          { domain: 'sensor',        suffixes: ['hub_version', 'version'] },
  bitcoinPrice:        { domain: 'sensor',        suffixes: ['bitcoin_price', 'bitcoin_preis'] },
  bitcoinBlockHeight:  { domain: 'sensor',        suffixes: ['bitcoin_block_height', 'bitcoin_blockhoehe'] },
  bitcoinHashrate:     { domain: 'sensor',        suffixes: ['bitcoin_hashrate'] },
  blocksUntilHalving:  { domain: 'sensor',        suffixes: ['blocks_until_halving', 'bloecke_bis_halving'] },
  nextHalvingEstimate: { domain: 'sensor',        suffixes: ['next_halving_estimate', 'next_halving_eta', 'naechstes_halving_schaetzung'] },
  nwcBudgetTotal:      { domain: 'sensor',        suffixes: ['nwc_budget_total', 'nwc_budget_gesamt'] },
  nwcBudgetUsed:       { domain: 'sensor',        suffixes: ['nwc_budget_used', 'nwc_budget_genutzt'] },
  nwcBudgetRemaining:  { domain: 'sensor',        suffixes: ['nwc_budget_remaining', 'nwc_budget_verfuegbar'] },
  nwcBudgetRenewal:    { domain: 'sensor',        suffixes: ['nwc_budget_renewal_period', 'nwc_budget_renewal', 'nwc_budget_erneuerungszeitraum'] },
  invoiceAmount:       { domain: 'number',        suffixes: ['invoice_amount', 'rechnungsbetrag'] },
  invoiceAmountUnit:   { domain: 'select',        suffixes: ['invoice_amount_unit', 'einheit_des_rechnungsbetrags'] },
  createInvoice:       { domain: 'button',        suffixes: ['create_invoice', 'rechnung_erstellen', 'create_invoice_btn'] },
  // last_invoice is a sensor; full BOLT11 lives in the "bolt11" attribute
  lastInvoice:         { domain: 'sensor',        suffixes: ['last_invoice', 'letzte_rechnung'] },
  invoiceInput:        { domain: 'text',          suffixes: ['invoice_input', 'rechnungseingabe'] },
};

// Minimum ms between content-only updates (throttle)
const UPDATE_THROTTLE_MS = 2000;

// ──────────────────────────────────────────────────────────────────────────────
// AlbyHubPanel – main Web Component
// ──────────────────────────────────────────────────────────────────────────────
class AlbyHubPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._hass = null;
    this._narrow = false;
    this._instances = [];     // [{prefix, displayName}]
    this._activePrefix = null;
    this._activeTab = 'overview';
    this._lastInstanceKey = '';
    this._lastUpdate = 0;
    this._visibilityHandler = null;
    // Preserved input values (survive re-renders)
    this._pendingInvAmount = '';   // receive: amount typed by user
    this._pendingInvUnit   = '';   // receive: unit selected by user
    this._pendingInvMemo   = '';   // receive: memo / purpose
    this._pendingPayInput  = '';   // send: payment string typed by user
    this._pendingPayAmount = '';   // send: amount typed by user
    this._pendingPayUnit   = '';   // send: unit selected by user
    this._pendingPayMemo   = '';   // send: memo / purpose
    this._lastInvoiceByPrefix = {}; // prefix -> {bolt11, amount_sat, memo}
    // Activity tab state
    this._txFilter = 'all';        // 'all' | 'incoming' | 'outgoing'
    this._transactions = null;     // null = not loaded, [] = loaded
    this._txLoading = false;
    // Scheduled payments tab state
    this._schedules = null;        // null = not loaded
    this._schedLoading = false;
    this._schedEditId = null;
    // Scheduled form state
    this._schedForm = {
      recipient: '', amount: '', label: '', memo: '',
      frequency: 'monthly', hour: '8', minute: '0',
      day_of_week: '0', day_of_month: '1',
      start_date: this._todayIso(), end_date: '',
    };
    // Camera scan state
    this._cameraStream = null;
    this._cameraScanning = false;
    this._cameraEntitySel = '';
    this._cameraScanMsg = '';
    // Automation builder state
    this._autoForm = {
      direction: 'send',
      triggerType: 'state_on',
      trigEntityId: '',
      threshold: '100',
      actionType: 'send_payment',
      recipient: '',
      amountSat: '1000',
      memo: '',
      targetEntityId: '',
      notifyMsg: '',
    };
    this._autoYaml = '';
    this._autoBuilderVisible = false;
  }

  connectedCallback() {
    this._visibilityHandler = () => {
      if (document.visibilityState === 'visible' && this._hass) {
        this._lastUpdate = 0;
        this._updateContent();
      }
    };
    document.addEventListener('visibilitychange', this._visibilityHandler);
  }

  disconnectedCallback() {
    if (this._visibilityHandler) {
      document.removeEventListener('visibilitychange', this._visibilityHandler);
      this._visibilityHandler = null;
    }
  }

  // ── HA panel API ────────────────────────────────────────────────────────────

  /** Translation helper: returns the string for the current HA language. */
  _t(path) {
    const lang = (this._hass?.language || 'en').split('-')[0].toLowerCase();
    const dict = TRANSLATIONS[lang] || TRANSLATIONS['en'];
    return path.split('.').reduce((o, k) => (o && o[k] !== undefined ? o[k] : null), dict)
      ?? path.split('.').reduce((o, k) => (o && o[k] !== undefined ? o[k] : null), TRANSLATIONS['en'])
      ?? path;
  }

  /** Dynamically built tabs using current language. */
  _tabs() {
    const t = this._t.bind(this);
    return [
      { id: 'overview',   label: t('tabs.overview')   },
      { id: 'receive',    label: t('tabs.receive')    },
      { id: 'send',       label: t('tabs.send')       },
      { id: 'budget',     label: t('tabs.budget')     },
      { id: 'network',    label: t('tabs.network')    },
      { id: 'activity',   label: t('tabs.activity')   },
      { id: 'scheduled',  label: t('tabs.scheduled')  },
    ];
  }

  set hass(hass) {
    this._hass = hass;

    const instances = this._discoverInstances(hass);
    const key = instances.map((i) => i.prefix).join(',');

    if (key !== this._lastInstanceKey) {
      // Instance list changed – full structural re-render
      this._lastInstanceKey = key;
      this._instances = instances;
      if (!this._activePrefix || !instances.find((i) => i.prefix === this._activePrefix)) {
        this._activePrefix = instances.length > 0 ? instances[0].prefix : null;
      }
      this._render();
      return;
    }

    // Same instances – throttled content update only
    const now = Date.now();
    if (now - this._lastUpdate >= UPDATE_THROTTLE_MS) {
      this._updateContent();
    }
  }

  set panel(p)  { this._panel = p; }
  set narrow(n) {
    this._narrow = n;
    const btn = this.shadowRoot.querySelector('ha-menu-button');
    if (btn) btn.narrow = n;
  }

  // ── Discovery ───────────────────────────────────────────────────────────────

  _discoverInstances(hass) {
    const seen = new Set();
    const instances = [];
    const lightningBalanceSuffixes = ENTITY_IDS.lightningBalance.suffixes.map((s) => `_${s}`);

    for (const entityId of Object.keys(hass.states)) {
      if (!entityId.startsWith('sensor.')) continue;
      const matchedSuffix = lightningBalanceSuffixes.find((suffix) => entityId.endsWith(suffix));
      if (!matchedSuffix) continue;

      const prefix = entityId.slice('sensor.'.length, -matchedSuffix.length);
      if (seen.has(prefix)) continue;

      // Require the node_online binary sensor to confirm this is an Alby Hub
      const hasNodeOnline = ENTITY_IDS.nodeOnline.suffixes.some(
        (suffix) => Boolean(hass.states[`binary_sensor.${prefix}_${suffix}`])
      );
      if (!hasNodeOnline) continue;
      seen.add(prefix);

      // Derive display name: strip " Lightning balance" from friendly_name, or title-case prefix
      const state = hass.states[entityId];
      let displayName = prefix.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
      const fn = state?.attributes?.friendly_name;
      if (fn) {
        const stripped = fn.replace(
          /\s+(Lightning[-\s]+balance|Lightning[-\s]+guthaben|Balance[-\s]+Lightning)\s*$/i,
          ''
        ).trim();
        if (stripped) displayName = stripped;
      }

      instances.push({ prefix, displayName });
    }

    return instances.sort((a, b) => a.displayName.localeCompare(b.displayName));
  }

  // ── State helpers ────────────────────────────────────────────────────────────

  _esc(v) {
    return String(v ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  _state(id)                     { return this._hass?.states[id]; }
  _val(id, def = 'unavailable')  { return this._state(id)?.state ?? def; }
  _attr(id, attr, def = '')      { return this._state(id)?.attributes?.[attr] ?? def; }
  _num(id, def = 0)              { return parseFloat(this._val(id, String(def))) || def; }
  _isUnavail(v)                  { return !v || v === 'unavailable' || v === 'unknown' || v === 'none' || v === ''; }
  _displayAmountValue(raw, unit) {
    if (raw === undefined || raw === null) return '';
    const str = String(raw);
    if ((unit || '').toUpperCase() === 'SAT') {
      const n = parseFloat(str);
      if (Number.isFinite(n)) return String(Math.floor(n));
    }
    return str;
  }
  _todayIso() {
    return new Date().toISOString().slice(0, 10);
  }
  _eid(kind, prefix) {
    const cfg = ENTITY_IDS[kind];
    if (!cfg || !prefix) return '';
    for (const suffix of cfg.suffixes) {
      const entityId = `${cfg.domain}.${prefix}_${suffix}`;
      if (this._hass?.states?.[entityId]) return entityId;
    }
    return `${cfg.domain}.${prefix}_${cfg.suffixes[0]}`;
  }

  // ── Full structural render ───────────────────────────────────────────────────

  _render() {
    const root = this.shadowRoot;

    if (this._instances.length === 0) {
      root.innerHTML = `
        ${this._css()}
        <div class="panel-root">
          <div class="header">
            <ha-menu-button></ha-menu-button>
            <span class="header-icon">⚡</span>
            <span class="header-title">Alby Hub</span>
          </div>
          <div class="empty-state">
            <div class="empty-icon">⚡</div>
            <h2>${this._t('noInstance')}</h2>
            <p>${this._t('noInstanceHint')}</p>
          </div>
        </div>`;
      this._applyMenuBtn();
      return;
    }

    const p = this._activePrefix;
    const multi = this._instances.length > 1;
    const displayName = this._instances.find((i) => i.prefix === p)?.displayName ?? '';

    const instanceBar = multi
      ? `<div class="instance-bar">${this._instances
          .map(
            (i) =>
              `<button class="instance-btn${i.prefix === p ? ' active' : ''}" data-prefix="${this._esc(i.prefix)}">${this._esc(i.displayName)}</button>`
          )
          .join('')}</div>`
      : '';

    const tabBar = `<div class="tab-bar">${this._tabs().map(
      (t) =>
        `<button class="tab-btn${t.id === this._activeTab ? ' active' : ''}" data-tab="${t.id}">${t.label}</button>`
    ).join('')}</div>`;

    root.innerHTML = `
      ${this._css()}
      <div class="panel-root">
        <div class="header">
          <ha-menu-button></ha-menu-button>
          <span class="header-icon">⚡</span>
          <span class="header-title">Alby Hub${!multi ? ` – ${this._esc(displayName)}` : ''}</span>
        </div>
        ${instanceBar}
        ${tabBar}
        <div class="content" id="content">${this._renderTab(this._activeTab, p)}</div>
      </div>`;

    this._applyMenuBtn();
    this._attachListeners();
    this._lastUpdate = Date.now();
  }

  // ── Content-only update ──────────────────────────────────────────────────────

  _updateContent() {
    // Skip update if user is currently interacting with an input/select
    const focused = this.shadowRoot.querySelector(':focus');
    if (focused && (focused.tagName === 'INPUT' || focused.tagName === 'SELECT' || focused.tagName === 'TEXTAREA')) {
      return;
    }
    const scrollSnapshots = Array.from(this.shadowRoot.querySelectorAll('.tx-scroll')).map((el) => ({
      scrollLeft: el.scrollLeft,
      scrollTop: el.scrollTop,
    }));
    const content = this.shadowRoot.querySelector('#content');
    if (!content || !this._activePrefix) return;
    content.innerHTML = this._renderTab(this._activeTab, this._activePrefix);
    this._attachContentListeners();
    Array.from(this.shadowRoot.querySelectorAll('.tx-scroll')).forEach((el, idx) => {
      const snap = scrollSnapshots[idx];
      if (!snap) return;
      el.scrollLeft = snap.scrollLeft;
      el.scrollTop = snap.scrollTop;
    });
    // Re-attach live camera stream if scanning
    if (this._cameraScanning && this._cameraStream) {
      const video = this.shadowRoot.querySelector('#camera-video');
      if (video && !video.srcObject) {
        video.srcObject = this._cameraStream;
        video.play().catch(() => {});
      }
    }
    this._lastUpdate = Date.now();
  }

  // ── Tab dispatcher ───────────────────────────────────────────────────────────

  _renderTab(id, p) {
    switch (id) {
      case 'overview':   return this._tabOverview(p);
      case 'receive':    return this._tabReceive(p);
      case 'send':       return this._tabSend(p);
      case 'budget':     return this._tabBudget(p);
      case 'network':    return this._tabNetwork(p);
      case 'activity':   return this._tabActivity(p);
      case 'scheduled':  return this._tabScheduled(p);
      default:           return '';
    }
  }

  // ── Tab: Overview ────────────────────────────────────────────────────────────

  _tabOverview(p) {
    const t        = (k) => this._t(`overview.${k}`);
    const isOnline = this._val(this._eid('nodeOnline', p)) === 'on';
    const lightning  = this._num(this._eid('lightningBalance', p));
    const onchain    = this._num(this._eid('onChainBalance', p));
    const price      = this._num(this._eid('bitcoinPrice', p));
    const currency   = this._attr(this._eid('bitcoinPrice', p), 'unit_of_measurement', '');
    const relay      = this._val(this._eid('nwcRelay', p));
    const version    = this._val(this._eid('hubVersion', p));
    const address    = this._val(this._eid('lightningAddress', p));
    const blockH     = this._val(this._eid('bitcoinBlockHeight', p));
    const dispName   = this._instances.find((i) => i.prefix === p)?.displayName ?? p;

    const lnBtc   = (lightning / 1e8).toFixed(8);
    const ocBtc   = (onchain   / 1e8).toFixed(8);
    const lnFiat  = price > 0 ? ((lightning / 1e8) * price).toFixed(2) : null;
    const ocFiat  = price > 0 ? ((onchain   / 1e8) * price).toFixed(2) : null;

    return `<div class="cards-grid">
      <div class="card">
        <div class="card-title">⚡ ${this._esc(dispName)}</div>
        <div class="badge ${isOnline ? 'badge-on' : 'badge-off'}">${isOnline ? t('connected') : t('offline')}</div>
        <table class="bal-table">
          <thead><tr><th></th><th>⚡ ${t('lightning')}</th><th>₿ ${t('onchain')}</th></tr></thead>
          <tbody>
            <tr><td>sat</td><td class="num">${lightning.toLocaleString()}</td><td class="num">${onchain.toLocaleString()}</td></tr>
            <tr><td>BTC</td><td class="num">${lnBtc}</td><td class="num">${ocBtc}</td></tr>
            ${lnFiat ? `<tr><td>≈&nbsp;${this._esc(currency)}</td><td class="num">${lnFiat}</td><td class="num">${ocFiat}</td></tr>` : ''}
          </tbody>
        </table>
      </div>

      <div class="card">
        <div class="card-title">${t('balance')}</div>
        ${this._row('⚡', t('lightning'), `${lightning.toLocaleString()} sat`)}
        ${this._row('₿', t('onchain'),  `${onchain.toLocaleString()} sat`)}
        ${price > 0
          ? this._row('💵', `${t('btcPrice')} (${this._esc(currency)})`, price.toLocaleString())
          : this._row('💵', t('btcPrice'), `<span class="muted">${this._t('unavailable')}</span>`, true)}
        ${this._row('🧱', t('blockHeight'), this._esc(blockH))}
      </div>

      <div class="card">
        <div class="card-title">${t('connection')}</div>
        ${this._row(isOnline ? '🟢' : '🔴', t('nodeOnline'), isOnline ? 'On' : 'Off')}
        ${this._row('🔗', t('nwcRelay'),        this._esc(relay),   false, true)}
        ${this._row('ℹ️', t('hubVersion'),      this._esc(version))}
        ${this._row('📧', t('lightningAddress'), this._esc(address), false, true)}
      </div>
    </div>`;
  }

  // ── Tab: Receive ─────────────────────────────────────────────────────────────

  _tabReceive(p) {
    const t       = (k) => this._t(`receive.${k}`);
    const fallbackUnit = this._val(this._eid('invoiceAmountUnit', p), 'SAT');
    // Use pending (user-typed) values when available, fall back to entity state
    const amountRaw = this._pendingInvAmount || this._val(this._eid('invoiceAmount', p), '0');
    const unit = this._pendingInvUnit || fallbackUnit;
    const amount = this._displayAmountValue(amountRaw, unit);
    const memo = this._pendingInvMemo || '';
    const options = this._attr(this._eid('invoiceAmountUnit', p), 'options', ['SAT', 'BTC']);
    // last_invoice is a sensor; latest successful service response is used as immediate fallback
    const invoiceEntity = this._eid('lastInvoice', p);
    const latestInvoice = this._lastInvoiceByPrefix[p] || {};
    const invoice = this._attr(invoiceEntity, 'bolt11', '') || latestInvoice.bolt11 || '';
    const invoiceAmountSatRaw = this._attr(invoiceEntity, 'amount_sat', null);
    const invoiceAmountSat = Number.isFinite(Number(invoiceAmountSatRaw))
      ? Number(invoiceAmountSatRaw)
      : (Number.isFinite(Number(latestInvoice.amount_sat)) ? Number(latestInvoice.amount_sat) : null);
    const invoiceMemo = this._attr(invoiceEntity, 'memo', '') || latestInvoice.memo || '';
    const address   = this._val(this._eid('lightningAddress', p), '');
    const lightning = this._num(this._eid('lightningBalance', p));
    const onchain   = this._num(this._eid('onChainBalance', p));

    const opts = Array.isArray(options)
      ? options
          .map((o) => `<option value="${this._esc(o)}"${o === unit ? ' selected' : ''}>${this._esc(o)}</option>`)
          .join('')
      : `<option value="SAT"${unit === 'SAT' ? ' selected' : ''}>SAT</option>
         <option value="BTC"${unit === 'BTC' ? ' selected' : ''}>BTC</option>`;

    const invoiceBlock = !this._isUnavail(invoice)
      ? `<code class="invoice-code">${this._esc(invoice)}</code>
         <div class="qr-wrap">
            <img class="qr" src="https://api.qrserver.com/v1/create-qr-code/?data=lightning:${encodeURIComponent(invoice)}&size=280x280&margin=8" alt="Invoice QR">
          </div>
         ${invoiceAmountSat !== null ? `<div class="muted small"><b>${t('invoiceAmountSat')}:</b> ${invoiceAmountSat.toLocaleString()} sat</div>` : ''}
         <div class="muted small"><b>${t('invoicePurpose')}:</b> ${this._esc(invoiceMemo || '—')}</div>
         <div class="muted small">${t('scanHint')}</div>`
      : `<div class="muted">${t('noInvoice')}</div>`;

    const addrBlock = !this._isUnavail(address)
      ? `<div class="ln-addr">${this._esc(address)}</div>
         <div class="qr-wrap">
           <img class="qr" src="https://api.qrserver.com/v1/create-qr-code/?data=lightning:${encodeURIComponent(address)}&size=240x240&margin=8" alt="Address QR">
         </div>`
      : `<div class="muted">${t('lnAddressUnavail')}</div>`;

    return `<div class="cards-grid">
      <div class="card">
        <div class="card-title">${t('createInvoice')}</div>
        <div class="field">
          <label>${t('amount')}</label>
          <input type="number" class="inp" id="inv-amount" min="0" value="${this._esc(amount)}"
            data-entity="${this._esc(this._eid('invoiceAmount', p))}">
        </div>
        <div class="field">
          <label>${t('unit')}</label>
          <select class="inp" id="inv-unit" data-entity="${this._esc(this._eid('invoiceAmountUnit', p))}">${opts}</select>
        </div>
        <div class="field">
          <label>${t('purpose')}</label>
          <input type="text" class="inp" id="inv-memo" value="${this._esc(memo)}">
        </div>
        <button class="btn" id="create-inv-btn" data-prefix="${this._esc(p)}">${t('btn')}</button>
      </div>

      <div class="card">
        <div class="card-title">${t('invoiceTitle')}</div>
        ${invoiceBlock}
      </div>

      <div class="card">
        <div class="card-title">${t('lnAddressTitle')}</div>
        ${this._row('📧', this._t('overview.lightningAddress'), this._esc(address), false, true)}
      </div>

      <div class="card">
        <div class="card-title">${t('lnAddressQrTitle')}</div>
        ${addrBlock}
      </div>

      <div class="card">
        <div class="card-title">${t('balanceTitle')}</div>
        ${this._row('⚡', this._t('overview.lightning'), `${lightning.toLocaleString()} sat`)}
        ${this._row('₿', this._t('overview.onchain'),  `${onchain.toLocaleString()} sat`)}
      </div>
    </div>
    ${this._buildAutoExamplesCard('receive')}
    ${this._buildAutoBuilderCard()}
    `;
  }

  // ── Tab: Send ────────────────────────────────────────────────────────────────

  _tabSend(p) {
    const t        = (k) => this._t(`send.${k}`);
    // Prefer pending (user-typed) value; fall back to entity state
    const safeInput  = this._pendingPayInput  || ((() => {
      const raw = this._val(this._eid('invoiceInput', p), '');
      return this._isUnavail(raw) ? '' : raw;
    })());
    const lightning  = this._num(this._eid('lightningBalance', p));
    const onchain    = this._num(this._eid('onChainBalance', p));
    const payAmountRaw = this._pendingPayAmount || this._val(this._eid('invoiceAmount', p), '0');
    const payUnit    = this._pendingPayUnit   || this._val(this._eid('invoiceAmountUnit', p), 'SAT');
    const payAmount  = this._displayAmountValue(payAmountRaw, payUnit);
    const payMemo    = this._pendingPayMemo || '';
    const options    = this._attr(this._eid('invoiceAmountUnit', p), 'options', ['SAT', 'BTC']);
    const opts = Array.isArray(options)
      ? options
          .map((o) => `<option value="${this._esc(o)}"${o === payUnit ? ' selected' : ''}>${this._esc(o)}</option>`)
          .join('')
      : `<option value="SAT"${payUnit === 'SAT' ? ' selected' : ''}>SAT</option>
         <option value="BTC"${payUnit === 'BTC' ? ' selected' : ''}>BTC</option>`;

    return `<div class="cards-grid">
      <div class="card">
        <div class="card-title">${t('paymentTitle')}</div>
        <div class="field">
          <label>${t('invoice')}</label>
          <input type="text" class="inp mono" id="inv-input" placeholder="${t('invoicePlaceholder')}"
            value="${this._esc(safeInput)}"
            data-prefix="${this._esc(p)}">
        </div>
        <div class="field">
          <label>${t('amountTitle')}</label>
          <div style="display:flex;gap:6px">
            <input type="number" class="inp" id="pay-amount" min="0" value="${this._esc(payAmount)}"
              data-entity="${this._esc(this._eid('invoiceAmount', p))}" style="flex:1">
            <select class="inp" id="pay-unit" data-entity="${this._esc(this._eid('invoiceAmountUnit', p))}" style="flex:0 0 90px">${opts}</select>
          </div>
        </div>
        <div class="field">
          <label>${t('purpose')}</label>
          <input type="text" class="inp" id="pay-memo" value="${this._esc(payMemo)}">
        </div>
      </div>

      <div class="card">
        <div class="card-title">${t('howTitle')}</div>
        <p>${t('how1')}</p>
        <p>${t('how2')}</p>
        <p>${t('how3')}</p>
      </div>

      <div class="card send-card">
        <button class="btn send-btn" id="send-btn" data-prefix="${this._esc(p)}">${t('sendBtn')}</button>
      </div>

      <div class="card">
        <div class="card-title">${t('balanceTitle')}</div>
        ${this._row('⚡', this._t('overview.lightning'), `${lightning.toLocaleString()} sat`)}
        ${this._row('₿', this._t('overview.onchain'),  `${onchain.toLocaleString()} sat`)}
      </div>
    </div>
    ${this._buildCameraScanCard()}
    ${this._buildAutoExamplesCard('send')}
    ${this._buildAutoBuilderCard()}
    `;
  }

  // ── Tab: Budget ──────────────────────────────────────────────────────────────

  _tabBudget(p) {
    const t         = (k) => this._t(`budget.${k}`);
    const total     = this._num(this._eid('nwcBudgetTotal', p));
    const used      = this._num(this._eid('nwcBudgetUsed', p));
    const remaining = this._num(this._eid('nwcBudgetRemaining', p));
    const renewal   = this._val(this._eid('nwcBudgetRenewal', p));

    let usageBlock;
    if (total > 0) {
      const pctUsed = ((used / total) * 100).toFixed(1);
      const pctRem  = ((remaining / total) * 100).toFixed(1);
      const dot     = parseFloat(pctUsed) >= 90 ? '🔴'
                    : parseFloat(pctUsed) >= 70 ? '🟠'
                    : parseFloat(pctUsed) >= 50 ? '🟡' : '🟢';
      usageBlock = `
        <div class="budget-row">${dot} <b>${pctUsed}% ${t('used')}</b> (${used.toLocaleString()} / ${total.toLocaleString()} sat)</div>
        <div class="prog-bar"><div class="prog-fill" style="width:${Math.min(100, parseFloat(pctUsed))}%"></div></div>
        <div class="muted">${t('remaining')}: <b>${remaining.toLocaleString()} sat</b> (${pctRem}%)</div>
        <div class="muted">${t('renewal')}: <b>${this._esc(renewal)}</b></div>`;
    } else {
      usageBlock = `<div class="muted"><em>${t('noBudget')}</em></div>`;
    }

    return `<div class="cards-grid">
      <div class="card">
        <div class="card-title">${t('usageTitle')}</div>
        ${usageBlock}
        <div class="card-title" style="margin-top:14px">${t('limitsTitle')}</div>
        ${this._row('💰', t('totalBudget'),     `${total.toLocaleString()} sat`)}
        ${this._row('💸', t('usedBudget'),      `${used.toLocaleString()} sat`)}
        ${this._row('💵', t('remainingBudget'), `${remaining.toLocaleString()} sat`)}
        ${this._row('🔄', t('renewalPeriod'),    this._esc(renewal))}
      </div>

      <div class="card">
        <div class="card-title">${t('aboutTitle')}</div>
        <p>${t('about')}</p>
        <ul>
          <li>${t('aboutTotal')}</li>
          <li>${t('aboutUsed')}</li>
          <li>${t('aboutRemaining')}</li>
          <li>${t('aboutRenewal')}</li>
        </ul>
        <p class="muted"><em>${t('aboutUnavail')}</em></p>
      </div>
    </div>`;
  }

  // ── Tab: Network ─────────────────────────────────────────────────────────────

  _tabNetwork(p) {
    const t        = (k) => this._t(`network.${k}`);
    const price    = this._val(this._eid('bitcoinPrice', p));
    const currency = this._attr(this._eid('bitcoinPrice', p), 'unit_of_measurement', '');
    const blockH   = this._val(this._eid('bitcoinBlockHeight', p));
    const hashrate = this._val(this._eid('bitcoinHashrate', p));
    const blocks   = this._num(this._eid('blocksUntilHalving', p));
    const halvEta  = this._val(this._eid('nextHalvingEstimate', p));

    let halvingBlock;
    if (blocks > 0) {
      let etaStr = halvEta;
      try { etaStr = new Date(halvEta).toLocaleString(); } catch (_) { /* keep raw */ }
      halvingBlock = `
        <p>⛏️ <b>${blocks.toLocaleString()} ${t('halvingBlocks')}</b></p>
        <p>📅 ${t('halvingDate')}: <b>${this._esc(etaStr)}</b></p>`;
    } else {
      halvingBlock = `<p class="muted"><em>${t('halvingUnavail')}</em></p>`;
    }

    return `<div class="cards-grid">
      <div class="card">
        <div class="card-title">${t('marketTitle')}</div>
        ${this._row('💵', `${t('btcPrice')} (${this._esc(currency)})`, this._esc(price))}
        ${this._row('🧱', t('blockHeight'),        this._esc(blockH))}
        ${this._row('⚡', t('hashrate'),             this._esc(hashrate))}
        ${this._row('⛏️', t('blocksUntilHalving'), blocks > 0 ? blocks.toLocaleString() : this._esc(String(blocks)))}
        ${this._row('📅', t('nextHalving'), this._esc(halvEta))}
      </div>

      <div class="card">
        <div class="card-title">${t('halvingTitle')}</div>
        ${halvingBlock}
      </div>
    </div>`;
  }

  // ── Tab: Activity ─────────────────────────────────────────────────────────────

  _tabActivity(p) {
    const t = (k) => this._t(`activity.${k}`);

    // Load transactions on first render of this tab
    if (this._transactions === null && !this._txLoading) {
      this._loadTransactions(p);
      return `<div class="cards-grid"><div class="card"><p class="muted">${t('loading')}</p></div></div>`;
    }

    const txs = (this._transactions || []).filter((tx) => {
      if (this._txFilter === 'incoming') return tx.type === 'incoming';
      if (this._txFilter === 'outgoing') return tx.type === 'outgoing';
      return true;
    });

    const filterBar = `<div class="filter-bar">
      <button class="filter-btn${this._txFilter === 'all'      ? ' active' : ''}" data-filter="all">${t('filterAll')}</button>
      <button class="filter-btn${this._txFilter === 'incoming' ? ' active' : ''}" data-filter="incoming">${t('filterIn')}</button>
      <button class="filter-btn${this._txFilter === 'outgoing' ? ' active' : ''}" data-filter="outgoing">${t('filterOut')}</button>
      <button class="filter-btn refresh-btn" data-action="refresh-tx" style="margin-left:auto">${t('refresh')}</button>
    </div>`;

    const rows = txs.length === 0
      ? `<tr><td colspan="5" class="muted" style="text-align:center;padding:16px">${t('noTx')}</td></tr>`
      : txs.map((tx) => {
          const sign   = tx.type === 'incoming' ? '+' : '−';
          const color  = tx.type === 'incoming' ? '#4caf50' : '#f44336';
          const typeLabel = tx.type === 'incoming' ? t('typeIn') : t('typeOut');
          const dateStr = tx.settled_at
            ? new Date(tx.settled_at * 1000).toLocaleString()
            : (tx.settled ? '' : t('pending'));
          return `<tr>
            <td>${typeLabel}</td>
            <td style="text-align:right;color:${color};font-weight:600">${sign}${tx.amount_sat.toLocaleString()}</td>
            <td style="text-align:right;color:var(--secondary-text-color,#aaa)">${tx.fees_sat > 0 ? tx.fees_sat.toLocaleString() : '—'}</td>
            <td class="small">${this._esc(tx.description || '—')}</td>
            <td class="small muted">${this._esc(dateStr)}</td>
          </tr>`;
        }).join('');

    return `<div class="cards-grid" style="grid-template-columns:1fr">
      <div class="card">
        <div class="card-title">${t('title')}</div>
        ${filterBar}
        <div class="tx-scroll">
          <table class="tx-table">
            <thead>
              <tr>
                <th>${t('colType')}</th>
                <th style="text-align:right">${t('colAmount')}</th>
                <th style="text-align:right">${t('colFee')}</th>
                <th>${t('colDesc')}</th>
                <th>${t('colDate')}</th>
              </tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      </div>
    </div>`;
  }

  // ── Tab: Scheduled Payments ────────────────────────────────────────────────

  _tabScheduled(p) {
    const t  = (k) => this._t(`scheduled.${k}`);
    const f  = this._schedForm;
    if (!f.start_date) {
      f.start_date = this._todayIso();
    }
    const DAYS = [t('dow0'), t('dow1'), t('dow2'), t('dow3'), t('dow4'), t('dow5'), t('dow6')];

    // Load schedules on first render
    if (this._schedules === null && !this._schedLoading) {
      this._loadSchedules(p);
      return `<div class="cards-grid"><div class="card"><p class="muted">${this._t('activity.loading')}</p></div></div>`;
    }

    // ── Create form ──────────────────────────────────────────────────────────
    const showDayOfWeek  = f.frequency === 'weekly';
    const showDayOfMonth = f.frequency === 'monthly' || f.frequency === 'quarterly';
    const isEditing = Boolean(this._schedEditId);
    const submitLabel = isEditing ? t('updateBtn') : t('createBtn');

    const createForm = `<div class="card">
      <div class="card-title">${t('newTitle')}</div>

      <div class="field">
        <label>${t('label')}</label>
        <input type="text" class="inp" id="sched-label" placeholder="${t('labelPlaceholder')}" value="${this._esc(f.label)}">
      </div>
      <div class="field">
        <label>${t('recipient')}</label>
        <input type="text" class="inp" id="sched-recipient" placeholder="${t('recipientPlaceholder')}" value="${this._esc(f.recipient)}">
      </div>
      <div class="field">
        <label>${t('amount')}</label>
        <input type="number" class="inp" id="sched-amount" min="1" step="1" value="${this._esc(f.amount)}">
      </div>
      <div class="field">
        <label>${t('memo')}</label>
        <input type="text" class="inp" id="sched-memo" value="${this._esc(f.memo)}">
      </div>
      <div class="field">
        <label>${t('frequency')}</label>
        <select class="inp" id="sched-freq">
          <option value="daily"     ${f.frequency === 'daily'     ? 'selected' : ''}>${t('freqDaily')}</option>
          <option value="weekly"    ${f.frequency === 'weekly'    ? 'selected' : ''}>${t('freqWeekly')}</option>
          <option value="monthly"   ${f.frequency === 'monthly'   ? 'selected' : ''}>${t('freqMonthly')}</option>
          <option value="quarterly" ${f.frequency === 'quarterly' ? 'selected' : ''}>${t('freqQuarterly')}</option>
        </select>
      </div>
      <div class="field" style="display:flex;gap:8px">
        <div style="flex:1">
          <label>${t('time')}</label>
          <div style="display:flex;gap:4px">
            <input type="number" class="inp" id="sched-hour"   min="0" max="23" value="${this._esc(f.hour)}"   style="width:60px">
            <span style="align-self:center">:</span>
            <input type="number" class="inp" id="sched-minute" min="0" max="59" value="${this._esc(f.minute)}" style="width:60px">
          </div>
        </div>
        ${showDayOfWeek ? `<div style="flex:1">
          <label>${t('dayOfWeek')}</label>
          <select class="inp" id="sched-dow">
            ${DAYS.map((d, i) => `<option value="${i}" ${f.day_of_week === String(i) ? 'selected' : ''}>${d}</option>`).join('')}
          </select>
        </div>` : ''}
        ${showDayOfMonth ? `<div style="flex:1">
          <label>${t('dayOfMonth')}</label>
          <input type="number" class="inp" id="sched-dom" min="1" max="28" value="${this._esc(f.day_of_month)}">
        </div>` : ''}
      </div>
      <div class="field" style="display:flex;gap:8px">
        <div style="flex:1">
          <label>${t('startDate')}</label>
          <input type="date" class="inp" id="sched-start" value="${this._esc(f.start_date)}">
        </div>
        <div style="flex:1">
          <label>${t('endDate')}</label>
          <input type="date" class="inp" id="sched-end" value="${this._esc(f.end_date)}">
        </div>
      </div>
      <button class="btn" id="sched-create-btn" data-prefix="${this._esc(p)}">${submitLabel}</button>
      ${isEditing ? `<button class="filter-btn" id="sched-cancel-edit-btn" style="margin-top:8px;width:100%">${t('cancelEditBtn')}</button>` : ''}
    </div>`;

    // ── Schedule list ────────────────────────────────────────────────────────
    const schedules = this._schedules || [];
    // Each header entry: { label, style? }
    const scheduleHeaders = [
      { label: t('colLabel') },
      { label: t('colRecipient') },
      { label: t('colAmount'), style: 'text-align:right' },
      { label: t('colFreq') },
      { label: t('colNext') },
      { label: t('colLastRun') },
    ];
    // One extra column is reserved for row action buttons (edit/run/delete).
    const scheduleColumnCount = scheduleHeaders.length + 1;
    const schedRows = schedules.length === 0
      ? `<tr><td colspan="${scheduleColumnCount}" class="muted" style="text-align:center;padding:16px">${t('noSchedules')}</td></tr>`
      : schedules.map((s) => {
          const lastRun = s.last_run
            ? new Date(s.last_run).toLocaleString()
            : t('never');
          const nextRun = s.next_run
            ? new Date(s.next_run).toLocaleString()
            : '—';
          const freqLabel = ({daily: t('freqDaily'), weekly: t('freqWeekly'), monthly: t('freqMonthly'), quarterly: t('freqQuarterly')})[s.frequency] || s.frequency;
          return `<tr>
            <td>${this._esc(s.label || '—')}</td>
            <td class="small">${this._esc(s.recipient.length > 30 ? s.recipient.slice(0, 28) + '…' : s.recipient)}</td>
            <td style="text-align:right">${s.amount_sat.toLocaleString()}</td>
            <td>${freqLabel}</td>
            <td class="small muted">${this._esc(nextRun)}</td>
            <td class="small muted">${this._esc(lastRun)}</td>
            <td style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">
              <button class="sched-edit-btn small-btn" data-id="${this._esc(s.id)}">${t('editBtn')}</button>
              <button class="sched-run-btn small-btn" data-id="${this._esc(s.id)}">${t('runNowBtn')}</button>
              <button class="sched-del-btn small-btn" data-id="${this._esc(s.id)}">${t('deleteBtn')}</button>
            </td>
          </tr>`;
        }).join('');

    const listCard = `<div class="card">
      <div class="card-title" style="display:flex;align-items:center;gap:8px">
        ${t('listTitle')}
        <button class="filter-btn" style="margin-left:auto" data-action="refresh-sched">${t('refresh')}</button>
      </div>
      <div class="tx-scroll">
        <table class="tx-table">
          <thead>
            <tr>
              ${scheduleHeaders.map((h) => `<th${h.style ? ` style="${h.style}"` : ''}>${h.label}</th>`).join('')}
              <th aria-label="${this._t('scheduled.deleteBtn')}"></th>
            </tr>
          </thead>
          <tbody>${schedRows}</tbody>
        </table>
      </div>
    </div>`;

    return `<div class="cards-grid" style="grid-template-columns:repeat(auto-fill,minmax(400px,1fr))">
      ${createForm}
      ${listCard}
    </div>`;
  }

  // ── Row helper ───────────────────────────────────────────────────────────────

  _row(icon, name, value, rawHtml = false, small = false) {
    const valHtml = rawHtml ? value : this._esc(value);
    return `<div class="row">
      <span class="row-icon">${icon}</span>
      <span class="row-name">${this._esc(name)}</span>
      <span class="row-val${small ? ' small' : ''}">${valHtml}</span>
    </div>`;
  }

  // ── Camera entity helper ────────────────────────────────────────────────────

  _getCameraEntities() {
    return Object.keys(this._hass?.states || {})
      .filter((id) => id.startsWith('camera.'))
      .sort();
  }

  // ── Camera scan card ─────────────────────────────────────────────────────────

  _buildCameraScanCard() {
    const t = (k) => this._t(`camera.${k}`);
    const cameras = this._getCameraEntities();
    const cameraOptions = cameras
      .map((id) => `<option value="${this._esc(id)}"${id === this._cameraEntitySel ? ' selected' : ''}>${this._esc(id)}</option>`)
      .join('');
    const hasBarcodeApi = typeof BarcodeDetector !== 'undefined';

    return `<div class="card">
      <div class="card-title">${t('title')}</div>
      <p class="muted" style="font-size:0.8rem">${t('hint')}</p>
      ${!hasBarcodeApi ? `<p class="muted" style="font-size:0.75rem;background:rgba(255,165,0,.1);padding:6px 10px;border-radius:6px;margin-bottom:8px">${t('noBarcodeApiHint')}</p>` : ''}
      ${cameras.length > 0 ? `<div class="field">
        <label>${t('selectEntity')}</label>
        <select class="inp" id="camera-entity-sel">
          <option value="">${t('noCamera')}</option>
          ${cameraOptions}
        </select>
        <button class="filter-btn" id="scan-entity-btn" style="margin-top:6px;width:100%">${t('scanEntityBtn')}</button>
      </div>` : ''}
      <div class="field" style="display:flex;gap:6px;flex-wrap:wrap;margin-top:4px">
        <button class="filter-btn${this._cameraScanning ? ' active' : ''}" id="scan-device-btn" style="flex:1">${this._cameraScanning ? t('stopBtn') : t('deviceCameraBtn')}</button>
        <label class="filter-btn" for="scan-file-input" style="flex:1;text-align:center;cursor:pointer;display:flex;align-items:center;justify-content:center">${t('fileInputBtn')}</label>
        <input type="file" id="scan-file-input" accept="image/*" capture="environment" style="position:absolute;opacity:0;width:0;height:0">
      </div>
      ${this._cameraScanning ? `<video id="camera-video" autoplay playsinline muted style="width:100%;border-radius:8px;margin-top:8px;max-height:220px;object-fit:cover;background:#000"></video>` : ''}
      ${this._cameraScanMsg ? `<p class="muted" style="margin-top:6px;font-size:0.82rem">${this._esc(this._cameraScanMsg)}</p>` : ''}
      <p class="muted" style="font-size:0.73rem;margin-top:8px">${t('companionHint')}</p>
    </div>`;
  }

  // ── Automation examples card ─────────────────────────────────────────────────

  _buildAutoExamplesCard(direction) {
    const t = (k) => this._t(`autoExamples.${k}`);
    const lang = (this._hass?.language || 'en').split('-')[0].toLowerCase();
    const isDE = lang === 'de';
    const title = direction === 'receive' ? t('receiveTitle') : t('sendTitle');

    const examples = direction === 'receive' ? [
      {
        desc: isDE
          ? 'Wenn eine Zahlung empfangen wird → Benachrichtigung senden'
          : 'When a payment is received → send notification',
        yaml: [
          `alias: "${isDE ? 'Alby Hub – Zahlung empfangen, Benachrichtigung' : 'Alby Hub – Payment received, notify'}"`,
          `description: >`,
          `  ${isDE ? 'Sendet eine Benachrichtigung wenn die Lightning-Balance steigt.' : 'Sends a notification when the Lightning balance increases.'}`,
          `trigger:`,
          `  - platform: state`,
          `    entity_id: sensor.alby_hub_lightning_balance`,
          `condition:`,
          `  - condition: template`,
          `    value_template: >`,
          `      {{ trigger.to_state.state | int(0) >`,
          `         trigger.from_state.state | int(0) }}`,
          `action:`,
          `  - service: notify.notify`,
          `    data:`,
          `      message: >`,
          `        ${isDE ? '⚡ Zahlung empfangen!' : '⚡ Payment received!'}`,
          `        ${isDE ? 'Neue Balance' : 'New balance'}: {{ states('sensor.alby_hub_lightning_balance') }} sat`,
          `mode: single`,
        ].join('\n'),
      },
      {
        desc: isDE
          ? 'Wenn eine Zahlung empfangen wird → Schalter einschalten'
          : 'When a payment is received → turn on a switch',
        yaml: [
          `alias: "${isDE ? 'Alby Hub – Zahlung empfangen, Zugang freischalten' : 'Alby Hub – Payment received, grant access'}"`,
          `description: >`,
          `  ${isDE ? 'Ersetze switch.beispiel_zugang durch deine Ziel-Entität.' : 'Replace switch.example_access with your target entity.'}`,
          `trigger:`,
          `  - platform: state`,
          `    entity_id: sensor.alby_hub_lightning_balance`,
          `condition:`,
          `  - condition: template`,
          `    value_template: >`,
          `      {{ trigger.to_state.state | int(0) >`,
          `         trigger.from_state.state | int(0) }}`,
          `action:`,
          `  - service: switch.turn_on`,
          `    target:`,
          `      entity_id: ${isDE ? 'switch.beispiel_zugang' : 'switch.example_access'}`,
          `mode: single`,
        ].join('\n'),
      },
    ] : [
      {
        desc: isDE
          ? 'Wenn ein Schalter eingeschaltet wird → Lightning-Zahlung senden'
          : 'When a switch is turned on → send Lightning payment',
        yaml: [
          `alias: "${isDE ? 'Alby Hub – Schalter → Zahlung auslösen' : 'Alby Hub – Switch → trigger payment'}"`,
          `description: >`,
          `  ${isDE ? 'Ersetze switch.zahlungs_schalter, Empfänger und Betrag.' : 'Replace switch.payment_trigger, recipient, and amount.'}`,
          `trigger:`,
          `  - platform: state`,
          `    entity_id: ${isDE ? 'switch.zahlungs_schalter' : 'switch.payment_trigger'}`,
          `    to: "on"`,
          `action:`,
          `  - service: alby_hub.send_payment`,
          `    data:`,
          `      payment_request: "recipient@lightning.address"`,
          `      amount_sat: 1000`,
          `      memo: "${isDE ? 'Automatische Zahlung von HA' : 'Automatic payment from HA'}"`,
          `mode: single`,
        ].join('\n'),
      },
      {
        desc: isDE
          ? 'Wenn ein Sensor-Grenzwert überschritten wird → Lightning-Zahlung senden'
          : 'When a sensor threshold is exceeded → send Lightning payment',
        yaml: [
          `alias: "${isDE ? 'Alby Hub – Grenzwert → Zahlung' : 'Alby Hub – Threshold → payment'}"`,
          `description: >`,
          `  ${isDE ? 'Ersetze Sensor-ID, Grenzwert, Empfänger und Betrag.' : 'Replace sensor ID, threshold, recipient, and amount.'}`,
          `trigger:`,
          `  - platform: numeric_state`,
          `    entity_id: ${isDE ? 'sensor.beispiel_sensor' : 'sensor.example_sensor'}`,
          `    above: 100`,
          `action:`,
          `  - service: alby_hub.send_payment`,
          `    data:`,
          `      payment_request: "recipient@lightning.address"`,
          `      amount_sat: 5000`,
          `      memo: "${isDE ? 'Abrechnung' : 'Billing'} {{ now().strftime('%Y-%m-%d') }}"`,
          `mode: single`,
        ].join('\n'),
      },
    ];

    if (!this._autoExamplesStore) this._autoExamplesStore = {};
    this._autoExamplesStore[direction] = examples;

    const cards = examples.map((ex, idx) => `
      <div class="auto-example">
        <div class="auto-example-desc">${this._esc(ex.desc)}</div>
        <pre class="auto-yaml"><code>${this._esc(ex.yaml)}</code></pre>
        <button class="filter-btn copy-example-btn" data-direction="${direction}" data-idx="${idx}">${t('copy')}</button>
      </div>`).join('');

    return `<div class="card">
      <div class="card-title">${title}</div>
      <p class="muted" style="font-size:0.8rem">${t('intro')}</p>
      ${cards}
    </div>`;
  }

  // ── Automation builder card ───────────────────────────────────────────────────

  _buildAutoBuilderCard() {
    const t   = (k) => this._t(`autoBuilder.${k}`);
    const f   = this._autoForm;
    const isSend    = f.direction === 'send';
    const isStateOn = f.triggerType === 'state_on';
    const isAbove   = f.triggerType === 'thresh_above';
    const isBelow   = f.triggerType === 'thresh_below';
    const isPayment = f.actionType === 'send_payment';
    const isNotify  = f.actionType === 'notify';

    const triggerFields = isSend ? `
      <div class="field">
        <label>${t('triggerType')}</label>
        <select class="inp" id="ab-trig-type">
          <option value="state_on"     ${isStateOn ? 'selected' : ''}>${t('trigStateOn')}</option>
          <option value="thresh_above" ${isAbove   ? 'selected' : ''}>${t('trigThreshAbove')}</option>
          <option value="thresh_below" ${isBelow   ? 'selected' : ''}>${t('trigThreshBelow')}</option>
        </select>
      </div>
      <div class="field">
        <label>${t('trigEntityId')}</label>
        <input type="text" class="inp" id="ab-trig-entity" placeholder="${isStateOn ? 'switch.your_switch' : 'sensor.your_sensor'}" value="${this._esc(f.trigEntityId)}">
      </div>
      ${!isStateOn ? `<div class="field">
        <label>${t('trigThreshold')}</label>
        <input type="number" class="inp" id="ab-threshold" value="${this._esc(f.threshold)}">
      </div>` : ''}
    ` : `
      <div class="field">
        <label>${t('triggerType')}</label>
        <select class="inp" id="ab-trig-type" disabled>
          <option value="balance_increase" selected>${t('trigBalanceIncrease')}</option>
        </select>
      </div>
    `;

    const actionFields = `
      <div class="field">
        <label>${t('actionType')}</label>
        <select class="inp" id="ab-action-type">
          ${isSend ? `<option value="send_payment" ${isPayment ? 'selected' : ''}>${t('actSendPayment')}</option>` : ''}
          <option value="turn_on"  ${f.actionType === 'turn_on'  ? 'selected' : ''}>${t('actTurnOn')}</option>
          <option value="turn_off" ${f.actionType === 'turn_off' ? 'selected' : ''}>${t('actTurnOff')}</option>
          <option value="notify"   ${isNotify ? 'selected' : ''}>${t('actNotify')}</option>
        </select>
      </div>
      ${isPayment && isSend ? `
        <div class="field">
          <label>${t('recipient')}</label>
          <input type="text" class="inp" id="ab-recipient" placeholder="user@lightning.address" value="${this._esc(f.recipient)}">
        </div>
        <div class="field" style="display:flex;gap:6px">
          <div style="flex:1">
            <label>${t('amountSat')}</label>
            <input type="number" class="inp" id="ab-amount" min="1" value="${this._esc(f.amountSat)}">
          </div>
        </div>
        <div class="field">
          <label>${t('memo')}</label>
          <input type="text" class="inp" id="ab-memo" value="${this._esc(f.memo)}">
        </div>
      ` : ''}
      ${(f.actionType === 'turn_on' || f.actionType === 'turn_off') ? `
        <div class="field">
          <label>${t('targetEntityId')}</label>
          <input type="text" class="inp" id="ab-target-entity" placeholder="switch.your_entity" value="${this._esc(f.targetEntityId)}">
        </div>
      ` : ''}
      ${isNotify ? `
        <div class="field">
          <label>${t('notifyMsg')}</label>
          <input type="text" class="inp" id="ab-notify-msg" value="${this._esc(f.notifyMsg)}">
        </div>
      ` : ''}
    `;

    const yamlBlock = this._autoYaml
      ? `<pre class="auto-yaml" style="margin-top:10px"><code>${this._esc(this._autoYaml)}</code></pre>
         <button class="filter-btn" id="ab-copy-btn" style="margin-top:6px;width:100%">${t('copyBtn')}</button>`
      : `<p class="muted" style="font-size:0.8rem;margin-top:8px">${t('placeholder')}</p>`;

    return `<div class="card">
      <div class="card-title">${t('title')}</div>
      <p class="muted" style="font-size:0.8rem">${t('intro')}</p>
      <div class="field">
        <label>${t('direction')}</label>
        <select class="inp" id="ab-direction">
          <option value="send"    ${f.direction === 'send'    ? 'selected' : ''}>${t('dirSend')}</option>
          <option value="receive" ${f.direction === 'receive' ? 'selected' : ''}>${t('dirReceive')}</option>
        </select>
      </div>
      ${triggerFields}
      ${actionFields}
      <button class="btn" id="ab-generate-btn" style="margin-top:4px">${t('generateBtn')}</button>
      ${yamlBlock}
      <p class="muted" style="font-size:0.73rem;margin-top:10px">${t('haHint')}</p>
    </div>`;
  }

  _generateAutomationYaml() {
    const f    = this._autoForm;
    const lang = (this._hass?.language || 'en').split('-')[0].toLowerCase();
    const isDE = lang === 'de';
    const isSend = f.direction === 'send';

    let triggerAndCondition = '';
    if (f.triggerType === 'state_on') {
      triggerAndCondition = `trigger:\n  - platform: state\n    entity_id: ${f.trigEntityId || 'switch.your_switch'}\n    to: "on"`;
    } else if (f.triggerType === 'thresh_above') {
      triggerAndCondition = `trigger:\n  - platform: numeric_state\n    entity_id: ${f.trigEntityId || 'sensor.your_sensor'}\n    above: ${f.threshold || '100'}`;
    } else if (f.triggerType === 'thresh_below') {
      triggerAndCondition = `trigger:\n  - platform: numeric_state\n    entity_id: ${f.trigEntityId || 'sensor.your_sensor'}\n    below: ${f.threshold || '100'}`;
    } else {
      triggerAndCondition = `trigger:\n  - platform: state\n    entity_id: sensor.alby_hub_lightning_balance\ncondition:\n  - condition: template\n    value_template: >\n      {{ trigger.to_state.state | int(0) >\n         trigger.from_state.state | int(0) }}`;
    }

    let action = '';
    if (f.actionType === 'send_payment') {
      const memoLine = f.memo ? `\n      memo: "${f.memo}"` : '';
      action = `action:\n  - service: alby_hub.send_payment\n    data:\n      payment_request: "${f.recipient || 'recipient@lightning.address'}"\n      amount_sat: ${f.amountSat || '1000'}${memoLine}`;
    } else if (f.actionType === 'turn_on') {
      action = `action:\n  - service: switch.turn_on\n    target:\n      entity_id: ${f.targetEntityId || 'switch.your_entity'}`;
    } else if (f.actionType === 'turn_off') {
      action = `action:\n  - service: switch.turn_off\n    target:\n      entity_id: ${f.targetEntityId || 'switch.your_entity'}`;
    } else {
      const msg = f.notifyMsg || (isDE ? '⚡ Zahlung empfangen!' : '⚡ Payment received!');
      action = `action:\n  - service: notify.notify\n    data:\n      message: "${msg}"`;
    }

    const aliasStr = isSend
      ? (isDE ? 'Alby Hub – Zahlung auslösen' : 'Alby Hub – Trigger payment')
      : (isDE ? 'Alby Hub – Auf Zahlung reagieren' : 'Alby Hub – React to payment');

    return `alias: "${aliasStr}"\n${triggerAndCondition}\n${action}\nmode: single`;
  }

  // ── Data loaders for async tabs ──────────────────────────────────────────────

  _loadTransactions(p) {
    if (this._txLoading) return;
    this._txLoading = true;
    const serviceData = {};
    const entry = this._resolveEntryId(p);
    if (entry) serviceData.config_entry_id = entry;
    this._hass.callService('alby_hub', 'list_transactions', serviceData, undefined, true, true)
      .then((resp) => {
        const data = resp?.response ?? resp;
        this._transactions = Array.isArray(data?.transactions) ? data.transactions : [];
        this._txLoading = false;
        this._updateContent();
      })
      .catch(() => {
        this._transactions = [];
        this._txLoading = false;
        this._updateContent();
      });
  }

  _loadSchedules(p) {
    if (this._schedLoading) return;
    this._schedLoading = true;
    const serviceData = {};
    const entry = this._resolveEntryId(p);
    if (entry) serviceData.config_entry_id = entry;
    this._hass.callService('alby_hub', 'list_scheduled_payments', serviceData, undefined, true, true)
      .then((resp) => {
        const data = resp?.response ?? resp;
        this._schedules = Array.isArray(data?.schedules) ? data.schedules : [];
        this._schedLoading = false;
        this._updateContent();
      })
      .catch(() => {
        this._schedules = [];
        this._schedLoading = false;
        this._updateContent();
      });
  }

  /** Resolve a config entry ID from a known entity prefix (best-effort). */
  _resolveEntryId(_prefix) {
    // The panel doesn't have direct access to config entry IDs from hass.states;
    // pass undefined and let the backend pick the first available runtime.
    return undefined;
  }

  // ── Menu button ──────────────────────────────────────────────────────────────

  _applyMenuBtn() {
    const btn = this.shadowRoot.querySelector('ha-menu-button');
    if (btn) {
      btn.hass   = this._hass;
      btn.narrow = this._narrow;
    }
  }

  // ── Camera stream cleanup helper ─────────────────────────────────────────────

  _stopCameraStream() {
    if (this._cameraStream) {
      this._cameraStream.getTracks().forEach((t) => t.stop());
      this._cameraStream = null;
    }
    this._cameraScanning = false;
    this._cameraScanMsg = '';
  }

  // ── Event listeners ──────────────────────────────────────────────────────────

  _attachListeners() {
    const root = this.shadowRoot;

    // Instance tab clicks
    root.querySelectorAll('.instance-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        this._activePrefix = btn.dataset.prefix;
        this._render();
      });
    });

    // Navigation tab clicks
    root.querySelectorAll('.tab-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const prevTab = this._activeTab;
        this._activeTab = btn.dataset.tab;
        // Stop camera when leaving the Send tab
        if (prevTab === 'send' && this._cameraStream) {
          this._stopCameraStream();
        }
        // Reset loaded data when navigating to async tabs so fresh data is loaded
        if (this._activeTab === 'activity' && prevTab !== 'activity') {
          this._transactions = null;
          this._txLoading = false;
        }
        if (this._activeTab === 'scheduled' && prevTab !== 'scheduled') {
          this._schedules = null;
          this._schedLoading = false;
        }
        this._render();
      });
    });

    this._attachContentListeners();
  }

  _attachContentListeners() {
    const root = this.shadowRoot;

    // Invoice amount number input (receive tab) – store locally AND sync to entity
    root.querySelectorAll('#inv-amount').forEach((el) => {
      el.addEventListener('input', () => { this._pendingInvAmount = el.value; });
      el.addEventListener('change', () => {
        this._pendingInvAmount = el.value;
        if (el.dataset.entity) {
          this._hass.callService('number', 'set_value', {
            entity_id: el.dataset.entity,
            value: el.value,
          });
        }
      });
    });

    // Invoice amount unit select (receive tab) – store locally AND sync to entity
    root.querySelectorAll('#inv-unit').forEach((el) => {
      el.addEventListener('change', () => {
        this._pendingInvUnit = el.value;
        if (el.dataset.entity) {
          this._hass.callService('select', 'select_option', {
            entity_id: el.dataset.entity,
            option: el.value,
          });
        }
      });
    });

    root.querySelectorAll('#inv-memo').forEach((el) => {
      el.addEventListener('input',  () => { this._pendingInvMemo = el.value; });
      el.addEventListener('change', () => { this._pendingInvMemo = el.value; });
    });

    // Create invoice button
    root.querySelectorAll('#create-inv-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        if (btn.dataset.prefix) {
          const amountEl = root.querySelector('#inv-amount');
          const unitEl = root.querySelector('#inv-unit');
          const memoEl = root.querySelector('#inv-memo');
          const amountRaw = (this._pendingInvAmount || amountEl?.value || '').trim();
          const unit = (this._pendingInvUnit || unitEl?.value || 'SAT').toUpperCase();
          const memo = (this._pendingInvMemo || memoEl?.value || '').trim();
          const amountNum = parseFloat(amountRaw);
          if (!Number.isFinite(amountNum) || amountNum <= 0) {
            console.warn('Alby Hub panel: invalid invoice amount', amountRaw);
            return;
          }

          const serviceData = {};
          if (unit === 'SAT') {
            serviceData.amount_sat = Math.max(1, Math.floor(amountNum));
          } else if (unit === 'BTC') {
            serviceData.amount_btc = amountNum;
          } else {
            serviceData.amount_fiat = amountNum;
            serviceData.fiat_currency = unit;
          }
          if (memo) serviceData.memo = memo;

          this._hass.callService('alby_hub', 'create_invoice', serviceData, undefined, true, true).then((resp) => {
            const invoiceData = resp?.response ?? resp;
            if (invoiceData?.payment_request) {
              this._lastInvoiceByPrefix[btn.dataset.prefix] = {
                bolt11: invoiceData.payment_request,
                amount_sat: invoiceData.amount_sat,
                memo,
              };
            }
            // Clear pending receive inputs after create (entity will be updated)
            this._pendingInvAmount = '';
            this._pendingInvUnit = '';
            this._pendingInvMemo = '';
            this._hass.callService('homeassistant', 'update_entity', {
              entity_id: [
                this._eid('lastInvoice', btn.dataset.prefix),
                this._eid('lightningBalance', btn.dataset.prefix),
              ],
            }).catch((err) => {
              console.warn('Alby Hub panel: failed to refresh entities after invoice creation', err);
            });
            this._lastUpdate = 0;
            this._updateContent();
          }).catch((err) => {
            console.warn('Alby Hub panel: invoice creation failed', err);
          });
        }
      });
    });

    // Invoice input text field (send tab) – store locally only; do NOT sync to HA
    // entity to avoid the 255-char state limit. The value is passed directly when
    // the send button is pressed.
    root.querySelectorAll('#inv-input').forEach((el) => {
      el.addEventListener('input',  () => { this._pendingPayInput = el.value; });
      el.addEventListener('change', () => { this._pendingPayInput = el.value; });
    });

    // Send amount (send tab) – store locally AND sync to entity
    root.querySelectorAll('#pay-amount').forEach((el) => {
      el.addEventListener('input', () => { this._pendingPayAmount = el.value; });
      el.addEventListener('change', () => {
        this._pendingPayAmount = el.value;
        if (el.dataset.entity) {
          this._hass.callService('number', 'set_value', {
            entity_id: el.dataset.entity,
            value: el.value,
          });
        }
      });
    });

    // Send unit (send tab) – store locally AND sync to entity
    root.querySelectorAll('#pay-unit').forEach((el) => {
      el.addEventListener('change', () => {
        this._pendingPayUnit = el.value;
        if (el.dataset.entity) {
          this._hass.callService('select', 'select_option', {
            entity_id: el.dataset.entity,
            option: el.value,
          });
        }
      });
    });

    root.querySelectorAll('#pay-memo').forEach((el) => {
      el.addEventListener('input',  () => { this._pendingPayMemo = el.value; });
      el.addEventListener('change', () => { this._pendingPayMemo = el.value; });
    });

    // Send payment button – pass payment_request and amount directly to avoid
    // the 255-char text entity state limit
    root.querySelectorAll('#send-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const payInput  = this._pendingPayInput.trim();
        const payAmount = this._pendingPayAmount;
        const payUnit   = this._pendingPayUnit || 'SAT';
        const payMemo   = this._pendingPayMemo.trim();
        const serviceData = {};
        if (payInput) serviceData.payment_request = payInput;
        // Pass amount params if provided and a Lightning address is being used
        if (payAmount && parseFloat(payAmount) > 0) {
          if (payUnit === 'SAT') {
            serviceData.amount_sat = parseInt(payAmount, 10);
          } else if (payUnit === 'BTC') {
            serviceData.amount_btc = parseFloat(payAmount);
          } else {
            serviceData.amount_fiat = parseFloat(payAmount);
            serviceData.fiat_currency = payUnit;
          }
        }
        if (payMemo) serviceData.memo = payMemo;
        this._hass.callService('alby_hub', 'send_payment', serviceData).then(() => {
          // Clear pending values after successful send
          this._pendingPayInput  = '';
          this._pendingPayAmount = '';
          this._pendingPayUnit   = '';
          this._pendingPayMemo   = '';
          // Force re-render
          this._lastUpdate = 0;
          this._updateContent();
        }).catch(() => {});
      });
    });

    // ── Activity tab listeners ────────────────────────────────────────────────

    root.querySelectorAll('.filter-btn[data-filter]').forEach((btn) => {
      btn.addEventListener('click', () => {
        this._txFilter = btn.dataset.filter;
        this._updateContent();
      });
    });

    root.querySelectorAll('[data-action="refresh-tx"]').forEach((btn) => {
      btn.addEventListener('click', () => {
        this._transactions = null;
        this._txLoading = false;
        this._updateContent();
      });
    });

    // ── Scheduled payments tab listeners ─────────────────────────────────────

    root.querySelectorAll('[data-action="refresh-sched"]').forEach((btn) => {
      btn.addEventListener('click', () => {
        this._schedules = null;
        this._schedLoading = false;
        this._updateContent();
      });
    });

    // Live-update the form state when fields change (to show/hide day-of-week/month)
    const bindSchedField = (id, key, rerenderOnChange = false) => {
      const el = root.querySelector(`#${id}`);
      if (el) {
        el.addEventListener('change', () => {
          this._schedForm[key] = el.value;
          if (rerenderOnChange) this._updateContent();
        });
        el.addEventListener('input',  () => { this._schedForm[key] = el.value; });
      }
    };
    bindSchedField('sched-label',     'label');
    bindSchedField('sched-recipient', 'recipient');
    bindSchedField('sched-amount',    'amount');
    bindSchedField('sched-memo',      'memo');
    bindSchedField('sched-freq',      'frequency', true);
    bindSchedField('sched-hour',      'hour');
    bindSchedField('sched-minute',    'minute');
    bindSchedField('sched-dow',       'day_of_week');
    bindSchedField('sched-dom',       'day_of_month');
    bindSchedField('sched-start',     'start_date');
    bindSchedField('sched-end',       'end_date');

    // Create/update schedule button
    root.querySelectorAll('#sched-create-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const f = this._schedForm;
        const t = (k) => this._t(`scheduled.${k}`);
        const amtNum = parseInt(f.amount, 10);
        if (!f.recipient.trim()) { alert(t('errRecipient')); return; }
        if (!Number.isFinite(amtNum) || amtNum < 1) { alert(t('errAmountMin')); return; }

        const serviceData = {
          recipient:    f.recipient.trim(),
          amount_sat:   amtNum,
          label:        f.label.trim(),
          memo:         f.memo.trim(),
          frequency:    f.frequency,
          hour:         parseInt(f.hour, 10),
          minute:       parseInt(f.minute, 10),
          day_of_week:  parseInt(f.day_of_week, 10),
          day_of_month: parseInt(f.day_of_month, 10),
        };
        if (f.start_date) serviceData.start_date = f.start_date;
        if (f.end_date) serviceData.end_date = f.end_date;

        btn.disabled = true;
        const isEditing = Boolean(this._schedEditId);
        if (isEditing) serviceData.schedule_id = this._schedEditId;
        if (isEditing && !f.end_date) serviceData.end_date = null;
        this._hass.callService('alby_hub', isEditing ? 'update_scheduled_payment' : 'schedule_payment', serviceData)
          .then(() => {
            // Reset form and reload list
            this._schedForm = {
              recipient: '', amount: '', label: '', memo: '',
              frequency: 'monthly', hour: '8', minute: '0',
              day_of_week: '0', day_of_month: '1',
              start_date: this._todayIso(), end_date: '',
            };
            this._schedEditId = null;
            this._schedules = null;
            this._schedLoading = false;
            this._updateContent();
          })
          .catch((err) => {
            console.warn('Alby Hub panel: schedule create/update failed', err);
          })
          .finally(() => { btn.disabled = false; });
      });
    });

    root.querySelectorAll('#sched-cancel-edit-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        this._schedEditId = null;
        this._schedForm = {
          recipient: '', amount: '', label: '', memo: '',
          frequency: 'monthly', hour: '8', minute: '0',
          day_of_week: '0', day_of_month: '1',
          start_date: this._todayIso(), end_date: '',
        };
        this._updateContent();
      });
    });

    root.querySelectorAll('.sched-edit-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const schedId = btn.dataset.id;
        if (!schedId || !Array.isArray(this._schedules)) return;
        const schedule = this._schedules.find((s) => s.id === schedId);
        if (!schedule) return;
        this._schedEditId = schedId;
        this._schedForm = {
          recipient: String(schedule.recipient || ''),
          amount: String(schedule.amount_sat || ''),
          label: String(schedule.label || ''),
          memo: String(schedule.memo || ''),
          frequency: String(schedule.frequency || 'monthly'),
          hour: String(schedule.hour ?? '8'),
          minute: String(schedule.minute ?? '0'),
          day_of_week: String(schedule.day_of_week ?? '0'),
          day_of_month: String(schedule.day_of_month ?? '1'),
          start_date: String(schedule.start_date || this._todayIso()),
          end_date: String(schedule.end_date || ''),
        };
        this._updateContent();
      });
    });

    root.querySelectorAll('.sched-run-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const schedId = btn.dataset.id;
        if (!schedId) return;
        btn.disabled = true;
        this._hass.callService('alby_hub', 'run_scheduled_payment_now', { schedule_id: schedId })
          .then(() => {
            this._schedules = null;
            this._schedLoading = false;
            this._updateContent();
          })
          .catch((err) => {
            console.warn('Alby Hub panel: run_scheduled_payment_now failed', err);
            btn.disabled = false;
          });
      });
    });

    // Delete schedule buttons
    root.querySelectorAll('.sched-del-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const schedId = btn.dataset.id;
        if (!schedId) return;
        btn.disabled = true;
        this._hass.callService('alby_hub', 'delete_scheduled_payment', { schedule_id: schedId })
          .then(() => {
            if (this._schedEditId === schedId) {
              this._schedEditId = null;
            }
            this._schedules = null;
            this._schedLoading = false;
            this._updateContent();
          })
          .catch((err) => {
            console.warn('Alby Hub panel: delete_scheduled_payment failed', err);
            btn.disabled = false;
          });
      });
    });

    // ── Camera scan listeners ────────────────────────────────────────────────

    root.querySelectorAll('#camera-entity-sel').forEach((sel) => {
      sel.addEventListener('change', () => { this._cameraEntitySel = sel.value; });
    });

    root.querySelectorAll('#scan-entity-btn').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const entityId = this._cameraEntitySel;
        if (!entityId) return;
        const t = (k) => this._t(`camera.${k}`);
        this._cameraScanMsg = t('scanning');
        this._updateContent();
        try {
          const hasBarcodeApi = typeof BarcodeDetector !== 'undefined';
          if (!hasBarcodeApi) {
            this._cameraScanMsg = t('noBarcodeApiHint');
            this._updateContent();
            return;
          }
          // Fetch camera snapshot with HA auth
          let snapUrl = `/api/camera_proxy/${entityId}`;
          let imgBlob;
          if (typeof this._hass.fetchWithAuth === 'function') {
            const resp = await this._hass.fetchWithAuth(snapUrl);
            imgBlob = await resp.blob();
          } else {
            const token = this._hass.connection?.options?.accessToken ||
                          this._hass.auth?.data?.access_token || '';
            const resp = await fetch(snapUrl, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
            imgBlob = await resp.blob();
          }
          const imgUrl = URL.createObjectURL(imgBlob);
          const img = new Image();
          await new Promise((resolve, reject) => { img.onload = resolve; img.onerror = reject; img.src = imgUrl; });
          URL.revokeObjectURL(imgUrl);
          const detector = new BarcodeDetector({ formats: ['qr_code'] });
          const barcodes = await detector.detect(img);
          if (barcodes.length > 0) {
            this._pendingPayInput = barcodes[0].rawValue;
            this._cameraScanMsg = t('found') + ': ' + barcodes[0].rawValue.slice(0, 30) + (barcodes[0].rawValue.length > 30 ? '…' : '');
          } else {
            this._cameraScanMsg = t('notFound');
          }
        } catch (err) {
          this._cameraScanMsg = t('error') + ': ' + String(err).slice(0, 80);
        }
        this._updateContent();
      });
    });

    root.querySelectorAll('#scan-device-btn').forEach((btn) => {
      btn.addEventListener('click', async () => {
        if (this._cameraScanning) {
          // Stop camera
          this._stopCameraStream();
          this._updateContent();
          return;
        }
        const t = (k) => this._t(`camera.${k}`);
        const hasBarcodeApi = typeof BarcodeDetector !== 'undefined';
        if (!hasBarcodeApi) {
          this._cameraScanMsg = t('noBarcodeApiHint');
          this._updateContent();
          return;
        }
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
          this._cameraStream = stream;
          this._cameraScanning = true;
          this._cameraScanMsg = t('scanning');
          this._updateContent();

          const video = this.shadowRoot.querySelector('#camera-video');
          if (video) { video.srcObject = stream; video.play().catch(() => {}); }

          const detector = new BarcodeDetector({ formats: ['qr_code'] });
          const scanLoop = async () => {
            if (!this._cameraScanning || !this._cameraStream) return;
            const vid = this.shadowRoot.querySelector('#camera-video');
            if (!vid || vid.readyState < 2) { requestAnimationFrame(scanLoop); return; }
            try {
              const codes = await detector.detect(vid);
              if (codes.length > 0) {
                this._pendingPayInput = codes[0].rawValue;
                this._cameraStream = stream; // ensure _stopCameraStream can stop it
                const foundMsg = t('found') + ': ' + codes[0].rawValue.slice(0, 40) + (codes[0].rawValue.length > 40 ? '…' : '');
                this._stopCameraStream();
                this._cameraScanMsg = foundMsg;
                this._updateContent();
                return;
              }
            } catch (_) { /* keep scanning */ }
            if (this._cameraScanning) requestAnimationFrame(scanLoop);
          };
          requestAnimationFrame(scanLoop);
        } catch (err) {
          this._cameraScanning = false;
          this._cameraScanMsg = this._t('camera.error') + ': ' + String(err).slice(0, 80);
          this._updateContent();
        }
      });
    });

    root.querySelectorAll('#scan-file-input').forEach((input) => {
      input.addEventListener('change', async () => {
        const file = input.files?.[0];
        if (!file) return;
        const t = (k) => this._t(`camera.${k}`);
        const hasBarcodeApi = typeof BarcodeDetector !== 'undefined';
        if (!hasBarcodeApi) {
          this._cameraScanMsg = t('noBarcodeApiHint');
          this._updateContent();
          return;
        }
        this._cameraScanMsg = t('scanning');
        this._updateContent();
        try {
          const imgUrl = URL.createObjectURL(file);
          const img = new Image();
          await new Promise((resolve, reject) => { img.onload = resolve; img.onerror = reject; img.src = imgUrl; });
          URL.revokeObjectURL(imgUrl);
          const detector = new BarcodeDetector({ formats: ['qr_code'] });
          const barcodes = await detector.detect(img);
          if (barcodes.length > 0) {
            this._pendingPayInput = barcodes[0].rawValue;
            this._cameraScanMsg = t('found') + ': ' + barcodes[0].rawValue.slice(0, 40) + (barcodes[0].rawValue.length > 40 ? '…' : '');
          } else {
            this._cameraScanMsg = t('notFound');
          }
        } catch (err) {
          this._cameraScanMsg = t('error') + ': ' + String(err).slice(0, 80);
        }
        this._updateContent();
      });
    });

    // ── Copy automation example buttons ─────────────────────────────────────

    root.querySelectorAll('.copy-example-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const dir = btn.dataset.direction;
        const idx = parseInt(btn.dataset.idx, 10);
        const yaml = this._autoExamplesStore?.[dir]?.[idx]?.yaml;
        if (!yaml) return;
        const origText = btn.textContent;
        navigator.clipboard.writeText(yaml).then(() => {
          btn.textContent = this._t('autoExamples.copied');
          setTimeout(() => { btn.textContent = origText; }, 2000);
        }).catch(() => { btn.textContent = origText; });
      });
    });

    // ── Automation builder listeners ─────────────────────────────────────────

    const bindABField = (id, key, rerenderOnChange = false) => {
      const el = root.querySelector(`#${id}`);
      if (!el) return;
      el.addEventListener('change', () => { this._autoForm[key] = el.value; if (rerenderOnChange) { this._autoYaml = ''; this._updateContent(); } });
      el.addEventListener('input',  () => { this._autoForm[key] = el.value; });
    };
    bindABField('ab-direction',     'direction', true);
    bindABField('ab-trig-type',     'triggerType', true);
    bindABField('ab-trig-entity',   'trigEntityId');
    bindABField('ab-threshold',     'threshold');
    bindABField('ab-action-type',   'actionType', true);
    bindABField('ab-recipient',     'recipient');
    bindABField('ab-amount',        'amountSat');
    bindABField('ab-memo',          'memo');
    bindABField('ab-target-entity', 'targetEntityId');
    bindABField('ab-notify-msg',    'notifyMsg');

    root.querySelectorAll('#ab-generate-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        this._autoYaml = this._generateAutomationYaml();
        this._updateContent();
      });
    });

    root.querySelectorAll('#ab-copy-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        if (!this._autoYaml) return;
        const origText = btn.textContent;
        navigator.clipboard.writeText(this._autoYaml).then(() => {
          btn.textContent = this._t('autoBuilder.copied');
          setTimeout(() => { btn.textContent = origText; }, 2000);
        }).catch(() => { btn.textContent = origText; });
      });
    });

  }

  // ── CSS ──────────────────────────────────────────────────────────────────────

  _css() {
    return `<style>
      :host {
        display: block;
        height: 100%;
        background: var(--primary-background-color);
        color: var(--primary-text-color);
        font-family: var(--mdc-typography-body1-font-family, Roboto, sans-serif);
        font-size: 14px;
        box-sizing: border-box;
      }
      *, *::before, *::after { box-sizing: inherit; }

      /* ── Panel root ── */
      .panel-root {
        display: flex;
        flex-direction: column;
        height: 100%;
        overflow: hidden;
      }

      /* ── Header ── */
      .header {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        background: var(--app-header-background-color, #1c1c1c);
        color: var(--app-header-text-color, #fff);
        border-bottom: 1px solid var(--divider-color, #333);
        min-height: 56px;
      }
      .header-icon  { font-size: 1.4rem; }
      .header-title { font-size: 1.1rem; font-weight: 500; flex: 1; }

      /* ── Instance bar ── */
      .instance-bar {
        display: flex;
        gap: 6px;
        padding: 6px 12px;
        border-bottom: 1px solid var(--divider-color, #333);
        overflow-x: auto;
        flex-wrap: wrap;
      }
      .instance-btn {
        padding: 4px 14px;
        border-radius: 16px;
        border: 1px solid var(--divider-color, #555);
        background: transparent;
        color: var(--primary-text-color);
        cursor: pointer;
        font-size: 0.85rem;
        white-space: nowrap;
      }
      .instance-btn.active {
        background: var(--primary-color, #f7931a);
        color: #000;
        border-color: var(--primary-color, #f7931a);
        font-weight: 600;
      }

      /* ── Tab bar ── */
      .tab-bar {
        display: flex;
        border-bottom: 2px solid var(--divider-color, #333);
        overflow-x: auto;
      }
      .tab-btn {
        padding: 10px 16px;
        border: none;
        background: transparent;
        color: var(--secondary-text-color, #999);
        cursor: pointer;
        font-size: 0.9rem;
        white-space: nowrap;
        border-bottom: 2px solid transparent;
        margin-bottom: -2px;
      }
      .tab-btn.active {
        color: var(--primary-color, #f7931a);
        border-bottom-color: var(--primary-color, #f7931a);
        font-weight: 600;
      }

      /* ── Content area ── */
      .content {
        flex: 1;
        overflow-y: auto;
        padding: 14px;
      }

      /* ── Card grid ── */
      .cards-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 14px;
      }

      /* ── Card ── */
      .card {
        background: var(--card-background-color, #1e1e1e);
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, .35);
      }
      .card-title {
        font-weight: 600;
        font-size: 0.95rem;
        margin-bottom: 10px;
        color: var(--primary-text-color);
      }

      /* ── Status badge ── */
      .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 10px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 10px;
      }
      .badge-on  { background: rgba(76, 175, 80, .18); color: #4caf50; }
      .badge-off { background: rgba(244, 67, 54, .18); color: #f44336; }

      /* ── Balance table ── */
      .bal-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.85rem;
        margin-top: 4px;
      }
      .bal-table th,
      .bal-table td {
        padding: 5px 6px;
        text-align: left;
        border-bottom: 1px solid var(--divider-color, #333);
      }
      .bal-table thead th { color: var(--secondary-text-color, #aaa); font-weight: 500; }
      .bal-table td.num   { text-align: right; color: var(--primary-color, #f7931a); font-weight: 500; }

      /* ── Entity row ── */
      .row {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 7px 0;
        border-bottom: 1px solid var(--divider-color, #2a2a2a);
        font-size: 0.88rem;
      }
      .row:last-child { border-bottom: none; }
      .row-icon { font-size: 1rem; min-width: 22px; text-align: center; }
      .row-name { flex: 1; color: var(--primary-text-color); }
      .row-val  { color: var(--primary-color, #f7931a); font-weight: 500; text-align: right; }
      .row-val.small {
        font-size: 0.75rem;
        max-width: 50%;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      /* ── Form controls ── */
      .field { margin-bottom: 10px; }
      .field label {
        display: block;
        font-size: 0.78rem;
        color: var(--secondary-text-color, #aaa);
        margin-bottom: 3px;
      }
      .inp {
        width: 100%;
        padding: 8px 10px;
        border-radius: 8px;
        border: 1px solid var(--divider-color, #444);
        background: var(--secondary-background-color, #111);
        color: var(--primary-text-color);
        font-size: 0.9rem;
      }
      .mono { font-family: monospace; font-size: 0.78rem; }

      /* ── Buttons ── */
      .btn {
        width: 100%;
        padding: 10px;
        border-radius: 8px;
        border: none;
        background: var(--primary-color, #f7931a);
        color: #000;
        font-size: 0.95rem;
        font-weight: 700;
        cursor: pointer;
        transition: opacity .15s;
      }
      .btn:hover { opacity: .85; }
      .send-card { display: flex; align-items: center; justify-content: center; }
      .send-btn  { font-size: 1.25rem; padding: 20px; }

      /* ── Invoice / QR ── */
      .invoice-code {
        display: block;
        background: var(--secondary-background-color, #111);
        border-radius: 6px;
        padding: 8px;
        font-size: 0.68rem;
        font-family: monospace;
        word-break: break-all;
        margin: 8px 0;
      }
      .qr-wrap { text-align: center; margin: 10px 0; }
      .qr      { max-width: 280px; width: 100%; border-radius: 8px; }
      .ln-addr {
        text-align: center;
        color: var(--primary-color, #f7931a);
        word-break: break-all;
        font-size: 0.85rem;
        margin: 6px 0;
      }

      /* ── Budget ── */
      .budget-row  { margin-bottom: 4px; }
      .prog-bar    { height: 8px; background: var(--secondary-background-color, #111); border-radius: 4px; overflow: hidden; margin: 6px 0; }
      .prog-fill   { height: 100%; background: var(--primary-color, #f7931a); border-radius: 4px; }

      /* ── Transaction / schedule table ── */
      .tx-scroll  { overflow-x: auto; }
      .tx-table   { width: 100%; border-collapse: collapse; font-size: 0.83rem; }
      .tx-table th, .tx-table td {
        padding: 6px 8px;
        text-align: left;
        border-bottom: 1px solid var(--divider-color, #2a2a2a);
        white-space: nowrap;
      }
      .tx-table thead th { color: var(--secondary-text-color, #aaa); font-weight: 500; }

      /* ── Filter bar ── */
      .filter-bar  { display: flex; gap: 6px; margin-bottom: 10px; flex-wrap: wrap; }
      .filter-btn  {
        padding: 4px 12px;
        border-radius: 14px;
        border: 1px solid var(--divider-color, #555);
        background: transparent;
        color: var(--secondary-text-color, #aaa);
        cursor: pointer;
        font-size: 0.8rem;
        white-space: nowrap;
      }
      .filter-btn.active {
        background: var(--primary-color, #f7931a);
        color: #000;
        border-color: var(--primary-color, #f7931a);
        font-weight: 600;
      }
      .filter-btn:hover { opacity: .8; }

      /* ── Small delete button ── */
      .small-btn {
        padding: 3px 8px;
        border-radius: 6px;
        border: 1px solid var(--error-color, #f44336);
        background: transparent;
        color: var(--error-color, #f44336);
        cursor: pointer;
        font-size: 0.78rem;
      }
      .small-btn:hover { background: rgba(244,67,54,.12); }

      /* ── Automation examples & builder ── */
      .auto-example {
        margin-bottom: 14px;
        padding-bottom: 14px;
        border-bottom: 1px solid var(--divider-color, #2a2a2a);
      }
      .auto-example:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
      .auto-example-desc {
        font-size: 0.85rem;
        font-weight: 500;
        margin-bottom: 6px;
        color: var(--primary-text-color);
      }
      .auto-yaml {
        background: var(--secondary-background-color, #111);
        border-radius: 6px;
        padding: 10px 12px;
        font-size: 0.72rem;
        font-family: monospace;
        white-space: pre;
        overflow-x: auto;
        margin: 6px 0;
        color: var(--primary-text-color);
        border: 1px solid var(--divider-color, #333);
      }
      .auto-yaml code { font-family: inherit; }

      /* ── Typography ── */
      .muted { color: var(--secondary-text-color, #aaa); font-size: 0.85rem; }
      .small { font-size: 0.78rem; }
      p      { line-height: 1.5; margin: 0 0 8px; }
      ul     { margin: 6px 0; padding-left: 18px; }
      li     { margin-bottom: 4px; }

      /* ── Empty state ── */
      .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 60px 20px;
        text-align: center;
        color: var(--secondary-text-color, #aaa);
      }
      .empty-icon      { font-size: 4rem; margin-bottom: 16px; }
      .empty-state h2  { margin: 0 0 8px; color: var(--primary-text-color); }
    </style>`;
  }

  getCardSize() { return 10; }
}

// ──────────────────────────────────────────────────────────────────────────────
// Register
// ──────────────────────────────────────────────────────────────────────────────

if (!customElements.get(PANEL_ELEMENT_NAME)) {
  customElements.define(PANEL_ELEMENT_NAME, AlbyHubPanel);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === PANEL_ELEMENT_NAME)) {
  window.customCards.push({
    type: PANEL_ELEMENT_NAME,
    name: 'Alby Hub Panel',
    description: 'Alby Hub Bitcoin Lightning Integration – locked-down integration dashboard',
    preview: false,
  });
}

console.info(
  `%c ALBY HUB PANEL %c v${ALBY_HUB_VERSION} `,
  'background:#f7931a;color:#000;font-weight:bold;padding:2px 6px;border-radius:3px 0 0 3px',
  'background:#222;color:#f7931a;font-weight:bold;padding:2px 6px;border-radius:0 3px 3px 0'
);
