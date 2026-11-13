# NOTE Integration v1.2: release through the marketplace

The owner's decision of 2026-11-13, for Block 6 (first release).

## Decision D15-A

The first release is published in Home Assistant's Marketplace,
and `hacs.json` stays for Home Assistant 2026.10, where HACS still installs.

## Why

Home Assistant 2026.11 (released 2026-11-04) ends HACS:
its release notes say "The HACS installer stops at Home Assistant 2026.11"
and send publishers to the Marketplace.
Block 6 as v1.2 states it plans a HACS listing and CI's HACS check;
the Marketplace takes their place, with HACS kept for those still on 2026.10,
which the integration supports.

## What follows for the next revision

- Block 6: the Marketplace's publisher requirements, read when the block is
  revised; the manifest's category, which 2026.11 introduces for the
  Marketplace (presumably the climate one); the HACS check in CI kept as long
  as `hacs.json` is.
- The tests on 2026.11 as well, once `pytest-homeassistant-custom-component`
  publishes a version for it (its newest on 2026-11-13 is 0.13.375, for
  2026.10.4).
- Two 2026.11 developer changes to check the code against:
  config entry functions returning `None`, and `DeviceInfo` as a dataclass
  (the integration builds it with keyword arguments only).
