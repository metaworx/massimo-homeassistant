# Massimo for Home Assistant

A Home Assistant integration for [Massimo](https://github.com/metaworx/massimo),
the server that holds eQ-3 MAX!
Cubes: Massimo keeps the Cubes, their radio budget, pairing and week programmes,
and Home Assistant becomes one more client of its HTTP API,
beside Massimo's own web UI and apps.

> **Not released yet.**
> It sets up a Massimo server, follows its Cubes,
> shows their devices with their sensors and key locks,
> controls each room's heating, boost included, and reads, writes and copies
> its week programme.
> A week-programme card follows.
> Until a release, Home Assistant's own MAX! integration can control the Cube through
> Massimo's LAN proxy,
> as Massimo's
> [docs/homeassistant.md](https://github.com/metaworx/massimo/blob/main/docs/homeassistant.md) describes.

## What it does so far

- **Setup** by address, or found by mDNS (`_massimo._tcp`), with an API key.
  The server is known by its node id, so a new address is followed.
- **Live data**:
  it reads the server's Cubes and rooms once and then follows each Cube's event
  stream.
  After an interruption it resumes after the last event it read,
  where the server supports it (Massimo with event ids),
  and reads again what the server no longer holds.
- **Devices**: the Cube as a hub, and each thermostat, window contact and eco
  switch as a device of its own beneath it,
  in an area named as its room in Massimo
  (the area is only suggested, when the device first appears;
  the areas stay yours).
  Devices paired later appear without a restart,
  and devices removed in Massimo leave Home Assistant too.
- **Entities**:
  - each thermostat's measured temperature, and a radiator thermostat's valve;
  - each window contact's window;
  - every device's battery, and its link and transmit errors (diagnostic);
  - each thermostat's **key lock** as a switch: on locks its buttons,
    written through Massimo's queue, and shown once the thermostat reports it;
  - the Cube's connection, radio duty cycle, free memory slots,
    pending radiograms and queued commands (diagnostic).

  A device's entities are unavailable while its Cube is not connected,
  until it has reported, and while Massimo calls it stale
  (a thermostat silent for 24 hours).
- **Rooms**, from a Massimo with virtual wall thermostats
  (Massimo's feature `vwt`; an older one gets the devices alone, and a warning):
  each room with a thermostat is a device of its own, in its area,
  and stays the room's whatever thermostats come and go in it.
  - Its **`climate`** shows the room's temperature as Massimo computes it:
    its wall thermostat's, else the median of its radiator thermostats
    (the attribute `temperature_sources` says which).
    Modes: `auto` follows the week programme, `heat` holds a setpoint,
    `off` holds 4.5 °C, which the thermostats show as off.
    Presets: `eco` and `comfort` hold the room's eco and comfort
    temperatures, `away` shows vacation mode, `none` goes back to the week
    programme, and `boost` (from a Massimo with the feature `boost`) opens the
    valves for the thermostats' boost time, after which they go back to the
    mode they had.
    Every write goes through Massimo's queue to all thermostats of the room,
    and shows once they report it.
  - **Massimo: Set vacation** (`massimo.set_vacation`) holds a room at a
    temperature until an end, rounded up to the half hour,
    then goes back to its week programme.
  - **Room temperature from** (configuration): the median or the mean of the
    radiator thermostats, for a room without a wall thermostat.
- **Week programmes**, from a Massimo that tags them
  (Massimo's feature `program_etag`), as actions on a room's `climate`:
  - **Massimo: Get week programme** (`massimo.get_program`) answers the
    room's programme, its tag, whether a write to it is still on its way,
    and whether its thermostats agree;
  - **Massimo: Set week programme** (`massimo.set_program`) writes days of
    it, each 1 to 13 switch points such as `{"temp": 21, "until": "07:00"}`,
    the last until 24:00, and answers the new tag;
    given the tag it read, a write over a change made meanwhile
    (in Massimo's web UI, at a thermostat) is refused instead of
    overwriting it;
  - **Massimo: Copy week programme** (`massimo.copy_program`) copies a
    room's programme, or some of its days, to other rooms, or one day of a
    room onto its other days.

  The `climate`'s attributes `program_tag` and `program_changed` say which
  programme the room has and when the integration saw it change.
- **Re-authentication** when the key stops working.

## Setting up

1. In Massimo, create a user with the role **integration** and an API key for
   it: System settings → Users,
   or on the server `massimo user add homeassistant -role integration`.
   The role reads, sets temperatures, locks and configures (week programmes,
   temperatures, device settings), and nothing else.
2. Copy `custom_components/massimo` into Home Assistant's
   `custom_components` directory and restart Home Assistant.
   (Through HACS or the Marketplace once released.)
3. Settings → Devices & services → Add integration → **Massimo**:
   the address at which a browser opens Massimo's web UI, and the key.

Home Assistant 2026.10 or newer.

## Development

The tests run against a real `massimo serve` and Massimo's fake Cube,
not against mocks.
[CONTRIBUTING.md](CONTRIBUTING.md) says how to set up, test, commit
and cut a release.

## Licence

Apache-2.0, as Home Assistant itself.
Massimo is AGPL-3.0; this integration talks to it over HTTP and is a work of its
own.
