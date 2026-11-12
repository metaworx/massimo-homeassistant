"""The key lock of each thermostat: its buttons locked or not ("LoC" on
its display), written through Massimo's queue."""

from __future__ import annotations

from typing import Any, override

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import MassimoDiscardedError, MassimoError
from .const import DOMAIN, THERMOSTATS
from .coordinator import MassimoConfigEntry
from .entity import DeviceEntity, add_entities_as_they_come, devices_of

KEY_LOCK = SwitchEntityDescription(key="key_lock", translation_key="key_lock", entity_category=EntityCategory.CONFIG)


async def async_setup_entry(
    hass: HomeAssistant, entry: MassimoConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add a key lock per thermostat."""
    coordinator = entry.runtime_data

    def make():
        for serial, dev in devices_of(coordinator):
            if dev.get("type") in THERMOSTATS:
                yield f"{serial}_{KEY_LOCK.key}", lambda serial=serial: KeyLock(coordinator, serial, KEY_LOCK)

    add_entities_as_they_come(coordinator, entry, async_add_entities, make)


class KeyLock(DeviceEntity, SwitchEntity):
    """A thermostat's key lock. It shows what the device reports: a change
    written shows once the device has taken it and reported again."""

    @property
    @override
    def is_on(self) -> bool:
        """Whether the buttons are locked."""
        return bool(self.state_data.get("panel_locked"))

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Lock the buttons."""
        await self._lock(True)

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Unlock the buttons."""
        await self._lock(False)

    async def _lock(self, locked: bool) -> None:
        found = self.found
        if found is None:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="device_gone")
        cube_serial, _, dev = found
        try:
            await self.coordinator.client.set_lock(cube_serial, dev["rf_address"], locked)
        except MassimoDiscardedError as err:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="discarded") from err
        except MassimoError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="write_failed", translation_placeholders={"error": str(err)}
            ) from err
