# Alby Hub Dashboard Templates

This directory contains ready-to-use Lovelace dashboard configurations for the
**Alby Hub** Home Assistant integration.

## 📁 Available Templates

### `alby-hub-dashboard.yaml`

A complete, multi-view Lovelace dashboard for a single Alby Hub connection.

**Views:**

| View | Icon | Content |
|------|------|---------|
| **Overview** | `mdi:view-dashboard` | Connection status badge, balance summary (sat + BTC + fiat equivalent), BTC price & block height, connection info |
| **Receive** | `mdi:arrow-bottom-left` | Invoice creation form, BOLT11 invoice + QR code, Lightning address + QR |
| **Send** | `mdi:arrow-top-right` | BOLT11 / Lightning address input, how-to guide, Send button |
| **NWC Budget** | `mdi:cash-lock` | Dynamic budget usage summary with colour indicator, spending limit entities |
| **Network** | `mdi:bitcoin` | BTC market & network entities, 7-day price history graph, halving countdown |

## 🚀 Quick Start (5 minutes)

> **Note:** The integration automatically creates this dashboard when you first set it up –
> you usually don't need to do anything manually.
> Use this template when you want a **custom layout** or an **additional dashboard instance**.

### Step 1 – Find your connection name slug

Your entity IDs follow the pattern `sensor.<slug>_balance_lightning`.

1. In Home Assistant go to **Developer Tools → States**
2. Search for `balance_lightning`
3. Note the slug before `_balance_lightning`  
   *Example: `sensor.alby_hub_balance_lightning` → slug is `alby_hub`*

### Step 2 – Open the Raw configuration editor

1. Go to **Settings → Dashboards**
2. Click **+ ADD DASHBOARD**
3. Choose **"New dashboard from scratch"**
4. Give it a title (e.g. *"Alby Hub"*) and click **CREATE**
5. Open the new dashboard
6. Click **⋮ (three dots)** → **Edit Dashboard**
7. Click **⋮** again → **Raw configuration editor**

### Step 3 – Paste and customise

1. Copy the entire content of `alby-hub-dashboard.yaml`
2. Paste it into the editor
3. Press **Ctrl+H** (Find & Replace) and replace every occurrence of  
   `YOUR_CONNECTION_NAME` with your slug from Step 1
4. Click **SAVE**
5. Click **DONE** to exit edit mode – your dashboard is live! 🎉

## 🎨 Customisation

### Adjust history-graph time range

```yaml
- type: history-graph
  hours_to_show: 168   # 24 = 1 day, 168 = 1 week, 720 = 30 days
```

### Add a second connection

Duplicate the entire `views:` block (or individual cards) and replace the slug
with the second connection's slug.

### Change colours / icons

Modify `severity` thresholds on gauge cards or adjust emoji indicators in the
markdown cards.

## 🛠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| "Entity not found" | Check slug in **Developer Tools → States**; ensure all `YOUR_CONNECTION_NAME` occurrences were replaced |
| History graph is empty | Wait for data to accumulate; verify HA Recorder is enabled |
| Markdown shows raw `{% %}` | Verify HA version supports Jinja2 in markdown; check entity availability |
| Dashboard not in sidebar | Go to **Settings → Dashboards**, edit the dashboard and enable "Show in sidebar" |

## 📚 Additional Resources

- [Home Assistant Dashboard Documentation](https://www.home-assistant.io/dashboards/)
- [Integration README](../README.md)
- [Developer Handbook](../docs/developer-handbook.de.md)
