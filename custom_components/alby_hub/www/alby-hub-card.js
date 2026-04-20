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

const ALBY_HUB_VERSION = '1.0.0';
const PANEL_ELEMENT_NAME = 'alby-hub-panel';

// ──────────────────────────────────────────────────────────────────────────────
// Entity ID builders
//
// Entity IDs are derived from HA's slugified translation names:
//   {platform}.{device_slug}_{entity_name_slug}
// e.g. device "Alby Hub" → device_slug "alby_hub"
//      entity name "Lightning balance" → name_slug "lightning_balance"
//      → sensor.alby_hub_lightning_balance
// ──────────────────────────────────────────────────────────────────────────────
const E = {
  nodeOnline:          (p) => `binary_sensor.${p}_node_online`,
  lightningBalance:    (p) => `sensor.${p}_lightning_balance`,
  onChainBalance:      (p) => `sensor.${p}_on_chain_balance`,
  lightningAddress:    (p) => `sensor.${p}_lightning_address`,
  nwcRelay:            (p) => `sensor.${p}_nwc_relay`,
  hubVersion:          (p) => `sensor.${p}_hub_version`,
  bitcoinPrice:        (p) => `sensor.${p}_bitcoin_price`,
  bitcoinBlockHeight:  (p) => `sensor.${p}_bitcoin_block_height`,
  bitcoinHashrate:     (p) => `sensor.${p}_bitcoin_hashrate`,
  blocksUntilHalving:  (p) => `sensor.${p}_blocks_until_halving`,
  nextHalvingEstimate: (p) => `sensor.${p}_next_halving_estimate`,
  nwcBudgetTotal:      (p) => `sensor.${p}_nwc_budget_total`,
  nwcBudgetUsed:       (p) => `sensor.${p}_nwc_budget_used`,
  nwcBudgetRemaining:  (p) => `sensor.${p}_nwc_budget_remaining`,
  nwcBudgetRenewal:    (p) => `sensor.${p}_nwc_budget_renewal_period`,
  invoiceAmount:       (p) => `number.${p}_invoice_amount`,
  invoiceAmountUnit:   (p) => `select.${p}_invoice_amount_unit`,
  createInvoice:       (p) => `button.${p}_create_invoice`,
  lastInvoice:         (p) => `text.${p}_last_invoice`,
  invoiceInput:        (p) => `text.${p}_invoice_input`,
};

// Navigation tabs
const TABS = [
  { id: 'overview', label: '⚡ Overview' },
  { id: 'receive',  label: '↙ Receive'  },
  { id: 'send',     label: '↗ Send'     },
  { id: 'budget',   label: '💰 Budget'  },
  { id: 'network',  label: '₿ Network'  },
];

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

    for (const entityId of Object.keys(hass.states)) {
      if (!entityId.startsWith('sensor.') || !entityId.endsWith('_lightning_balance')) continue;

      const prefix = entityId.slice('sensor.'.length, -'_lightning_balance'.length);
      if (seen.has(prefix)) continue;

      // Require the node_online binary sensor to confirm this is an Alby Hub
      if (!hass.states[`binary_sensor.${prefix}_node_online`]) continue;
      seen.add(prefix);

      // Derive display name: strip " Lightning balance" from friendly_name, or title-case prefix
      const state = hass.states[entityId];
      let displayName = prefix.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
      const fn = state?.attributes?.friendly_name;
      if (fn) {
        const stripped = fn.replace(/\s+Lightning\s+balance\s*$/i, '').trim();
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
            <h2>No Alby Hub instance found</h2>
            <p>Configure the Alby Hub integration under
              <strong>Settings → Devices &amp; Services</strong>.</p>
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

    const tabBar = `<div class="tab-bar">${TABS.map(
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
    const isOnline   = this._val(E.nodeOnline(p)) === 'on';
    const lightning  = this._num(E.lightningBalance(p));
    const onchain    = this._num(E.onChainBalance(p));
    const price      = this._num(E.bitcoinPrice(p));
    const currency   = this._attr(E.bitcoinPrice(p), 'unit_of_measurement', '');
    const relay      = this._val(E.nwcRelay(p));
    const version    = this._val(E.hubVersion(p));
    const address    = this._val(E.lightningAddress(p));
    const blockH     = this._val(E.bitcoinBlockHeight(p));
    const dispName   = this._instances.find((i) => i.prefix === p)?.displayName ?? p;

    const lnBtc   = (lightning / 1e8).toFixed(8);
    const ocBtc   = (onchain   / 1e8).toFixed(8);
    const lnFiat  = price > 0 ? ((lightning / 1e8) * price).toFixed(2) : null;
    const ocFiat  = price > 0 ? ((onchain   / 1e8) * price).toFixed(2) : null;

    return `<div class="cards-grid">
      <div class="card">
        <div class="card-title">⚡ ${this._esc(dispName)}</div>
        <div class="badge ${isOnline ? 'badge-on' : 'badge-off'}">${isOnline ? '✅ Connected' : '🔴 Offline'}</div>
        <table class="bal-table">
          <thead><tr><th></th><th>⚡ Lightning</th><th>₿ On-chain</th></tr></thead>
          <tbody>
            <tr><td>sat</td><td class="num">${lightning.toLocaleString()}</td><td class="num">${onchain.toLocaleString()}</td></tr>
            <tr><td>BTC</td><td class="num">${lnBtc}</td><td class="num">${ocBtc}</td></tr>
            ${lnFiat ? `<tr><td>≈&nbsp;${this._esc(currency)}</td><td class="num">${lnFiat}</td><td class="num">${ocFiat}</td></tr>` : ''}
          </tbody>
        </table>
      </div>

      <div class="card">
        <div class="card-title">Balance</div>
        ${this._row('⚡', 'Lightning', `${lightning.toLocaleString()} sat`)}
        ${this._row('₿', 'On-chain',  `${onchain.toLocaleString()} sat`)}
        ${price > 0
          ? this._row('💵', `Bitcoin Price (${this._esc(currency)})`, price.toLocaleString())
          : this._row('💵', 'Bitcoin Price', '<span class="muted">unavailable</span>', true)}
        ${this._row('🧱', 'Block Height', this._esc(blockH))}
      </div>

      <div class="card">
        <div class="card-title">Connection</div>
        ${this._row(isOnline ? '🟢' : '🔴', 'Node Online', isOnline ? 'On' : 'Off')}
        ${this._row('🔗', 'NWC Relay',        this._esc(relay),   false, true)}
        ${this._row('ℹ️', 'Hub Version',      this._esc(version))}
        ${this._row('📧', 'Lightning Address', this._esc(address), false, true)}
      </div>
    </div>`;
  }

  // ── Tab: Receive ─────────────────────────────────────────────────────────────

  _tabReceive(p) {
    const amount    = this._val(E.invoiceAmount(p),    '0');
    const unit      = this._val(E.invoiceAmountUnit(p), 'SAT');
    const options   = this._attr(E.invoiceAmountUnit(p), 'options', ['SAT', 'BTC']);
    const invoice   = this._val(E.lastInvoice(p),    '');
    const address   = this._val(E.lightningAddress(p), '');
    const lightning = this._num(E.lightningBalance(p));
    const onchain   = this._num(E.onChainBalance(p));

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
         <div class="muted small">Scan or copy the invoice above</div>`
      : `<div class="muted">No invoice yet. Set the amount and unit above, then press <b>Create Invoice</b>.</div>`;

    const addrBlock = !this._isUnavail(address)
      ? `<div class="ln-addr">${this._esc(address)}</div>
         <div class="qr-wrap">
           <img class="qr" src="https://api.qrserver.com/v1/create-qr-code/?data=lightning:${encodeURIComponent(address)}&size=240x240&margin=8" alt="Address QR">
         </div>`
      : `<div class="muted">Lightning address not available.</div>`;

    return `<div class="cards-grid">
      <div class="card">
        <div class="card-title">Create Invoice</div>
        <div class="field">
          <label>Amount</label>
          <input type="number" class="inp" id="inv-amount" min="0" value="${this._esc(amount)}"
            data-entity="${this._esc(E.invoiceAmount(p))}">
        </div>
        <div class="field">
          <label>Unit</label>
          <select class="inp" id="inv-unit" data-entity="${this._esc(E.invoiceAmountUnit(p))}">${opts}</select>
        </div>
        <button class="btn" id="create-inv-btn" data-prefix="${this._esc(p)}">Create Invoice ⚡</button>
      </div>

      <div class="card">
        <div class="card-title">BOLT11 Invoice &amp; QR Code</div>
        ${invoiceBlock}
      </div>

      <div class="card">
        <div class="card-title">Lightning Address</div>
        ${this._row('📧', 'Address', this._esc(address), false, true)}
      </div>

      <div class="card">
        <div class="card-title">Lightning Address QR (receive without fixed amount)</div>
        ${addrBlock}
      </div>

      <div class="card">
        <div class="card-title">Balance</div>
        ${this._row('⚡', 'Lightning', `${lightning.toLocaleString()} sat`)}
        ${this._row('₿', 'On-chain',  `${onchain.toLocaleString()} sat`)}
      </div>
    </div>`;
  }

  // ── Tab: Send ────────────────────────────────────────────────────────────────

  _tabSend(p) {
    const rawInput  = this._val(E.invoiceInput(p), '');
    const safeInput = this._isUnavail(rawInput) ? '' : rawInput;
    const lightning = this._num(E.lightningBalance(p));
    const onchain   = this._num(E.onChainBalance(p));

    return `<div class="cards-grid">
      <div class="card">
        <div class="card-title">Payment</div>
        <div class="field">
          <label>BOLT11 Invoice / Lightning Address</label>
          <input type="text" class="inp mono" id="inv-input" placeholder="lnbc…"
            value="${this._esc(safeInput)}"
            data-entity="${this._esc(E.invoiceInput(p))}">
        </div>
      </div>

      <div class="card">
        <div class="card-title">How to pay</div>
        <p><b>Option 1 – Paste:</b><br>
          Copy a BOLT11 invoice (or Lightning address) and paste it into the field above.</p>
        <p><b>Option 2 – QR scan (HA Companion App):</b><br>
          Tap the QR-code icon next to the input field to scan a Lightning invoice with your phone camera.</p>
        <p>Then press <b>Send Payment</b> below.</p>
      </div>

      <div class="card send-card">
        <button class="btn send-btn" id="send-btn" data-prefix="${this._esc(p)}">➤ Send Payment</button>
      </div>

      <div class="card">
        <div class="card-title">Balance</div>
        ${this._row('⚡', 'Lightning', `${lightning.toLocaleString()} sat`)}
        ${this._row('₿', 'On-chain',  `${onchain.toLocaleString()} sat`)}
      </div>
    </div>`;
  }

  // ── Tab: Budget ──────────────────────────────────────────────────────────────

  _tabBudget(p) {
    const total     = this._num(E.nwcBudgetTotal(p));
    const used      = this._num(E.nwcBudgetUsed(p));
    const remaining = this._num(E.nwcBudgetRemaining(p));
    const renewal   = this._val(E.nwcBudgetRenewal(p));

    let usageBlock;
    if (total > 0) {
      const pctUsed = ((used / total) * 100).toFixed(1);
      const pctRem  = ((remaining / total) * 100).toFixed(1);
      const dot     = parseFloat(pctUsed) >= 90 ? '🔴'
                    : parseFloat(pctUsed) >= 70 ? '🟠'
                    : parseFloat(pctUsed) >= 50 ? '🟡' : '🟢';
      usageBlock = `
        <div class="budget-row">${dot} <b>${pctUsed}% used</b> (${used.toLocaleString()} / ${total.toLocaleString()} sat)</div>
        <div class="prog-bar"><div class="prog-fill" style="width:${Math.min(100, parseFloat(pctUsed))}%"></div></div>
        <div class="muted">Remaining: <b>${remaining.toLocaleString()} sat</b> (${pctRem}%)</div>
        <div class="muted">Renewal: <b>${this._esc(renewal)}</b></div>`;
    } else {
      usageBlock = `<div class="muted"><em>No budget limit configured, or hub does not support get_budget.</em></div>`;
    }

    return `<div class="cards-grid">
      <div class="card">
        <div class="card-title">Budget Usage</div>
        ${usageBlock}
        <div class="card-title" style="margin-top:14px">NWC Spending Limits</div>
        ${this._row('💰', 'Total Budget',     `${total.toLocaleString()} sat`)}
        ${this._row('💸', 'Used Budget',      `${used.toLocaleString()} sat`)}
        ${this._row('💵', 'Remaining Budget', `${remaining.toLocaleString()} sat`)}
        ${this._row('🔄', 'Renewal Period',    this._esc(renewal))}
      </div>

      <div class="card">
        <div class="card-title">About NWC Budget</div>
        <p>These sensors show the spending limits configured for this NWC connection.</p>
        <ul>
          <li><b>Total budget</b> – maximum amount this connection may spend per renewal period</li>
          <li><b>Used budget</b> – amount already spent in the current period</li>
          <li><b>Remaining budget</b> – amount still available to spend</li>
          <li><b>Renewal period</b> – how often the budget resets (daily / weekly / monthly / …)</li>
        </ul>
        <p class="muted"><em>Sensors show 'unavailable' if no budget limit is set or if your hub does not support the get_budget method.</em></p>
      </div>
    </div>`;
  }

  // ── Tab: Network ─────────────────────────────────────────────────────────────

  _tabNetwork(p) {
    const price    = this._val(E.bitcoinPrice(p));
    const currency = this._attr(E.bitcoinPrice(p), 'unit_of_measurement', '');
    const blockH   = this._val(E.bitcoinBlockHeight(p));
    const hashrate = this._val(E.bitcoinHashrate(p));
    const blocks   = this._num(E.blocksUntilHalving(p));
    const halvEta  = this._val(E.nextHalvingEstimate(p));

    let halvingBlock;
    if (blocks > 0) {
      let etaStr = halvEta;
      try { etaStr = new Date(halvEta).toLocaleString(); } catch (_) { /* keep raw */ }
      halvingBlock = `
        <p>⛏️ <b>${blocks.toLocaleString()} blocks</b> remaining until the next halving.</p>
        <p>📅 Estimated date: <b>${this._esc(etaStr)}</b></p>`;
    } else {
      halvingBlock = `<p class="muted"><em>Halving data not available.</em></p>`;
    }

    return `<div class="cards-grid">
      <div class="card">
        <div class="card-title">Bitcoin Market &amp; Network</div>
        ${this._row('💵', `Bitcoin Price (${this._esc(currency)})`, this._esc(price))}
        ${this._row('🧱', 'Block Height',        this._esc(blockH))}
        ${this._row('⚡', 'Hashrate',             this._esc(hashrate))}
        ${this._row('⛏️', 'Blocks Until Halving', blocks > 0 ? blocks.toLocaleString() : this._esc(String(blocks)))}
        ${this._row('📅', 'Next Halving Estimate', this._esc(halvEta))}
      </div>

      <div class="card">
        <div class="card-title">Next Halving</div>
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

    // Invoice amount number input
    root.querySelectorAll('#inv-amount').forEach((el) => {
      el.addEventListener('change', () => {
        if (el.dataset.entity) {
          this._hass.callService('number', 'set_value', {
            entity_id: el.dataset.entity,
            value: el.value,
          });
        }
      });
    });

    // Invoice amount unit select
    root.querySelectorAll('#inv-unit').forEach((el) => {
      el.addEventListener('change', () => {
        if (el.dataset.entity) {
          this._hass.callService('select', 'select_option', {
            entity_id: el.dataset.entity,
            option: el.value,
          });
        }
      });
    });

    // Create invoice button – presses the HA button entity which reads
    // amount + unit from sibling entities automatically (see button.py)
    root.querySelectorAll('#create-inv-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        if (btn.dataset.prefix) {
          this._hass.callService('button', 'press', {
            entity_id: E.createInvoice(btn.dataset.prefix),
          });
        }
      });
    });

    // Invoice input text field (send tab)
    root.querySelectorAll('#inv-input').forEach((el) => {
      el.addEventListener('change', () => {
        if (el.dataset.entity) {
          this._hass.callService('text', 'set_value', {
            entity_id: el.dataset.entity,
            value: el.value,
          });
        }
      });
    });

    // Send payment button – reads invoice_input entity automatically (see services.py)
    root.querySelectorAll('#send-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        this._hass.callService('alby_hub', 'send_payment', {});
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
