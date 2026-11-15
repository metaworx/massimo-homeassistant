# NOTE SetupPolish v1.0: how the run went

The `PLAN++` run of 2026-11-15, Blocks 1 to 4, and where it went
differently from v1.0.

## Where the work differs from the plan

1. **The default name of a typed address** is "Massimo <host>" even where
   the host is an IP address ("Massimo 192.168.178.8"): it is a default in
   an editable field, and the address says more than "Massimo" alone.
2. **A registered entry follows the record's `url` only where it
   answered**; where the discovery fell back to the host and port found,
   only an entry whose address came from an announcement takes them.
3. **A title renamed by hand stays in reconfiguration too**, even where a
   new name is chosen there; the name is kept in the data, and the title
   follows it again once the hand-made one is renamed back.
4. **The server's device** is manufacturer "Massimo", model "Server", as
   the rooms are "Massimo", "Room"; its name is the entry's name.
   It cannot be removed by hand while its entry is set up.
5. **The Cubes name the server by its device id** (`via_device_id`), as
   the devices name their Cubes, since the identifier form is to go in
   Home Assistant 2027.8.

## Checks

- 88 tests against `massimo serve` built from Massimo's `main` at e9ab849,
  ruff 0.17.4, hassfest: all pass.
- `changelog.sh check` reports the problem it reported on `main` before:
  the manifest names 0.1.0 and nothing is cut yet (AP Integration,
  Block 11).
