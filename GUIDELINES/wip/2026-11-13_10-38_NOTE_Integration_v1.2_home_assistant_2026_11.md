# NOTE Integration v1.2: Home Assistant 2026.11

The integration checked against Home Assistant 2026.11.1 on 2026-11-13,
by its source, for the two changes the marketplace NOTE names and for what
else the integration uses.
Its tests cannot run on 2026.11 yet (below).

## Found, and fixed

**A device named its Cube by identifier** (`DeviceInfo(via_device=…)`),
which 2026.10 already reports as deprecated and 2027.8 removes;
2026.11 keeps it on its new `DeviceInfo` dataclass only for that time.
The Cubes' devices are now registered when the entry is set up,
and each device names its Cube by the Cube's device id (`via_device_id`),
which 2026.10 and 2026.11 both take.

## Found, and left as it is

- **`async_setup_entry` returns `True`.**
  2026.11 asks for `None` and ignores a boolean from a custom integration;
  2026.10 logs an error for anything but a boolean and fails the setup.
  `True` stays while the integration supports 2026.10;
  `None` once it requires 2026.11.
  `async_unload_entry` returns the unload's boolean, as both versions take.
- **`DeviceInfo` as a dataclass.**
  The integration builds it with keyword arguments only, which the dataclass
  takes; the Cube's device is registered with the same fields as keyword
  arguments, not as the `DeviceInfo` object.
- **Nothing else** the integration imports changed in a way it uses:
  the config flow, the coordinator, the entity platforms, the sensor,
  binary sensor and switch components, the exceptions with translations, the
  zeroconf service info, `probatio` (0.13.0 in both).
  2026.11's opt-in to changing an entity's id in place
  (until 2027.11) is optional, and not taken.

## Not yet possible

The tests on 2026.11: `pytest-homeassistant-custom-component` is at 0.13.375,
for 2026.10.4.
With 2026.11.1 put in its place, the harness does not load:
it imports `httpx` before Home Assistant, which 2026.11 refuses
("httpx was already imported; call `alias_httpx()` before any
`import httpx`").
They wait for the harness's version for 2026.11.
