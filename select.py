"""How a room's temperature is taken from its radiator thermostats where it
has no wall thermostat: their median or their mean (the virtual wall
thermostat's setting temp_method, kept by Massimo without radio)."""

from __future__ import annotations

from typing import override

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import MassimoConfigEntry, has_thermostat
from .entity import RoomEntity, add_entities_as_they_come, rooms_of

TEMP_METHOD = SelectEntityDescription(
    key="temp_method",
    translation_key="temp_method",
    entity_category=EntityCategory.CONFIG,
    options=["median", "mean"],
)


async def async_setup_entry(
    hass: HomeAssistant, entry: MassimoConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add the temperature method of each room with a thermostat."""
    coordinator = entry.runtime_data

    def make():
        for serial, room in rooms_of(coordinator):
            if has_thermostat(room):
                uid = room["room_uid"]
                yield (
                    f"{serial}_{uid}_{TEMP_METHOD.key}",
                    lambda serial=serial, uid=uid: TempMethod(coordinator, serial, uid, TEMP_METHOD),
                )

    add_entities_as_they_come(coordinator, entry, async_add_entities, make)


class TempMethod(RoomEntity, SelectEntity):
    """A room's temperature method."""

    @property
    @override
    def available(self) -> bool:
        """Whether the stream is up and the room's settings are read; the
        setting is Massimo's, whatever the thermostats report."""
        return self.coordinator.last_update_success and "temp_method" in (self.details.get("settings") or {})

    @property
    @override
    def current_option(self) -> str | None:
        """median or mean."""
        return (self.details.get("settings") or {}).get("temp_method")

    @override
    async def async_select_option(self, option: str) -> None:
        """Set the method; Massimo answers it, and its config event reads the
        room again."""
        rf = self.vwt.get("rf_address")
        if not rf:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="device_gone")
        await self.write(self.coordinator.client.set_device_config(self.cube_serial, rf, {"temp_method": option}))
