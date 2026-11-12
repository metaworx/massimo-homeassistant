# AP Integration v1.2: Entities, services, card, release

## TL;DR

The integration gets its devices, entities, services and week-programme card
on Massimo's room thermostat, is released through HACS and the Marketplace,
and replaces `maxcube` on breno.
What needs Massimo waits for Massimo's AP RoomApi on its main,
then is built as specified - never half-way.

- devices → none → the Cube as hub; a device per real device, its area
  suggested; a room device per virtual wall thermostat (VWT),
  `<cube>:<room_uid>`
- room → nothing → a `climate` on its VWT: Massimo's room temperature;
  presets eco, comfort, away, boost; `off` as 4.5 °C
- device entities → none → sensors, binary sensors, key-lock switch,
  the Cube's diagnostics, availability
- programmes → none → get, set, copy with Massimo's ETag (`412` → reload);
  `program_changed`
- card → none → Massimo's element from the connected server (its AGPL stays
  there)
- release → none → `changelog.sh cut`, a signed tag, a GitHub release
- what a server supports → `features` in `/healthz` (D12, asked of Massimo)

### Blocks

1. Devices and their entities (now), on `?devices=real`
2. Release mechanics (now): the cut, `manifest.json`, `CONTRIBUTING.md`
3. Rooms: room device on its VWT, `climate`, `set_vacation`,
   `temp_method` (waits: Massimo's VWT, boost, fake Cube)
4. Programmes: get, set, copy with the ETag, `program_changed`
   (waits: Massimo's ETag)
5. Card (waits: Block 4)
6. First release: brand images, topics, the HACS check, the tag, the
   listings
7. Breno, on the owner's word there

## Discussion

**Where it comes from.**
Massimo's AP HomeAssistant (metaworx/massimo) built what the integration needs
in Massimo - event ids and resume, `configure` for the role `integration`, the
week editor as the element `<massimo-week-program>` - and this repository with
the setup and the event stream.
Its revision v1.1 carried its Blocks 6 to 10 over to this plan (2026-11-12),
restated here.
This plan's gates since then asked Massimo for a room thermostat, boost over
the air, the last temperature kept, a programme ETag, a fake Cube that applies
writes, and a feature list:
Massimo's AP RoomApi v1.0 (2026-11-13) specifies all but the feature list,
which is with Massimo's owner.

**Decided in Massimo's plan, binding here:**
one repository for the integration and its card;
a `climate` per room, not per thermostat;
the card uses Massimo's own editor element, plain JavaScript, no build step,
with a kit of Home Assistant's controls;
Apache-2.0; the repository is public.

**Decided at this plan's gates (2026-11-12 and 13):**

- **D1-C.**
  A room's temperature: the wall thermostat's, else the median of its radiator
  thermostats.
  Now computed by Massimo, as its VWT's `actual_temp` (D10).
- **D2-A.**
  A setpoint from Home Assistant is a manual setpoint, as the web UI's is.
- **D3-A.**
  A release: `changelog.sh cut`, which writes `manifest.json`'s `version`;
  a signed tag `v<version>`; a GitHub release from the tag, its text the
  release's changelog section (`changelog.sh notes`).
  HACS offers GitHub releases, not bare tags.
- **D4-A.**
  The card's editor is fetched from the Massimo server the entry is connected
  to and passed on by a view of the integration:
  `week-program.js` is AGPL-3.0-or-later, as all of Massimo, and stays there.
- **D5-A.**
  `massimo.get_program` returns a room's programme with its ETag
  (a service response);
  the `climate` carries `program_changed`, the time it last saw the programme
  change, so that the card knows when to read it again.
- **D6-A.**
  A `switch` "Key lock" per real thermostat, in the configuration category.
- **D7-A.**
  `away` shows a room in vacation mode;
  vacation is set through `massimo.set_vacation`.
- **D8-A.**
  Boost over the air, once Massimo accepts it (its AP RoomApi, Block 10).
- **D9-A.**
  The last measured temperature is kept by Massimo, with its time.
- **D10-A.**
  Each room is a device backed by its VWT, read with `?devices=all`;
  real wall thermostats are devices of their own.
- **D11-A.**
  Programme writes carry `If-Match` with the programme's ETag;
  `412` means it changed meanwhile, and the card offers a reload.
- **D12-A.**
  What a server supports is read from `features` in `/healthz`,
  asked of Massimo on 2026-11-13; until Massimo decides, Block 3 waits on it
  too.
- **Areas.**
  Every device suggests its room's name as its area;
  Home Assistant matches or creates the area, once, and the areas stay the
  owner's.
- **Never half-way** (the owner, 2026-11-13).
  A step that needs Massimo waits until Massimo has it on its main,
  where CI's tests run, and is then built as Massimo specifies.

## Analysis

**The data** is the coordinator's (`coordinator.py`):
the server's Cubes, each with its rooms and their devices
(`GET …/rooms`; Massimo's `docs/api-v1.md`).
A device has `rf_address`, `serial`, `type` (`radiator_thermostat`,
`radiator_thermostat_plus`, `wall_thermostat`, `shutter_contact`,
`eco_switch`), `name`, `room_id`, `reported`, `stale`, `last_seen`,
`received` and `state`:
`mode`, `setpoint`, `actual_temp`, `valve_pct`, `until`, `window_open`,
`battery_low`, `error`, `link_error`, `panel_locked` (present when true).
`state` is absent until the device has reported.
A Cube carries `name`, `firmware`, `connected`,
`budget` (`duty_cycle_pct`, `free_memory_slots`), `pending_radiograms` and
`queued`.
A `state` event carries the whole device; a change of rooms, names or devices
reads them again.

**Massimo's views** (AP RoomApi, A2):
`?devices=default|real|virtual|all` on `GET …/rooms`, `GET …/devices` and the
event stream; an older Massimo ignores the parameter.
`default` will show a VWT in a room without a real wall thermostat;
Block 1 asks for `real`, so that no VWT reaches it before Block 3 knows what
one is -
on the stream too, where an unknown device's `state` would read the rooms
again at every event.
Block 3 moves to `all`.

**The VWT** (AP RoomApi, A2):
`virtual: true`, type `wall_thermostat`, serial `VWT` and the room number,
`room_uid` (a UUID, never reused), its state computed by Massimo
(`actual_temp`, `mode` with boost while any thermostat boosts, `setpoint`,
`until`, `valve_pct` the highest, `window_open`, `consistent`, `sources`,
`stale`);
setpoint, programme and room config go to its room;
its setting `temp_method` (`median`, `mean`) needs `configure`.

**Writes** go to Massimo, never to a Cube.
A write waits for the Cube's answer, up to two minutes when the radio budget
is spent; the client's ten-second timeout is for reads.
An `Idempotency-Key` makes the one retry after a lost answer safe:
the server answers the first request's outcome and sends nothing again.
`{"ok": true, "discarded": true}` means the Cube discarded the command.
The key lock: `PUT …/devices/{rf}/lock` with `{"locked": …}`;
the device's next report shows `panel_locked`.
The role `integration` has `read`, `setpoint`, `lock` and `configure`.

**Availability.**
The coordinator marks its data as not current when a stream breaks.
A stream that opens again and has nothing to resume sends nothing,
so the data stayed not current until the next event:
the client now reports the stream's opening, and the coordinator takes it
as current again.

**Brand images.**
Home Assistant 2026.10 serves a custom integration's images from its
`brand/` directory (`icon.png`, `logo.png`, their `@2x` and `dark_`
forms; `homeassistant/components/brands`).
Which image, and under which licence, is the owner's (D13);
HACS's brand check on that directory is seen only in CI.

**Tests** stay against a real `massimo serve` and the fake Cube.
Today's fake Cube acknowledges a write and changes no state;
Massimo's #197 (AP RoomApi, Block 1) makes it apply them, with a control port
and the fixtures Blocks 3 and 4 need.

## Implementation Plan

### Block 1: Devices and their entities

1. **The client:** `rooms` and `events` ask for `?devices=real`;
   `events` yields an `open` event once the stream answers;
   writes (`_write`) with an `Idempotency-Key`, a timeout of 130 s,
   one retry with the same key after a lost answer,
   and a discarded command as an error;
   `set_lock`.
2. **The coordinator:** an `open` event makes its data current again;
   after each read of a Cube's rooms, a device the Cube no longer lists
   leaves the device registry;
   `async_remove_config_entry_device` lets the owner remove one that is gone.
3. **Devices:**
   the Cube as the hub (serial, name, firmware, the server's URL);
   a device per real device (serial, type as model, eQ-3),
   `via_device` its Cube, its area suggested by its room's name.
4. **Entities follow the data:**
   a device that appears after a refresh gets its entities then,
   without a reload.
5. **Sensors and binary sensors:**
   per thermostat the measured temperature and, for radiator thermostats,
   the valve;
   per device the battery, the window for a shutter contact,
   link and transmit errors (diagnostic);
   per Cube: connected, duty cycle, free memory slots, pending radiograms,
   queued commands (diagnostic).
6. **Key lock** (D6): a `switch` per thermostat, configuration category.
7. **Availability:** an entity is unavailable while its Cube is not connected
   or the stream is down, and a device's while it has not reported or is
   stale.
8. **Texts** in `strings.json`, `en.json` and `de.json`;
   a refused write raises a translated `HomeAssistantError`.
9. **Tests** against the server: devices and their areas, the entities'
   values, the key lock's command, availability after `disconnected` and
   after a broken stream, a device appearing and leaving with the data.
10. **CHANGELOG fragment** under `Added`.

**Verification:**
the test gate and lint of the contract; hassfest.

### Block 2: Release mechanics

1. `manifest = custom_components/massimo/manifest.json` for `CHANGELOG.md`
   in `GUIDELINES/config.ini`, so that `changelog.sh cut` writes its
   `version`.
2. `CONTRIBUTING.md`, which the contract names and which does not exist yet:
   the development set-up (Python 3.14 through `uv`, a `massimo` from
   Massimo's checkout), the test gate, lint, hassfest,
   the changelog's fragments, and how a release is cut (D3).

**Verification:**
`changelog.sh check`; a dry run of `changelog.sh cut`;
`check-citations.sh`.

### Block 3: Rooms

Waits for Massimo's VWT, boost and fake Cube on Massimo's main,
and for D12.

1. `?devices=all`; a device per room, backed by its VWT
   (`<cube serial>:<room_uid>`), its area suggested by its name.
2. A `climate` per room on its VWT: current temperature and its sources,
   target, step 0.5, the range of the room's `min_setpoint` and
   `max_setpoint`;
   modes `auto`, `heat` (manual), `off` (manual 4.5 °C);
   `hvac_action` heating while a valve is open;
   presets `eco` and `comfort` (manual at the room's temperatures),
   `away` while in vacation (D7), `boost` (D8);
   `consistent` and the Cube's pending radiograms as attributes.
3. `massimo.set_vacation` (temperature and end, on the half hour).
4. `temp_method` as a configuration `select` on the room device.
5. Writes through the VWT's routes; Massimo's `features` required.
6. Tests on the fake Cube's fixture `rooms`, its writes applied, its control
   port: the median, boost and its end, a wall thermostat removed and back
   with the room's device unchanged, a stale thermostat.

**Verification:**
as Block 1.

### Block 4: Programmes

Waits for Massimo's ETag on its main.

1. `massimo.get_program` (D5): the programme, its ETag, `pending`,
   `program_consistent`.
2. `massimo.set_program` with `If-Match` (D11), checked as Massimo checks it
   (1 to 13 points, increasing, the last at 24:00);
   `massimo.copy_program` (a room's programme to other rooms, or a day to
   other days).
3. `program_changed` on the room's `climate`, from the `config` event's
   `changed` and `etag`.
4. Schemas in `probatio`, `services.yaml`, texts; tests, a `412` included.

**Verification:**
as Block 1.

### Block 5: Card

1. A view that passes on Massimo's `week-program.js` and its translations
   from the entry's server, kept per Massimo version (D4).
2. `massimo-week-program-card.js`: picks a room, reads its programme,
   gives the element a kit of Home Assistant's controls,
   sends the changed days with the ETag, offers a reload on `412`;
   a card editor to choose the room.
3. The integration serves the card and adds it to the frontend
   (`add_extra_js_url`).
4. Tests that both are served; a check by hand.

**Verification:**
as Block 1, and the card on a Home Assistant at 1100 and 390 px.

### Block 6: First release

1. The brand images in `custom_components/massimo/brand/` (D13).
2. The repository's topics; CI's HACS check without its `ignore`
   (whose comment still names Massimo's Block 9).
3. The first release by D3, its tag and GitHub release;
   the listing in HACS's default repositories and the Marketplace.

**Verification:**
the HACS check in CI; an install through HACS.

### Block 7: Breno

On the owner's word in that session:
the integration installed in the breno Pi's Home Assistant,
the `maxcube` YAML removed, the box's documentation updated.

**Verification:**
the rooms in Home Assistant,
a setpoint from Home Assistant seen in Massimo's log.

## Open

- **D13.
  The brand image** (Block 6)
  - **A (recommended).**
    Massimo's app icon, under a licence its owners give this repository
    for it.
  - **B.**
    An icon of its own, made for the integration.

## Proposed commit message

For the revision, committed on its own before Block 1:

```
chore(aps): +Integration v1.2

The plan on Massimo's room thermostat, as Massimo's AP RoomApi specifies it: what needs Massimo waits for it, the rest is done now, never half-way; every decision of its gates recorded, D13 open.

File-revision-v1: GUIDELINES/wip/2026-11-12_16-45_AP_Integration_entities_services_card_release.md::v1.2::2026-11-13::TL;DR, Discussion, Analysis, Implementation Plan, Open, Proposed commit message, Change History::D1 to D12 settled, the VWT, seven blocks
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
- v1.2 (2026-11-13): on Massimo's room thermostat (its AP RoomApi v1.0).
  D1 to D12 settled (D1-C, the rest A), areas suggested, nothing half-way;
  the room as a device on its VWT, the programme's ETag, features from
  `/healthz`.
  Seven blocks: devices and release mechanics now; rooms, programmes and the
  card waiting for Massimo; brand images, topics and the HACS check moved to
  the first release, for D13 and for a check only CI makes.
  A stream that opens again makes the data current.
