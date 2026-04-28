"""Notify platform for Alby Hub – exposes the Nostr bot as a HA notify entity.

The entity broadcasts an encrypted Nostr DM to *all* npubs in the bot's
allow-list.  For targeting a single recipient, use the service
``alby_hub.nostr_send_bot_message`` directly.

Example automation action::

    action:
      - action: notify.alby_hub_nostr_bot
        data:
          message: "⚡ Motion detected in the living room!"
          title: "Home Alert"   # prepended as "title: message"
"""

from __future__ import annotations

import logging

from homeassistant.components.notify import NotifyEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_NOSTR_ENABLED, DOMAIN
from .entity import AlbyHubCoordinatorEntity
from .helpers import get_runtime

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Alby Hub Nostr notify entity for a config entry.

    The entity is only registered when the Nostr bot is enabled and the
    manager has been initialised.
    """
    merged = dict(entry.data)
    merged.update(entry.options)

    if not merged.get(CONF_NOSTR_ENABLED):
        return

    runtime = get_runtime(hass, entry.entry_id)
    manager = runtime.nostr_bot_manager
    if manager is None:
        return

    async_add_entities(
        [AlbyHubNostrNotifyEntity(runtime.coordinator, entry.entry_id, manager)]
    )


class AlbyHubNostrNotifyEntity(AlbyHubCoordinatorEntity, NotifyEntity):
    """Notify entity that sends encrypted Nostr DMs via the configured bot key.

    Calling ``notify.alby_hub_nostr_bot`` with a ``message`` (and optional
    ``title``) broadcasts the text to every npub in the integration's
    allow-list.  Individual delivery failures are logged as warnings but do
    not prevent delivery to the remaining recipients.
    """

    _attr_translation_key = "nostr_bot"
    _attr_icon = "mdi:chat-processing-outline"

    def __init__(
        self,
        coordinator,
        entry_id: str,
        manager,
    ) -> None:
        super().__init__(coordinator, entry_id)
        self._manager = manager
        self._attr_unique_id = f"{entry_id}_nostr_bot_notify"

    async def async_send_message(self, message: str, title: str | None = None) -> None:
        """Send a Nostr DM to all whitelisted npubs.

        If *title* is provided the final message becomes ``"<title>: <message>"``.
        Each allowed npub is tried independently; a failure for one recipient
        is logged but does not abort delivery to the others.
        """
        if not self._manager:
            _LOGGER.warning(
                "Alby Hub notify: Nostr bot manager not available; message not sent"
            )
            return

        full_message = f"{title}: {message}" if title else message

        recipients = list(self._manager.allowed_npubs)
        if not recipients:
            _LOGGER.warning(
                "Alby Hub notify: no whitelisted npubs configured – message not sent"
            )
            return

        for npub in recipients:
            try:
                await self._manager.async_send_bot_message(npub, full_message)
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning(
                    "Alby Hub notify: failed to send Nostr DM to %s: %s", npub, exc
                )
