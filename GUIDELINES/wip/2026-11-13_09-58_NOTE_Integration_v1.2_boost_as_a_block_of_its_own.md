# NOTE Integration v1.2: boost as a block of its own

The owner's decision of 2026-11-13, for Block 3 (rooms).

## Decision D16-A

Block 3 builds the rooms with everything but the preset `boost`:
the room device on its virtual wall thermostat, its `climate` with the modes,
the presets `eco`, `comfort` and `away`, `set_vacation`, and `temp_method`.
`boost` becomes a block of its own, after Block 3,
once boost over the air is on Massimo's `main`.

## Why

Every block is then whole and tested against a Massimo that has what it
uses; the rooms do not wait for boost.

On 2026-11-13 Massimo's AP RoomApi had the virtual wall thermostat,
the kept temperature and the programme's ETag on `main`
(metaworx/massimo #200, #204, #205);
boost, tested on the owner's Cube, was its pull request #206, still open.

## What follows for the next revision

- Block 3 without `boost`; a new block for `boost` after it, waiting for
  Massimo's boost on `main`.
- Block 3 still waits for D12 (`features` in `/healthz`),
  which Massimo's owner has not decided: the next revision says how Block 3
  tells a Massimo with virtual wall thermostats from one without, if D12 is
  not there by then.
