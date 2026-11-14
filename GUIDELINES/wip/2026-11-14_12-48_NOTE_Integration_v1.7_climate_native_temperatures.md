# NOTE Integration v1.7: climate's native temperatures

The owner's decisions of 2026-11-14 on what the breno trial found
(NOTE "Integration v1.7: breno trial halted"), and the fix the first asks for.

## Decisions

- **D61-A.** The warnings Home Assistant 2026.11 gives on `climate.py` are
  fixed now, on a branch of their own, with a test, before the first
  release (Block 11).
- **D62-A.** The clone of `distro/devel` on the Pi stays; a `git pull`
  brings it up to date when the trial goes on.

## The fix

Home Assistant 2026.11 names climate's temperatures `native_*`
(`native_temperature_unit`, `native_current_temperature`,
`native_target_temperature`) and warns of an entity that gives an old
name alone, which stops working in 2027.11.
2026.10, which the integration still supports and the tests pin, has no
`native_*` names and reads the old ones.
Where a class gives both, 2026.11 takes the native one without a warning
(`homeassistant.helpers.deprecation.migrate_deprecated_entity_members`),
so `RoomClimate` gives both: the properties as `native_*`, the old names
as aliases of them, and the unit by both `_attr_` names.

`tests/test_rooms.py` checks that a room gives each by both names, with
the same value; on `main`'s `climate.py` it fails.
Imported in the Pi's Home Assistant 2026.11.0 (a copy in the container's
`/tmp`, removed afterwards), the class loads without a warning.

## Since the halt

The owner added the integration by its URL, `http://127.0.0.1:8099`,
in place of the discovered server, and it works.
Discovery overwrites a known entry's URL with the one it finds
(`config_flow.py`, the zeroconf step); with the Pi's announcement on,
before the integration reads the `url` that Massimo's AP IntegrationUsers
adds to the TXT record (its D8-A), the entry would get an address the Pi's
Massimo does not listen on. The Pi's `MASSIMO_ANNOUNCE` stays off until then.
