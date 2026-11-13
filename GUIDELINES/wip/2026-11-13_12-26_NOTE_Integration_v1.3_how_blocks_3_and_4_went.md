# NOTE Integration v1.3: how Blocks 3 and 4 went

The `PLAN++` run of 2026-11-13, Blocks 3 (rooms) and 4 (boost),
and where it went differently from v1.3.

## Where the work differs from the plan

1. **A room gets a device only where it has a thermostat**,
   not every room as Block 3's step 3 says.
   Home Assistant registers a device through its entities,
   and a room without a thermostat has nothing to control:
   the fixture's room 3, a window contact alone, has no room device,
   its contact being a device of its own in the room's area.
   A room that loses its last thermostat keeps its device,
   its `climate` unavailable.
2. **`off` holds 4.5 °C**, MAX!'s off, not the room's minimum setpoint as
   Block 3's step 4 says: a thermostat shows off at 4.5 °C only,
   whatever its minimum.
3. **The rooms in the tests are found by id**, not by name:
   `tests/test_init.py` renames the fixture's first room with a thermostat.

## Found on the way

None in the code of earlier blocks.
