# Massimo for Home Assistant

A Home Assistant integration for [Massimo](https://github.com/metaworx/massimo),
the server that holds eQ-3 MAX!
Cubes: Massimo keeps the Cubes, their radio budget, pairing and week programmes,
and Home Assistant becomes one more client of its HTTP API,
beside Massimo's own web UI and apps.

> **Not ready for use yet.**
> It sets up a Massimo server, follows its Cubes,
> and shows their devices with their sensors and key locks;
> it sets no temperatures yet.
> Rooms as `climate` entities, services and a week-programme card follow,
> once Massimo has the room thermostat they are built on.
> Until then, Home Assistant's own MAX! integration can control the Cube through
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
Build `massimo` from [metaworx/massimo](https://github.com/metaworx/massimo)
and point the tests at it and at the fake Cube's recorded greeting:

```bash
uv python install 3.14
uv venv --python-preference only-managed --python 3.14 .venv
VIRTUAL_ENV=.venv uv pip install -r requirements_test.txt
MASSIMO_BIN=/path/to/massimo \
MASSIMO_GREETING=/path/to/massimo-repo/tools/ui-test/greeting.txt \
.venv/bin/python -m pytest
```

Without `MASSIMO_BIN` and `MASSIMO_GREETING` the tests that need a server are
skipped; CI sets `MASSIMO_REQUIRED=1`, which fails them instead.
Lint with `ruff check` and `ruff format --check`.

## Licence

Apache-2.0, as Home Assistant itself.
Massimo is AGPL-3.0; this integration talks to it over HTTP and is a work of its
own.
