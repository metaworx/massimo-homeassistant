"""The integration's own services: those that need less than control.

Home Assistant lets a user call an entity service only where the user may
control each entity named, whatever the service does. Reading a room's week
programme needs only view, so ``massimo.get_program`` is a service of the
integration, registered once, that checks ``read`` itself; its target and
its answer, one programme per entity, are an entity service's.
"""

from __future__ import annotations

from homeassistant.components.climate import DATA_COMPONENT
from homeassistant.const import ENTITY_MATCH_ALL
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_extract_entity_ids

from .climate import SERVICE_GET_PROGRAM, RoomClimate
from .const import DOMAIN
from .entity import check_read, read_access


def _rooms(hass: HomeAssistant) -> dict[str, RoomClimate]:
    """Every room's climate of the integration, by its entity id."""
    component = hass.data.get(DATA_COMPONENT)
    if component is None:
        return {}
    return {entity.entity_id: entity for entity in component.entities if isinstance(entity, RoomClimate)}


async def _get_program(call: ServiceCall) -> ServiceResponse:
    """The week programme of each room named, for a user who may read it."""
    hass = call.hass
    rooms = _rooms(hass)
    if call.data.get("entity_id") == ENTITY_MATCH_ALL:
        # As an entity service does: every room the user may read.
        may_read = await read_access(hass, call.context)
        named = sorted(entity_id for entity_id in rooms if may_read(entity_id))
    else:
        named = sorted(await async_extract_entity_ids(call))
        await check_read(hass, call.context, named)
    for entity_id in named:
        if entity_id not in rooms:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="not_a_room",
                translation_placeholders={"entity_id": entity_id},
            )
    return {entity_id: await rooms[entity_id].async_get_program() for entity_id in named}


def async_register_services(hass: HomeAssistant) -> None:
    """Register the integration's own services."""
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_PROGRAM,
        _get_program,
        schema=cv.make_entity_service_schema({}),
        supports_response=SupportsResponse.ONLY,
    )
