# AP Integration v1.1: Entities, services, card, release

## TL;DR

The integration gets its entities, services and week-programme card,
is released through HACS and the Marketplace, and replaces the `maxcube`
stopgap on the breno site.
It carries over Blocks 6 to 10 of Massimo's AP HomeAssistant, restated here.

- rooms → nothing in HA → a `climate` per room, on a device per room;
  presets eco, comfort, away (vacation), boost shown
- devices → nothing → sensors (valve, battery, link, window, temperature),
  a key-lock switch (D6), the Cube's diagnostics
- writes → none → setpoints and modes through Massimo's API, with an
  idempotency key and the radio's two-minute wait
- programmes → none → `get_program` (a response, D5), `set_program`,
  `copy_program`, `set_vacation` (D7)
- card → none → Massimo's `<massimo-week-program>`, fetched from the
  connected server, not copied: Massimo is AGPL, this repository Apache (D4)
- release → none → `changelog.sh cut`, a signed tag, a GitHub release (D3)
- breno → `maxcube` through the proxy → this integration

### Blocks

1. Entities: devices, `climate` per room, sensors, key-lock switch,
   diagnostics, availability and pending
2. Services: `get_program`, `set_program`, `copy_program`, `set_vacation`
3. Card: Massimo's element served from the connected server, the card
   around it, registered with the frontend
4. Release: the cut, the first tag and GitHub release, brand images, topics,
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
    `changelog.sh cut`, which also writes `manifest.json`'s `version`
    once `config.ini` names it as the changelog's `manifest`;
    a signed tag `v<version>`;
    a GitHub release from the tag, its text the release's changelog section.
    HACS offers a repository's GitHub releases, not its bare tags.
  - **B.**
    GitHub releases by hand, the version and the changelog kept by hand.
- **D4.
  Where the card's editor comes from**
  (new in v1.1:
  `week-program.js` is AGPL-3.0-or-later, as all of Massimo,
  and this repository is Apache-2.0)
  - **A (recommended).**
    Fetched from the Massimo server the entry is connected to,
    which serves it openly at `/ui/week-program.js`
    with its texts at `/ui/i18n/<lang>.json`;
    the integration passes both on through a view of its own,
    so that the browser needs no route to Massimo.
    No AGPL file in this repository,
    and the editor always matches the server's API.
    Needs a Massimo with the element (0.13.0-alpha.1 or newer);
    the card says so on an older one.
  - **B.**
    A pinned copy, as v1.0 planned,
    with Massimo's owners licensing that file to this repository
    under Apache-2.0 as well, in a plan of Massimo's;
    the card then works offline from Massimo's UI files,
    and every change of the element is a copy here.
  - **C.**
    A pinned copy under its AGPL:
    the card is then AGPL inside an Apache repository,
    which HACS and the README have to explain.
- **D5.
  How the card and automations read a room's week programme**
  - **A (recommended).**
    A service `massimo.get_program` that returns it
    (a service response, which the card calls through the websocket):
    read when asked, never stored.
  - **B.**
    An attribute of the room's `climate`, as v1.0 planned:
    up to 91 switch points recorded with every state change of the room,
    unless left out of the recorder.
- **D6.
  The thermostats' key lock**
  (`panel_locked`, `PUT …/devices/{rf}/lock`)
  - **A (recommended).**
    A `switch` "Key lock" per thermostat, in the configuration category:
    its state shows, and a toggle is one radio command.
  - **B.**
    A service `massimo.lock`, as v1.0 planned: a write without a state.
- **D7.
  The preset `away`** (vacation needs a temperature and an end)
  - **A (recommended).**
    Shown while a room is in vacation mode;
    set through `massimo.set_vacation` with its temperature and end;
    choosing `away` in the climate's dialog is refused, naming the service.
  - **B.**
    `away` sets vacation at the room's eco temperature for a fixed time,
    such as seven days: a choice in the dialog, an end nobody picked.

## Analysis

**The data** is the coordinator's (`coordinator.py`):
the server's Cubes, each with its rooms and their devices as Massimo's API
gives them (`GET …/rooms`; Massimo's `docs/api-v1.md`).
A device has `rf_address`, `serial`, `type` (`radiator_thermostat`,
`radiator_thermostat_plus`, `wall_thermostat`, `shutter_contact`, `eco_switch`),
`name`, `room_id`, `reported`, `stale`, `last_seen` and `state`: `mode` (`auto`,
`manual`, `vacation`, `boost`), `setpoint`, `actual_temp`, `valve_pct`, `until`,
`window_open`, `battery_low`, `error`, `link_error`, `panel_locked`.
`state` is absent until the device has reported (`reported` false).
A room has `ready` and `stale`.
A Cube carries `connected`, `budget` (`duty_cycle_pct`, `free_memory_slots`),
`pending_radiograms` and `queued`.
A `state` event carries the whole device, which the coordinator puts in place;
a change of rooms, names or devices reads them again.
The coordinator follows only the Cubes it found at setup:
a Cube added later takes a reload of the entry.

**Writes** go to Massimo, never to a Cube:
`PUT …/rooms/{id}/setpoint` with `{"mode": "manual", "temp": …}`,
`{"mode": "auto"}` or `{"mode": "vacation", "temp": …, "until": …}`
(`until` `"YYYY-MM-DD HH:MM"`, on the half hour; temperatures 4.5 to 30.5
in steps of 0.5).
It waits for the Cube's answer,
up to two minutes when the radio budget is spent,
and costs about 1.25 % of the hour's duty cycle;
the client's ten-second timeout is for reads, so writes need one of their own.
An `Idempotency-Key` makes a retry after a lost answer safe:
the server answers the first request's outcome and sends nothing again.
Boost cannot be started over the air.
A room's eco and comfort temperatures come from `GET …/rooms/{id}/config`,
which the server answers from its copy, without radio;
a `config` event says they changed.
Week programmes: `GET` and `PUT …/rooms/{id}/program`,
each day 1 to 13 points, the last at 24:00.
The key lock: `PUT …/devices/{rf}/lock` with `{"locked": …}`.
The role `integration` has `read`, `setpoint`, `lock` and `configure`:
all of the above, and nothing that renames, moves or pairs.

**The card's editor** is Massimo's `internal/server/ui/week-program.js`,
a classic script that defines `<massimo-week-program>`,
in Massimo since 0.13.0-alpha.1,
under Massimo's AGPL-3.0-or-later (D4).
It owns the editing and none of the state;
the host gives it a kit (`t`, `elem`, `button`, `switchEl`, `fieldRow`,
`numberInput`, …) and its texts are Massimo's `prog.*`, `day.*` and
`dayShort.*` keys.
Massimo serves it, and its translations, without sign-in.

**Tests** stay against a real `massimo serve` and the fake Cube.
The fake Cube acknowledges a setpoint but changes no state:
a test checks the write's answer and its command on the server
(`GET /api/v1/commands/{id}`), and the entity's pending state,
and feeds state events to the coordinator directly where it needs one.

## Implementation Plan

### Block 1: Entities

1. **Devices** in Home Assistant's device registry:
   the Cube as the hub (serial, firmware, its `connected`);
   a device per room, holding its `climate`;
   a device per thermostat, contact and eco switch (serial, type as model),
   its area suggested by its room's name.
   A device the Cube forgot leaves the registry;
   `async_remove_config_entry_device` lets the owner remove one by hand.
2. **Entities follow the data:**
   a room or device that appears after a refresh gets its entities then,
   without a reload.
3. **Writes in the client:** `set_room_setpoint`, `room_config`,
   `set_lock`, each with an `Idempotency-Key` and a timeout of 130 s;
   a refused write raises `HomeAssistantError` with the server's message.
4. **`climate` per room:**
   current temperature (D1), target, step 0.5, range 4.5 to 30.5;
   modes `auto` (auto), `heat` (manual), `off` (manual 4.5 °C);
   `hvac_action` heating while a valve is open;
   presets `eco` and `comfort` (manual at the room's temperatures),
   `away` while in vacation (D7), `boost` shown while boosting, never set.
5. **Sensors and binary sensors per device:**
   valve, temperature where the device reports one, battery, link error,
   transmit error, window; diagnostics of the Cube:
   duty cycle, free memory slots, pending radiograms, queued commands,
   connected.
6. **Key lock** per thermostat as D6 decides.
7. **Availability and pending:**
   a device's entities unavailable while it has no state or is `stale`,
   and all of a Cube's while it is not connected or its stream is down;
   the room's `climate` carries `pending` while the Cube has radiograms
   waiting.
8. **Texts** in `strings.json`, `en.json` and `de.json`: entity names,
   presets, the errors.
9. **Tests** against the server: the entities and devices of the fake Cube,
   a setpoint's answer and command, a preset, availability after a
   `disconnected` event, an entity appearing after a refresh.

**Verification:**
the test gate and lint of the contract; hassfest.

### Block 2: Services

1. `massimo.get_program` (D5), `massimo.set_program` (a week programme,
   any subset of days, checked as the API checks it: 1 to 13 points,
   increasing, the last at 24:00), `massimo.copy_program` (one room's
   programme to other rooms, or one day to other days),
   `massimo.set_vacation` (temperature and end, D7),
   and `massimo.lock` where D6 chooses B.
2. Each targets a room's `climate` entity, with its schema in `probatio`,
   its `services.yaml` and its texts;
   a programme written is read again after the server's `config` event.
3. Tests: each service's answer and command against the server,
   a programme refused for its points.

**Verification:**
as Block 1.

### Block 3: Card

1. A view of the integration that serves Massimo's `week-program.js` and
   its translations, fetched from the entry's server and kept per Massimo
   version (D4-A); or the pinned copy (D4-B, C).
2. The card, `massimo-week-program-card.js` in this repository:
   picks a room's `climate`, reads its programme (D5), gives the element a
   kit of Home Assistant's controls, and sends the changed days with
   `massimo.set_program`; a card editor to choose the room.
3. The integration serves the card and adds it to the frontend
   (`add_extra_js_url`), so that nothing is installed by hand.
4. A test that both are served, and that an older Massimo without the
   element is answered as such; a check by hand in a Home Assistant.

**Verification:**
as Block 1, and the card on a Home Assistant at 1100 and 390 px.

### Block 4: Release

1. How a release is cut (D3): `manifest` for `CHANGELOG.md` in `config.ini`,
   the steps in `CONTRIBUTING.md`.
2. The brand images where Home Assistant 2026.10 takes them for a custom
   integration, the repository's topics, CI's HACS check without its
   `ignore` (whose comment still names Massimo's Block 9).
3. The first release, `0.1.0`, its tag and GitHub release;
   the listing in HACS's default repositories and the Marketplace.

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

For the revision, committed with the run that executes it:

```
chore(aps): +Integration v1.1

The card's editor fetched from the connected Massimo rather than copied, since Massimo is AGPL and this repository Apache; the programme read through a service response; the key lock as a switch; vacation through a service; writes with an idempotency key and a timeout of their own; releases as GitHub releases, which HACS offers.

File-revision-v1: GUIDELINES/wip/2026-11-12_16-45_AP_Integration_entities_services_card_release.md::v1.1::2026-11-12::TL;DR, Discussion, Analysis, Implementation Plan, Proposed commit message, Change History::D4 to D7 new, D3 corrected, Blocks 1 to 4 in steps
Assisted-by: claude-code:claude-opus-5-5
```

## Change History

- v1.0 (2026-11-12): the plan, carried over from Blocks 6 to 10 of Massimo's
  AP HomeAssistant v1.1.
- v1.1 (2026-11-12): checked against the code and Massimo's API.
  New decisions D4 (the card's editor fetched from the server, for its AGPL),
  D5 (the programme as a service response), D6 (key lock as a switch),
  D7 (vacation through a service); D3 corrected: HACS offers GitHub releases,
  not bare tags.
  Blocks 1 to 4 in steps: devices per room, entities after a refresh,
  writes with an idempotency key and a timeout of 130 s, `off` as 4.5 °C,
  the diagnostics; the comment in CI naming Massimo's Block 9.
