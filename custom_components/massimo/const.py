"""Constants of the Massimo integration."""

import logging
from datetime import timedelta
from typing import Final

DOMAIN: Final = "massimo"
LOGGER = logging.getLogger(__package__)

# The entry's data beside its address and key: whether the address is the
# one an announcement led to, which a later one may change, and whether the
# key is a registered integration's. The name Home Assistant gives itself
# in Massimo is a field of the flow alone.
CONF_ANNOUNCED: Final = "announced"
CONF_REGISTERED: Final = "registered"
CONF_REGISTRATION_NAME: Final = "registration_name"

# The mDNS service a Massimo server announces (Massimo's README, "Server").
ZEROCONF_TYPE: Final = "_massimo._tcp.local."

# The event stream's reconnection: the first wait, doubled after each
# failure up to the last.
RECONNECT_FIRST: Final = timedelta(seconds=2)
RECONNECT_LAST: Final = timedelta(seconds=60)

# The kinds of event after which a Cube's rooms are read again: they
# change rooms, names or devices, or say that events were lost.
REFRESH_KINDS: Final = frozenset({"metadata", "config", "connected", "resync", "device_forgotten", "paired"})

MANUFACTURER: Final = "eQ-3"

# The models of the device types Massimo names (docs/api-v1.md, the rooms).
MODELS: Final = {
    "radiator_thermostat": "MAX! Radiator Thermostat",
    "radiator_thermostat_plus": "MAX! Radiator Thermostat+",
    "wall_thermostat": "MAX! Wall Thermostat+",
    "shutter_contact": "MAX! Window Sensor",
    "eco_switch": "MAX! Eco Switch",
}
THERMOSTATS: Final = frozenset({"radiator_thermostat", "radiator_thermostat_plus", "wall_thermostat"})
RADIATOR_THERMOSTATS: Final = frozenset({"radiator_thermostat", "radiator_thermostat_plus"})
