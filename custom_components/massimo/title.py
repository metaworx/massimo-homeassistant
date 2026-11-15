"""An entry's title: its name, and whose key it signs in with where that
is a person's.

The name chosen in the setup flow is kept in the entry's data, and so is
the title last set from it; a title that differs from that one was renamed
by hand and is left alone. An entry made before either was kept has a
title ``Massimo`` or ``Massimo (<user>)``, both set automatically, and the
name ``Massimo``.
"""

from __future__ import annotations

import re

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.translation import async_get_translations

from .const import CONF_AUTO_TITLE, DOMAIN

DEFAULT_NAME = "Massimo"
_OLD_TITLE = re.compile(r"Massimo( \(.+\))?")
_KEY_OF = f"component.{DOMAIN}.exceptions.title_key_of.message"


async def entry_title(hass: HomeAssistant, name: str, user: str | None, registered: bool) -> str:
    """The title of an entry of that name: the name, followed by the key's
    user where the key is a person's, in Home Assistant's language."""
    if registered or not user:
        return name
    texts = await async_get_translations(hass, hass.config.language, "exceptions", [DOMAIN])
    return texts.get(_KEY_OF, "{name} (key of {user})").replace("{name}", name).replace("{user}", user)


def entry_name(entry: ConfigEntry) -> str:
    """The name chosen for an entry, ``Massimo`` for one made before."""
    return entry.data.get(CONF_NAME) or DEFAULT_NAME


def title_is_automatic(entry: ConfigEntry) -> bool:
    """Whether the entry's title is the one last set from its name, not
    renamed by hand."""
    if CONF_AUTO_TITLE in entry.data:
        return entry.title == entry.data[CONF_AUTO_TITLE]
    return _OLD_TITLE.fullmatch(entry.title) is not None
