"""Sensor platform for Alby Hub."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Callable

from homeassistant.components.sensor import SensorDeviceClass, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .entity import AlbyHubCoordinatorEntity
from .helpers import get_runtime
from .const import (
    DOMAIN,
    SENSOR_KEY_LAST_INVOICE,
    SENSOR_KEY_NWC_BUDGET_REMAINING,
    SENSOR_KEY_NWC_BUDGET_RENEWAL,
    SENSOR_KEY_NWC_BUDGET_TOTAL,
    SENSOR_KEY_NWC_BUDGET_USED,
)


@dataclass(frozen=True, kw_only=True)
class AlbyHubSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], object]


SENSOR_DESCRIPTIONS: tuple[AlbyHubSensorDescription, ...] = (
    AlbyHubSensorDescription(
        key="balance_lightning",
        translation_key="balance_lightning",
        native_unit_of_measurement="sat",
        icon="mdi:lightning-bolt",
        value_fn=lambda data: data.get("balance_lightning"),
    ),
    AlbyHubSensorDescription(
        key="balance_onchain",
        translation_key="balance_onchain",
        native_unit_of_measurement="sat",
        icon="mdi:bitcoin",
        value_fn=lambda data: data.get("balance_onchain"),
    ),
    AlbyHubSensorDescription(
        key="lightning_address",
        translation_key="lightning_address",
        icon="mdi:email-outline",
        value_fn=lambda data: data.get("lightning_address"),
    ),
    AlbyHubSensorDescription(
        key="relay",
        translation_key="relay",
        icon="mdi:transit-connection-variant",
        value_fn=lambda data: data.get("relay"),
    ),
    AlbyHubSensorDescription(
        key="version",
        translation_key="version",
        icon="mdi:information-outline",
        value_fn=lambda data: data.get("version"),
    ),
    AlbyHubSensorDescription(
        key="bitcoin_price",
        translation_key="bitcoin_price",
        device_class=SensorDeviceClass.MONETARY,
        icon="mdi:currency-btc",
        value_fn=lambda data: data.get("bitcoin_price"),
    ),
    AlbyHubSensorDescription(
        key="bitcoin_block_height",
        translation_key="bitcoin_block_height",
        icon="mdi:cube-outline",
        value_fn=lambda data: data.get("bitcoin_block_height"),
    ),
    AlbyHubSensorDescription(
        key="bitcoin_hashrate",
        translation_key="bitcoin_hashrate",
        native_unit_of_measurement="EH/s",
        icon="mdi:speedometer",
        value_fn=lambda data: data.get("bitcoin_hashrate"),
    ),
    AlbyHubSensorDescription(
        key="blocks_until_halving",
        translation_key="blocks_until_halving",
        native_unit_of_measurement="blocks",
        icon="mdi:counter",
        value_fn=lambda data: data.get("blocks_until_halving"),
    ),
    AlbyHubSensorDescription(
        key="next_halving_eta",
        translation_key="next_halving_eta",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:calendar-clock",
        # ETA is computed dynamically from blocks_until_halving + avg_minutes_per_block
        value_fn=lambda data: _compute_halving_eta(data),
    ),
    # ── NWC Budget sensors ────────────────────────────────────────────────────
    AlbyHubSensorDescription(
        key=SENSOR_KEY_NWC_BUDGET_TOTAL,
        translation_key=SENSOR_KEY_NWC_BUDGET_TOTAL,
        native_unit_of_measurement="sat",
        icon="mdi:cash-lock",
        value_fn=lambda data: data.get("nwc_budget_total"),
    ),
    AlbyHubSensorDescription(
        key=SENSOR_KEY_NWC_BUDGET_USED,
        translation_key=SENSOR_KEY_NWC_BUDGET_USED,
        native_unit_of_measurement="sat",
        icon="mdi:cash-minus",
        value_fn=lambda data: data.get("nwc_budget_used"),
    ),
    AlbyHubSensorDescription(
        key=SENSOR_KEY_NWC_BUDGET_REMAINING,
        translation_key=SENSOR_KEY_NWC_BUDGET_REMAINING,
        native_unit_of_measurement="sat",
        icon="mdi:cash-check",
        value_fn=lambda data: data.get("nwc_budget_remaining"),
    ),
    AlbyHubSensorDescription(
        key=SENSOR_KEY_NWC_BUDGET_RENEWAL,
        translation_key=SENSOR_KEY_NWC_BUDGET_RENEWAL,
        icon="mdi:calendar-refresh",
        value_fn=lambda data: data.get("nwc_budget_renewal"),
    ),
)


def _compute_halving_eta(data: dict) -> object | None:
    """Compute halving ETA dynamically so it stays fresh between coordinator updates."""
    blocks = data.get("blocks_until_halving")
    if blocks is None:
        return None
    minutes_per_block = data.get("minutes_per_block", 10.0)
    return datetime.now(UTC) + timedelta(minutes=float(blocks) * float(minutes_per_block))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Alby Hub sensors from a config entry."""
    runtime = get_runtime(hass, entry.entry_id)
    entities = [
        AlbyHubSensor(runtime.coordinator, entry.entry_id, description)
        for description in SENSOR_DESCRIPTIONS
    ]
    last_invoice = AlbyHubLastInvoiceSensor(runtime.coordinator, entry.entry_id)
    entities.append(last_invoice)
    async_add_entities(entities)
    runtime.last_invoice_entity = last_invoice


class AlbyHubSensor(AlbyHubCoordinatorEntity):
    """Sensor backed by coordinator data."""

    entity_description: AlbyHubSensorDescription

    def __init__(
        self,
        coordinator,
        entry_id: str,
        description: AlbyHubSensorDescription,
    ) -> None:
        super().__init__(coordinator, entry_id)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def native_value(self) -> object | None:
        """Return the current sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return dynamic units for selected price currency."""
        if self.entity_description.key == "bitcoin_price":
            return self.coordinator.data.get("price_currency")
        return self.entity_description.native_unit_of_measurement


class AlbyHubLastInvoiceSensor(AlbyHubCoordinatorEntity, RestoreEntity):
    """Sensor that stores the last created BOLT11 invoice in an attribute.

    HA's state machine limits state strings to 255 characters, which is too
    short for BOLT11 invoices (300-1000+ chars). This sensor stores the full
    invoice in ``extra_state_attributes["bolt11"]`` and uses a short status
    string ("set" / "") as the entity state.
    """

    _attr_icon = "mdi:qrcode"
    _attr_has_entity_name = True
    _attr_translation_key = SENSOR_KEY_LAST_INVOICE

    def __init__(self, coordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_{SENSOR_KEY_LAST_INVOICE}"
        self._bolt11: str = ""
        self._amount_sat: int | None = None
        self._memo: str | None = None

    async def async_added_to_hass(self) -> None:
        """Restore the last invoice from storage after a restart."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._bolt11 = last_state.attributes.get("bolt11", "") or ""
            amount_sat = last_state.attributes.get("amount_sat")
            self._amount_sat = int(amount_sat) if isinstance(amount_sat, (int, float)) else None
            memo = last_state.attributes.get("memo")
            self._memo = str(memo) if isinstance(memo, str) and memo.strip() else None

    @property
    def state(self) -> str:
        """Return 'set' when an invoice is stored, empty string otherwise."""
        return "set" if self._bolt11 else ""

    @property
    def extra_state_attributes(self) -> dict:
        """Expose the full BOLT11 invoice as an attribute."""
        return {
            "bolt11": self._bolt11,
            "amount_sat": self._amount_sat,
            "memo": self._memo,
        }

    async def async_set_invoice(
        self,
        invoice: str,
        amount_sat: int | None = None,
        memo: str | None = None,
    ) -> None:
        """Store a new BOLT11 invoice and push the state update."""
        self._bolt11 = invoice
        self._amount_sat = amount_sat
        memo_stripped = memo.strip() if isinstance(memo, str) else ""
        self._memo = memo_stripped or None
        self.async_write_ha_state()
