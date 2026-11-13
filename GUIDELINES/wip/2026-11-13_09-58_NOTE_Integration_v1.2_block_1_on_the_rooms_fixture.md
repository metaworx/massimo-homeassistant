# NOTE Integration v1.2: Block 1 on the rooms fixture

How Block 1's tests changed after the block, on 2026-11-13,
once Massimo's fake Cube carried out what it acknowledges
(Massimo's AP RoomApi, Block 1, on its `main`).

## What changed

- **The fixture:** `tests/conftest.py` starts the fake Cube on Massimo's
  fixture `rooms`, with its control port, instead of the recorded greeting;
  `MASSIMO_GREETING` is no longer read, in the tests, CI, the contract or
  `CONTRIBUTING.md`.
- **New tests:** a wall thermostat (its model, temperature and key lock,
  no valve); the key lock shown on once the thermostat reports it locked,
  and off again; a report set through the control port reaching its sensor,
  and a device the Cube holds no state for unavailable until it reports.
- **The tests' own reads** use `?devices=real`, as the integration does.

## Found on the way

Two tests failed against Massimo's `main` of 2026-11-13, not the
integration:
Massimo's default view now adds a virtual wall thermostat to each room
without a real one, and the tests read that view.
One expected a device for `VWT0000001`;
the other locked it and got `409`.
CI on `main` would have failed the same way at its next run.

## Not changed

The integration's code. It reads `?devices=real` since Block 1.
