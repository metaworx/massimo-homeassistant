# AP Integration v1.0: Entities, services, card, release

## TL;DR

The integration gets its entities, services and week-programme card,
is released through HACS and the Marketplace, and replaces the `maxcube`
stopgap on the breno site.
It carries over Blocks 6 to 10 of Massimo's AP HomeAssistant, restated here.

- rooms → nothing in HA → a `climate` per room, presets eco and comfort,
  away for vacation (D4-A of Massimo's plan)
- devices → nothing → sensors (valve, battery, link, window),
  the Cube's diagnostics; pending while radiograms wait, unavailable when stale
- writes → none → setpoints, mode, lock through Massimo's API and its queue;
  week programmes through services
- card → none → the week programme on a pinned copy of Massimo's
  `<massimo-week-program>`, served by the integration (D5-A)
- release → none → a tagged release, HACS and the Marketplace listing
- breno → `maxcube` through the proxy → this integration

### Blocks

1. Entities: `climate` per room, device sensors, the Cube's diagnostics,
   pending and availability
2. Services: `set_program`, `copy_program`, `lock`;
   the programme as a room's attribute
3. Card: the week-programme card on a pinned `week-program.js`,
   served and registered by the integration
4. Release: how a release is cut, the first tag, brand images, topics,
   the listing
5. Breno: installed on the breno Pi, `maxcube` removed, the box's documents

## Discussion

**Where it comes from.**
Massimo's AP HomeAssistant (metaworx/massimo, `GUIDELINES/wip/`) built what
the integration needs in Massimo: event ids and resume, `configure` for the
role `integration`, the week editor as the element `<massimo-week-program>`,
and Massimo's `docs/homeassistant.md` (its Blocks 1 to 4, Massimo's #154),
then this repository with the setup and the event stream (its Block 5).
Its revision v1.1 carried its Blocks 6 to 10 over to a plan of this repository
(D8-A, D9-A, D10-A, 2026-11-12); this plan restates them, numbered 1 to 5 here.

**Decided in Massimo's plan, binding here:**

- **D1-A.**
  One repository for the integration and its card.
- **D4-A.**
  A `climate` entity per room, not per thermostat:
  MAX! thermostats of a room act together, as Massimo's room tiles do.
- **D5-A.**
  The card uses Massimo's own editor element, plain JavaScript, no build step;
  it builds its controls with a kit the card gives it,
  Home Assistant's own (`ha-switch` and the like).
- **D6-A.**
  Apache-2.0.
- **D7-A.**
  The repository is public.

**Open, for this plan's gate:**

- **D1.
  A room's current temperature** where a room has a wall thermostat and radiator
  thermostats
  - **A (recommended).**
    The wall thermostat's: it measures the room,
    the radiators measure beside the heater; Massimo's tiles show the same.
  - **B.**
    The mean of all thermostats: a number no device shows.
- **D2.
  Who owns a setpoint Home Assistant sets**
  (Massimo's design.md section 4: owners `thermostat`, `app`, `loxone`)
  - **A (recommended).**
    Nothing yet: a setpoint from Home Assistant is a manual setpoint as the web
    UI's is;
    an `external` owner with a lease is a plan of Massimo's when an automation
    should hand control back.
  - **B.**
    Wait for that Massimo plan before Block 1.
- **D3.
  How a release is cut**
  (Block 4)
  - **A (recommended).**
    The shared guidelines' `changelog.sh cut` and a signed tag,
    the version in `manifest.json` set by it; HACS reads the tags.
  - **B.**
    GitHub releases by hand.

## Analysis

**The data** is the coordinator's (`coordinator.py`):
the server's Cubes, each with its rooms and their devices as Massimo's API
gives them (`GET …/rooms`; Massimo's `docs/api-v1.md`).
A device has `rf_address`, `serial`, `type` (`radiator_thermostat`,
`radiator_thermostat_plus`, `wall_thermostat`, `shutter_contact`, `eco_switch`),
`name`, `room_id`, `reported`, `stale`, `last_seen` and `state`: `mode` (`auto`,
`manual`, `vacation`, `boost`), `setpoint`, `actual_temp`, `valve_pct`, `until`,
`window_open`, `battery_low`, `error`, `link_error`, `panel_locked`.
A Cube carries `connected`, `budget` (`duty_cycle_pct`, `free_memory_slots`),
`pending_radiograms` and `queued`.
The stream updates a device in place; a change of rooms reads them again.

**Writes** go to Massimo, never to a Cube:
`PUT …/rooms/{id}/setpoint` with `{"mode": "manual", "temp": …}`,
`{"mode": "auto"}` or `{"mode": "vacation", "temp": …, "until": …}`;
it waits for the Cube's answer,
up to two minutes when the radio budget is spent,
and costs about 1.25 % of the hour's duty cycle.
A room's eco and comfort temperatures come from `GET …/rooms/{id}/config`;
week programmes from `GET` and `PUT …/rooms/{id}/program`.
Boost cannot be started over the air.

**Tests** stay against a real `massimo serve` and the fake Cube.
The fake Cube acknowledges a setpoint but changes no state:
a test checks the line the server sends and the entity's pending state,
and feeds state events to the coordinator directly where it needs one.

**The card** takes `week-program.js` from a Massimo release,
pinned by version in this repository,
and gives it a kit of Home Assistant's controls;
its texts are Massimo's `prog.*` keys, copied with the file.

## Implementation Plan

### Block 1: Entities

1. A device per Cube and per thermostat or contact,
   in Home Assistant's device registry, the Cube as the hub.
2. `climate` per room: current temperature (D1), target,
   modes `auto` and `heat`, presets eco and comfort, away for vacation;
   writes through the room's setpoint route.
3. Sensors and binary sensors per device; the Cube's diagnostics.
4. Availability from `stale` and the Cube's `connected`; a pending attribute
   while `pending_radiograms` is above zero.
5. Tests against the server: the entities, a write's line on the fake Cube,
   availability after a disconnect.

**Verification:**
the test gate and lint of the contract; hassfest.

### Block 2: Services

`massimo.set_program`, `massimo.copy_program`, `massimo.lock` with their
schemas and texts; the programme as a room's attribute; tests.

**Verification:**
as Block 1.

### Block 3: Card

The card on a pinned `week-program.js`, the integration serving it and
registering it with the frontend; a test that it is served; a check by hand
in a Home Assistant.

**Verification:**
as Block 1, and the card on a Home Assistant at 1100 and 390 px.

### Block 4: Release

How a release is cut (D3), the changelog's first release, the brand images,
the repository's topics, the HACS and Marketplace listing; CI's HACS check
without its `ignore`.

**Verification:**
the HACS check in CI; an install through HACS.

### Block 5: Breno

On the owner's word in that session:
the integration installed in the breno Pi's Home Assistant,
the `maxcube` YAML removed, the box's documentation updated.

**Verification:**
the rooms in Home Assistant,
a setpoint from Home Assistant seen in Massimo's log.

## Proposed commit message

For the registration:

```
chore(aps): +Integration v1.0

The integration's entities, services, week-programme card and release, and
its use on the breno site: Blocks 6 to 10 of Massimo's AP HomeAssistant,
carried over and restated here.

File-revision-v1: GUIDELINES/wip/2026-11-12_16-45_AP_Integration_entities_services_card_release.md::v1.0::2026-11-12::All::the plan, carried over from Massimo's AP HomeAssistant v1.1
Assisted-by: claude-code:claude-opus-5-5
```

## Change History

- v1.0 (2026-11-12): the plan, carried over from Blocks 6 to 10 of Massimo's
  AP HomeAssistant v1.1.
