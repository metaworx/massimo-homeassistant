# AP Integration v1.4: Entities, services, card, release

## TL;DR

The integration gets its rooms, services and week-programme card on
Massimo's room thermostat, is released through the Marketplace,
and replaces `maxcube` on breno.
Each block requires the Massimo feature it uses, by name, from `/healthz`.

- devices, release mechanics, rooms, boost, programmes → done (Blocks 1-5)
- brand images → none → the mark (`grayorange`, the "i" dotted orange) in
  `custom_components/massimo/brand/`, from Massimo's `tools/brand/`,
  trimmed to the mark (D27-A), now (D28-A)
- card → none → Massimo's element from the connected server
- release → none → `changelog.sh cut`, a signed tag, a GitHub release, the
  Marketplace; HACS kept for 2026.10

### Blocks

1. Devices and their entities - done
2. Release mechanics - done
3. Rooms: room devices, `climate`, `set_vacation`, `temp_method` - done
4. Boost: the preset `boost` - done
5. Programmes: get, set, copy with the ETag, `program_changed` - done
6. Brand images: Massimo's tool trims them; the eight in `brand/`
7. Card: Massimo's element served from the connected server
8. First release: the Marketplace, the tag
9. Breno, on the owner's word there

## Discussion

**Where it comes from.**
Massimo's AP HomeAssistant built what the integration first needed in
Massimo, and carried its Blocks 6 to 10 over to this plan (2026-11-12).
This plan's gates then asked Massimo for a room thermostat, boost over the air,
the last temperature kept, a programme ETag, a fake Cube that applies writes,
and a feature list; Massimo's AP RoomApi built them all,
on Massimo's `main` by 2026-11-13 (its #197, #200, #204 to #206, #210).

**Decided in Massimo's plan, binding here:**
one repository for the integration and its card;
a `climate` per room, not per thermostat;
the card uses Massimo's own editor element, plain JavaScript, no build step,
with a kit of Home Assistant's controls;
Apache-2.0; the repository is public.

**Decided at this plan's gates (2026-11-12 and 13):**

- **D1-C.**
  A room's temperature: its wall thermostat's, else the median of its
  radiator thermostats; computed by Massimo as its VWT's `actual_temp`.
- **D2-A.**
  A setpoint from Home Assistant is a manual setpoint, as the web UI's is.
- **D3-A.**
  A release: `changelog.sh cut`, which writes `manifest.json`'s `version`;
  a signed tag `v<version>`; a GitHub release from the tag.
- **D4-A.**
  The card's editor is fetched from the Massimo server the entry is connected
  to: `week-program.js` is AGPL-3.0-or-later and stays in Massimo.
- **D5-A.**
  `massimo.get_program` returns a room's programme with its ETag;
  the `climate` carries `program_changed`.
- **D6-A.**
  A `switch` "Key lock" per real thermostat.
- **D7-A.**
  `away` shows a room in vacation mode; vacation is set through
  `massimo.set_vacation`.
- **D8-A.**
  Boost over the air (Massimo's AP RoomApi, Blocks 9 and 10).
- **D9-A.**
  The last measured temperature is kept by Massimo.
- **D10-A.**
  Each room is a device backed by its VWT, read with `?devices=all`;
  real wall thermostats are devices of their own.
- **D11-A.**
  Programme writes carry `If-Match`; `412` offers a reload.
- **D12-A.**
  What a server supports is `features` in `/healthz`:
  each name with a version `"MAJOR.MINOR"`, the minor rising with a
  compatible addition, the map the running server's.
- **D13-Z4, as chosen since** (2026-11-13).
  One mark for Massimo and the integration, which the owner, as the licence
  holder of both, allows the integration to carry under Apache-2.0:
  a bold M with round corners in Massimo's blue (`#1F63C6`; `#5B95EC` on dark
  backgrounds), its V at a right angle, a thermometer cut out of each leg with
  a five-step scale.
  The chosen flavour is `grayorange`: a gray M behind (`#8F8F8F`; `#555555`
  on dark backgrounds), so that every cut-out shows gray on any page;
  the minute hand the MAX! logo's exclamation mark and the hour hand a
  capsule, both orange (`#ED6E21`), the hub's square turning with the minute
  hand; the logo the mark as the M of "Massimo", its "i" dotted orange,
  in Lato Regular.
  The generator is Massimo's `tools/brand/make_brand.py` (its AP Brand,
  #215); this repository carries only the images it makes.
- **D15-A.**
  The first release is published in Home Assistant's Marketplace;
  `hacs.json` stays for Home Assistant 2026.10, where HACS still installs,
  2026.11 having ended the HACS installer.
- **D16-A.**
  Boost is a block of its own after the rooms
  (decided while Massimo's boost waited; kept for two smaller changes).
- **D20-A.**
  This session writes the plan's revisions.
  v1.4 was written by the session that designed the mark, on the owner's
  `PLAN++` there.
- **D27-A.**
  Home Assistant's brand images are trimmed to the mark, as its brand rules
  ask: Massimo's tool does it in its `homeassistant` scope.
- **D28-A.**
  The brand images come now, a block of their own before the card,
  not with the first release.
- **D29-A.**
  That block is done in a worktree of its own, on a branch from `origin/main`.
- **Areas.**
  Every device suggests its room's name as its area, once;
  the areas stay the owner's.
- **Never half-way** (the owner, 2026-11-13).
  A step that needs Massimo waits until Massimo has it on its `main`,
  and is then built as Massimo specifies.

## Analysis

**What a server supports** (Massimo's `docs/api-v1.md`, `GET /healthz`):
`features` names `event_ids`, `idempotency`, `commands`, `vwt`,
`program_etag`, `boost`, `proxy_virtual`, each `"1.0"` today;
a server without a store leaves out `idempotency`, `commands` and
`proxy_virtual`; a server without the field has none.
The coordinator reads it with the health it already reads.
A block's entities need its feature's major 1;
the client retries a lost write only where `idempotency` is listed.

**Rooms** (`?devices=all`, measured on the fake Cube's fixture `rooms`):
each room carries `room_uid`, and lists its VWT first among its devices -
`rf_address` the room number (`000002`), serial `VWT` and the number,
`virtual: true`, type `wall_thermostat`.
Its `state` has `mode`, `setpoint`, `until`, `actual_temp`, `valve_pct`
(the highest), `consistent`, and `sources` (the addresses `actual_temp` and
`mode` came from).
A room without a thermostat has a VWT that is `reported: false`,
its state `window_open` alone: it gets no `climate`.
`GET …/devices/{vwt}` adds the room's configuration under `wall_thermostat`
(`comfort_temp`, `eco_temp`, `min_setpoint`, `max_setpoint`, the boost
settings, the week programme), `settings` (`temp_method`) and `etag`,
from the server's copy, without radio.
`PUT …/devices/{vwt}/setpoint` takes `manual` with `temp`, `auto`,
`vacation` with `temp` and `until` (`"YYYY-MM-DD HH:MM"`, on the half hour)
and `boost`; the fake Cube carries each out at its next device list.
`PUT …/devices/{vwt}/config` with `{"temp_method": "mean"}` answers its
settings and sends a `config` event with `changed: ["settings"]`.
The event stream with `?devices=all` sends the VWT's `state` and `config`
events.
The real devices' entities leave the VWTs out by `virtual`.

**Home Assistant's climate** (2026.10):
`HVACMode` `auto`, `heat`, `off`; `HVACAction` `heating`, `idle`, `off`;
presets `eco`, `comfort`, `away`, `boost`, `none`;
`ClimateEntityFeature` `TARGET_TEMPERATURE`, `PRESET_MODE`, `TURN_ON`,
`TURN_OFF`; an invalid mode raises `ServiceValidationError`.
An entity service is registered on the platform with a `probatio` schema,
as core's climate integrations do.

**Brand images** (Home Assistant 2026.10, `homeassistant/components/brands`):
a custom integration's `brand/` holds `icon.png`, `logo.png`, their `@2x`
and their `dark_` ones; a missing one falls back (`logo` to `icon`, `dark_` to
the light one); Home Assistant serves them through its brands view, and the
loader says `has_branding` where `brand/` is there.
Its code checks the names, not the sizes; the brand rules ask for an icon of
1:1 at 256 px (512 at `@2x`), a logo whose short side is 128 to 256 px,
transparent, trimmed.
Massimo's tool writes them from its drawing; its images of #215 keep a
margin (13 px left and right, 22 px top and bottom of the icon at 256 px).
Its v1.1.0, on the branch `claude/web-brand` of Massimo's AP WebBrand, adds
the web UI's files and leaves the others' bytes as they were.

**Tests** run on Massimo's fixture `rooms`:
room 1 "Wohnen", a wall thermostat at 21.4 °C and two radiator thermostats;
room 2 "Schlafen", three radiator thermostats at 19.0, 19.5 and 23.5;
room 3 "Flur", a window contact alone.
The fake Cube carries out what it acknowledges;
its control port sets a device's state, removes a device from its room and
restores it, and drops the connection;
`-boost-for` shortens a boost.

## Implementation Plan

### Block 1: Devices and their entities - done

Merged as #2, #3 and #4: the Cube as a hub, a device per real device in its
room's area, sensors, binary sensors, a key-lock switch, availability;
writes with an `Idempotency-Key`; tests on the fixture `rooms`;
a device names its Cube by its device id.

### Block 2: Release mechanics - done

Merged as #2: `changelog.sh cut` writes `manifest.json`'s `version`;
`CONTRIBUTING.md`.

### Block 3: Rooms - done

Merged as #5, as NOTE v1.3 "how blocks 3 and 4 went" records.

1. **Features:** the coordinator keeps the server's `features`;
   the client retries a lost write only where `idempotency` is listed.
2. **The data:** with `vwt` 1.x, rooms and the stream ask for
   `?devices=all`, and each room's VWT details (`GET …/devices/{vwt}`) are
   read with the rooms; without it, `?devices=real`, no rooms, and a warning
   once that the rooms need a newer Massimo.
   The device entities of Block 1 leave out `virtual` devices.
3. **Room devices:** a device per room, `(massimo, "<cube>:<room_uid>")`,
   named as the room, model "Room", the VWT's serial,
   beneath its Cube, its area suggested by its name;
   it leaves the registry with its room.
4. **`climate` per room with a thermostat:** current temperature, target,
   step 0.5, the room's `min_setpoint` to `max_setpoint`;
   modes `auto` (auto), `heat` (manual, or vacation and boost),
   `off` (manual at the minimum);
   `hvac_action` heating while a valve is open, idle, off;
   presets `eco` and `comfort` (manual at the room's temperatures),
   `away` while in vacation, `none` (back to the week programme);
   `away` chosen in the dialog is refused, naming `set_vacation`;
   attributes `consistent`, `temperature_sources` (the devices' names),
   `vacation_until`, `pending` (the Cube's radiograms waiting).
5. **`massimo.set_vacation`** on a room's `climate`:
   a temperature and an end, rounded up to the half hour,
   refused in the past.
6. **`temp_method`** as a configuration `select` on a room's device:
   `median` or `mean`.
7. **Writes** through the VWT's routes; a refused write raises a translated
   error.
8. **Texts and icons**, `services.yaml`.
9. **Tests** on the fixture: room devices for all three rooms and a
   `climate` for two; the wall thermostat's temperature and the median;
   a setpoint, `off`, `auto`, the presets, vacation, `away` refused;
   `temp_method` `mean`; a wall thermostat removed and restored with the
   room's device unchanged; a server without `vwt`.
10. **CHANGELOG fragment** under `Added`.

**Verification:**
the test gate and lint of the contract; hassfest.

### Block 4: Boost - done

Merged as #5.

1. The preset `boost` where `boost` 1.x is listed: `{"mode": "boost"}`;
   shown while any thermostat of the room boosts.
2. Tests with the fake Cube's `-boost-for`: the boost and its return.
3. CHANGELOG fragment.

**Verification:**
as Block 3.

### Block 5: Programmes - done

Merged as #6.

Requires `program_etag` 1.x.

1. `massimo.get_program` (D5): the programme, its ETag, `pending`,
   `program_consistent`.
2. `massimo.set_program` with `If-Match` (D11), checked as Massimo checks it;
   `massimo.copy_program`.
3. `program_changed` on the room's `climate`, from the `config` event's
   `changed` and `etag`.
4. Schemas in `probatio`, `services.yaml`, texts; tests, a `412` included.

**Verification:**
as Block 3.

### Block 6: Brand images

1. **Massimo** (its own plan, on `claude/web-brand`, a pull request stacked
   on it): the tool's `homeassistant` scope writes the images trimmed to the
   mark - the icon a square on the mark's wider side, the logo without a
   margin.
2. **Here:** the eight images Massimo's tool writes with
   `--flavour grayorange --scope homeassistant` in
   `custom_components/massimo/brand/`.
3. **A test** that Home Assistant's loader finds the integration's brand
   images, and that they have the names and sizes the brand rules ask.
4. **`CONTRIBUTING.md`:** where the images come from, and how to make them
   again.
5. **CHANGELOG fragment** under `Added`.

**Verification:**
the test gate and lint of the contract; hassfest.

### Block 7: Card

1. A view that passes on Massimo's `week-program.js` and its translations
   from the entry's server, kept per Massimo version (D4).
2. `massimo-week-program-card.js`: picks a room, reads its programme,
   gives the element a kit of Home Assistant's controls,
   sends the changed days with the ETag, offers a reload on `412`;
   a card editor.
3. The integration serves the card and adds it to the frontend.
4. Tests that both are served; a check by hand.

**Verification:**
as Block 3, and the card on a Home Assistant at 1100 and 390 px.

### Block 8: First release

1. The Marketplace (D15-A): its publisher requirements, read when the block
   runs; the manifest's category, which 2026.11 introduces.
   HACS for 2026.10: `hacs.json`, the repository's topics, CI's HACS check
   without its `ignore`, kept as long as `hacs.json` is.
2. The tests on 2026.11 too, once `pytest-homeassistant-custom-component`
   has a version for it.
3. The first release by D3; the Marketplace listing.

**Verification:**
CI; an install from the Marketplace and through HACS on 2026.10.

### Block 9: Breno

On the owner's word in that session:
the integration installed in the breno Pi's Home Assistant,
the `maxcube` YAML removed, the box's documentation updated.

**Verification:**
the rooms in Home Assistant,
a setpoint from Home Assistant seen in Massimo's log.

## Proposed commit message

For the revision, committed on its own before Block 6:

```
chore(aps): +Integration v1.4

The mark as the owner chose it, its generator in Massimo, and its brand images now, trimmed to the mark, as a block of their own before the card.

Key changes:
- D13-Z4 brought up to date: the flavour grayorange with the orange-dotted i, the generator Massimo's tools/brand/
- D27-A, D28-A, D29-A: trimmed by Massimo's tool; now, Block 6; in a worktree of its own
- Blocks 3 to 5 done (#5, #6); the brand images Block 6, the card 7, the first release 8, breno 9

File-revision-v1: GUIDELINES/wip/2026-11-12_16-45_AP_Integration_entities_services_card_release.md::v1.4::2026-11-13::TL;DR, Discussion, Analysis, Implementation Plan, Proposed commit message, Change History::the brand images Block 6, D13 up to date, D27-A to D29-A
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
- v1.3 (2026-11-13): with Massimo's room thermostat, boost, ETag and features
  on its `main`.
  Folded: NOTE Integration v1.2: boost as a block of its own (D16-A);
  NOTE Integration v1.2: release through the marketplace (D15-A);
  NOTE Integration v1.2: the icon (D13-Z4).
  D12-A as Massimo built it, a version per feature; D20-A.
  Blocks 1 and 2 done; Block 3 in steps from the measured API and
  Home Assistant's climate; boost Block 4; the first release through the
  Marketplace, with HACS for 2026.10; eight blocks.
- v1.4 (2026-11-13): D13-Z4 as chosen since (`grayorange`, the "i" dotted
  orange, the generator Massimo's `tools/brand/`); D27-A, D28-A, D29-A.
  Blocks 3 to 5 done (#5, #6); the brand images a block of their own, 6,
  trimmed by Massimo's tool; the card 7, the first release 8, breno 9.
