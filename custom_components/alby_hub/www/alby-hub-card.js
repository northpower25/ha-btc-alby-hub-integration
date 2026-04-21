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

const ALBY_HUB_VERSION = '1.0.1';
const PANEL_ELEMENT_NAME = 'alby-hub-panel';

// ──────────────────────────────────────────────────────────────────────────────
// Translations (DE / EN)
// ──────────────────────────────────────────────────────────────────────────────
const TRANSLATIONS = {
  de: {
    tabs: { overview: '⚡ Übersicht', receive: '↙ Empfangen', send: '↗ Senden', budget: '💰 Budget', network: '₿ Netzwerk' },
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
      btn: 'Rechnung erstellen ⚡',
      invoiceTitle: 'BOLT11-Rechnung & QR-Code',
      noInvoice: 'Noch keine Rechnung. Betrag und Einheit oben eingeben, dann <b>Rechnung erstellen</b> drücken.',
      scanHint: 'Rechnung scannen oder kopieren',
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
    unavailable: 'nicht verfügbar',
  },
  en: {
    tabs: { overview: '⚡ Overview', receive: '↙ Receive', send: '↗ Send', budget: '💰 Budget', network: '₿ Network' },
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
      btn: 'Create Invoice ⚡',
      invoiceTitle: 'BOLT11 Invoice & QR Code',
      noInvoice: 'No invoice yet. Set the amount and unit above, then press <b>Create Invoice</b>.',
      scanHint: 'Scan or copy the invoice above',
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
    this._pendingPayInput  = '';   // send: payment string typed by user
    this._pendingPayAmount = '';   // send: amount typed by user
    this._pendingPayUnit   = '';   // send: unit selected by user
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
      { id: 'overview', label: t('tabs.overview') },
      { id: 'receive',  label: t('tabs.receive')  },
      { id: 'send',     label: t('tabs.send')     },
      { id: 'budget',   label: t('tabs.budget')   },
      { id: 'network',  label: t('tabs.network')  },
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
        const stripped = fn.replace(/\s+Lightning[-\s]+balance\s*$/i, '').trim();
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
    const content = this.shadowRoot.querySelector('#content');
    if (!content || !this._activePrefix) return;
    content.innerHTML = this._renderTab(this._activeTab, this._activePrefix);
    this._attachContentListeners();
    this._lastUpdate = Date.now();
  }

  // ── Tab dispatcher ───────────────────────────────────────────────────────────

  _renderTab(id, p) {
    switch (id) {
      case 'overview': return this._tabOverview(p);
      case 'receive':  return this._tabReceive(p);
      case 'send':     return this._tabSend(p);
      case 'budget':   return this._tabBudget(p);
      case 'network':  return this._tabNetwork(p);
      default:         return '';
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
    // Use pending (user-typed) values when available, fall back to entity state
    const amount  = this._pendingInvAmount || this._val(this._eid('invoiceAmount', p), '0');
    const unit    = this._pendingInvUnit   || this._val(this._eid('invoiceAmountUnit', p), 'SAT');
    const options = this._attr(this._eid('invoiceAmountUnit', p), 'options', ['SAT', 'BTC']);
    // last_invoice is now a sensor; full BOLT11 is stored in the "bolt11" attribute
    const invoice   = this._attr(this._eid('lastInvoice', p), 'bolt11', '');
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
    </div>`;
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
    const payAmount  = this._pendingPayAmount || this._val(this._eid('invoiceAmount', p), '0');
    const payUnit    = this._pendingPayUnit   || this._val(this._eid('invoiceAmountUnit', p), 'SAT');
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
    </div>`;
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

  // ── Row helper ───────────────────────────────────────────────────────────────

  _row(icon, name, value, rawHtml = false, small = false) {
    const valHtml = rawHtml ? value : this._esc(value);
    return `<div class="row">
      <span class="row-icon">${icon}</span>
      <span class="row-name">${this._esc(name)}</span>
      <span class="row-val${small ? ' small' : ''}">${valHtml}</span>
    </div>`;
  }

  // ── Menu button ──────────────────────────────────────────────────────────────

  _applyMenuBtn() {
    const btn = this.shadowRoot.querySelector('ha-menu-button');
    if (btn) {
      btn.hass   = this._hass;
      btn.narrow = this._narrow;
    }
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
        this._activeTab = btn.dataset.tab;
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

    // Create invoice button
    root.querySelectorAll('#create-inv-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        if (btn.dataset.prefix) {
          this._hass.callService('button', 'press', {
            entity_id: this._eid('createInvoice', btn.dataset.prefix),
          });
          // Clear pending receive inputs after create (entity will be updated)
          this._pendingInvAmount = '';
          this._pendingInvUnit   = '';
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

    // Send payment button – pass payment_request and amount directly to avoid
    // the 255-char text entity state limit
    root.querySelectorAll('#send-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const payInput  = this._pendingPayInput.trim();
        const payAmount = this._pendingPayAmount;
        const payUnit   = this._pendingPayUnit || 'SAT';
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
        this._hass.callService('alby_hub', 'send_payment', serviceData).then(() => {
          // Clear pending values after successful send
          this._pendingPayInput  = '';
          this._pendingPayAmount = '';
          this._pendingPayUnit   = '';
          // Force re-render
          this._lastUpdate = 0;
          this._updateContent();
        }).catch(() => {});
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

customElements.define(PANEL_ELEMENT_NAME, AlbyHubPanel);

window.customCards = window.customCards || [];
window.customCards.push({
  type: PANEL_ELEMENT_NAME,
  name: 'Alby Hub Panel',
  description: 'Alby Hub Bitcoin Lightning Integration – locked-down integration dashboard',
  preview: false,
});

console.info(
  `%c ALBY HUB PANEL %c v${ALBY_HUB_VERSION} `,
  'background:#f7931a;color:#000;font-weight:bold;padding:2px 6px;border-radius:3px 0 0 3px',
  'background:#222;color:#f7931a;font-weight:bold;padding:2px 6px;border-radius:0 3px 3px 0'
);
