# AP Integration v1.7: Entities, services, card, release

## TL;DR

The integration gets its rooms, services and week-programme card on
Massimo's room thermostat, is released through the Marketplace,
and replaces `maxcube` on breno.
Each block requires the Massimo feature it uses, by name, from `/healthz`.

- devices, rooms, boost, programmes, brand images, card → done (1-7)
- read access → `get_program` needs `control` (an entity service) →
  a service of the integration checking `read`: a view-only user reads
  the programme, the card included; `copy_program` reads its source only
  where the user may
- users to Massimo → not here: waits for Massimo's `integration` feature
- distribution → a GitHub release by hand → CI: signed zip, SSH-signed
  `distro/<channel>` branches for git, the zips on `ha.massimo.metaworx.ch`
- channels: stable; beta (every 0.x, and `-beta`); alpha (`-alpha`);
  devel (`main` after its tests; no GitHub release)
- keys: release and rolling, made in `~/.ssh`, piped to `gh` (D46)
- breno → `maxcube` (not loaded since 2026-11-12) → the integration from
  `distro/devel`, before the first release
- release → 0.1.0, beta, a pre-release; Marketplace and HACS

### Blocks

1. Devices and their entities - done
2. Release mechanics - done
3. Rooms: room devices, `climate`, `set_vacation`, `temp_method` - done
4. Boost: the preset `boost` - done
5. Programmes: get, set, copy with the ETag, `program_changed` - done
6. Brand images - done
7. Card - done
8. Distribution: `dist.py`, the release workflow, `distro/*`, keys, site
9. Read access: `get_program` for a view-only user, `copy_program`'s source
10. Breno trial: the integration from `distro/devel` on the Pi
11. First release: 0.1.0, category, topics, the zip for HACS
12. Breno: `maxcube` removed, the box's documentation

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
- **D21-A.**
  The presets stay Home Assistant's standard ones: `none`, `eco`,
  `comfort`, `away`, `boost`; `none` goes back to the week programme.
- **D22-A.**
  The card fetches Massimo's element and texts through a view that needs
  Home Assistant's sign-in, and runs the element from a blob:
  Home Assistant passes Massimo's files to nobody who is not signed in.
- **D24-A.**
  The card is checked by hand in a scratch Home Assistant with its frontend,
  against the fake Cube, in a browser at 1100 and 390 px,
  its screenshots shown at the commit gate.
- **D27-A.**
  Home Assistant's brand images are trimmed to the mark, as its brand rules
  ask: Massimo's tool does it in its `homeassistant` scope.
- **D28-A.**
  The brand images come now, a block of their own before the card,
  not with the first release.
- **D29-A.**
  That block is done in a worktree of its own, on a branch from `origin/main`.
- **D30-A.**
  Two sessions wrote a v1.4 each; `main`'s stands, and v1.5 adds the card's
  steps and D21, D22 and D24 from the other, which was never committed to
  `main`.
- **D31-A** (replaces D20-A).
  One writer per revision: the session whose block comes next,
  after fetching `main` and building on the plan there.
- **D32-A.** `categories: ["climate.thermostats_heating"]`.
- **D33-A.** Before the release, a check on Home Assistant 2026.11:
  the breno trial (Block 10) is that check, the Pi running 2026.11.0;
  the tests on 2026.11 once the harness has a version for it.
- **D34-A.** The first version is 0.1.0; its cut ends D14's
  "bump without a cut".
- **D35-A, as D36 changes it.** This session cuts on a branch, with a
  signed tag, and opens the pull request; after the merge it pushes the tag
  at a gate of its own, and CI makes the release; the owner opens the
  catalog pull request from their account, its text written for them.
- **D36-A.** CI makes the GitHub release from a version tag.
- **D38** (the owner, 2026-11-14).
  This session works on the Pi directly for everything Home Assistant,
  as the user `pi` (`sudo`);
  no other configuration there is touched without the owner's prior,
  explicit permission.
- **D42-A.** Installs by git from `distro/<channel>`, whose root is the
  integration's folder:
  `git clone -b distro/<channel> … config/custom_components/massimo`.
  `release/*` is taken: Massimo's rolling tags and its release branches.
- **D45** (the owner, 2026-11-14).
  Every version below 1.0.0 is a GitHub pre-release, on the channel beta,
  or alpha where it carries `-alpha`.
  devel has no GitHub release: it is `distro/devel`, written only from a
  commit of `main` whose tests passed; `main` itself never goes on a box.
- **D46** (the owner, 2026-11-14).
  The keys are made in `~/.ssh` by this session, never shown, piped straight
  into `gh secret set`, and kept in `~/.ssh`.
- **D47-A.** Order: distribution (8), the breno trial (10), the first
  release (11), `maxcube` removed (12); read access (9) added by D56.
- **D48-A.** The channels' zips on this repository's Pages, not as
  releases: any release is one HACS may offer.
- **D49-A.** The `distro/*` commits are signed, the release key for
  stable, beta and alpha, the rolling key for devel.
- **D50** (the owner, 2026-11-14). The site is `ha.massimo.metaworx.ch`,
  its CNAME and Pages' custom domain set by the owner.
- **D51-A.** SSH signatures throughout: `ssh-keygen -Y sign` over each zip,
  the same keys signing the `distro/*` commits, one allowed-signers file
  for both checks.
- **D52-A.** Massimo's site files are copied here under Apache-2.0,
  as the owner, holder of both licences, allows.
- **D53-A** (the owner, 2026-11-14).
  Reading a programme needs view, writing it control:
  `massimo.get_program` is a service of the integration that checks `read`
  on each room it names, as Home Assistant checks `control` on an entity
  service; its name, target and answer stay as they are.
  `set_program`, `copy_program` and `set_vacation` stay entity services,
  needing `control`.
- **D54-A.** `copy_program` also needs `read` on the room it copies from.
- **D55-B** (the owner, 2026-11-14), for the plan that passes users on:
  a call without a user (an automation, a script, the system) names the
  fixed user `system`.
- **D56** (the owner, 2026-11-14).
  Read access is Block 9, after Block 8 of v1.6; the trial, the release and
  breno move down to 10 to 12.
  Passing the Home Assistant user on to Massimo - its id and name, and the
  call's access level, `admin`, `control` or `view` for the call's target -
  is not this plan's: it waits for Massimo's `integration` feature on
  Massimo's `main`, and is built as Massimo specifies it, under a plan of
  its own.
- **D57-B** (the owner, 2026-11-14).
  Nothing is asked of Massimo for it yet.
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

**The card's element** (Massimo's `internal/server/ui/week-program.js`,
AGPL-3.0-or-later): a classic script defining `<massimo-week-program>`,
without a shadow root; its host gives it `model`
(`MassimoWeekProgram.model(programme)`), `kit` and `storedOn`, and asks
`dirtyDays()` and `resetControls()`; it dispatches `change`.
Its kit is `t` (Massimo's texts `prog.*`, `day.*`, `dayShort.*`, flat keys
with `{placeholders}`, in `/ui/i18n/<lang>.json`: en, de, fr, it, nl, pl),
`elem`, `textEl`, `button`, `switchEl`, `fieldRow`, `numberInput`, `fmtNum`,
`fmtTemp`, `clamp` and `temps`.
It finds its day buttons as `.prog-days button` and sets their `className`
(`day`, `selected`, `editing`, `dirty`, `chosen`) and `disabled`:
the kit's buttons are native `<button>`s, styled by the card;
the switch is Home Assistant's `ha-switch`.
Its look is the class names Massimo's AGPL `style.css` styles
(`day-bar`, `prog-bar`, `prog-seg` with `--warm`, `prog-point`, `step`,
`muted`, `small`): the card has CSS of its own for them, in Home Assistant's
theme variables.
Massimo's page sends the changed days with the tag, and on `412` keeps the
edits and offers a reload (`config.js`, `sendProgram`).
Home Assistant 2026.10 loads a script on every page with
`frontend.add_extra_js_url`, serves files with
`http.async_register_static_paths`, and signs a card's fetch with
`hass.fetchWithAuth`.

**Distribution** (2026-11-14):

- **HACS** (`hacs/integration`, `repositories/base.py`; the Marketplace is
  HACS built in) reads the releases in GitHub's order, which is newest
  target commit first, and offers the first pre-release to whoever has
  **Pre-release** on; with no regular release, it installs the default
  branch's newest commit to everyone else.
  A rolling release would always be first: hence D48-A and no devel release.
  HACS has one switch, not channels: following a channel is git's and the
  zips'.
- **GitHub Pages** of this repository: build type `workflow`, the custom
  domain `ha.massimo.metaworx.ch`; no organisation site exists whose domain
  it would inherit.
  Pages keeps the first deploy of a commit (Massimo's
  `packaging/README.md`), so the site is built without state, from the
  `distro/*` branches, on every deploy.
- **Rulesets** let a deploy key through as a bypass actor, as Massimo's
  `release/*` branches do; GitHub's own token is not one.
- **The Pi** (`pi.breno.caleon.ch`): Home Assistant 2026.11.0, the container
  `homeassistant` (`ghcr.io/home-assistant/home-assistant:stable`) on the
  host network, `/srv/homeassistant/config` as `/config`, owned by root;
  git there; Massimo `v0.15.0-alpha.1-153-g1b3a9a1` as a service, with
  `features`; `maxcube` failed its setup on 2026-11-12 (the proxy refused)
  and has not run since.

**Permissions** (Home Assistant 2026.10, its `helpers/service.py` and
`auth/permissions`):
a user is an administrator or not; the groups are fixed
(`system-admin`, `system-users`, `system-read-only`), and their policies
grant `read`, `control` or `edit` per entity, without a UI.
An entity service needs `control` on each entity a non-admin names,
whatever it does, and offers nothing else;
a service of the integration checks what it needs itself, from
`call.context.user_id`, and a call without one is the system's.
The WebSocket's `call_service` merges its `target` into the call's data,
so the card's call reaches either kind unchanged.
The context of a call is set on the entity before the service runs,
so a write can tell whose it is: the later plan's starting point.

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

### Block 6: Brand images - done

Merged as #7.

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

1. **The view** `/api/massimo/ui/{name}`, signed in (D22-A):
   `week-program.js` and `i18n/<lang>.json` from the Massimo server of the
   entry an `entity_id` names, else the first, kept per Massimo version;
   any other name, and a file the server has not, `404`.
2. **The card** `massimo-week-program-card`, plain JavaScript without a
   build, in `custom_components/massimo/frontend/`:
   a room's `climate` in its configuration;
   Massimo's element and texts loaded once per page, by Home Assistant's
   language, else English;
   the kit of native elements and `ha-switch`, styled by the card's CSS in
   Home Assistant's theme variables;
   the programme read with `massimo.get_program`;
   **Send** writes the changed days, checked as Massimo's page checks them,
   with `massimo.set_program` and the tag;
   a programme changed meanwhile keeps the edits and offers **Reload**;
   read again by itself when `program_tag` changes and nothing is edited.
3. **Its editor** by `getConfigForm`: the room's `climate`, of this
   integration; the card listed in the card picker (`window.customCards`).
4. **The integration serves** the card's script on a static path and loads
   it on every page (`add_extra_js_url`) where the frontend runs;
   `manifest.json` names `http` as a dependency and `frontend` after it.
5. **Tests:** the view's files, signed in and refused without; a name it
   does not serve; the card's script served; the script registered with a
   frontend.
6. **The check by hand** (D24-A): a scratch Home Assistant 2026.10.4 with
   `home-assistant-frontend` 20260930.5, against the fake Cube, the card on a
   dashboard, at 1100 and 390 px: reading, editing, sending, a change made
   meanwhile, the editor.
7. **CHANGELOG fragment**, `README.md`.

**Verification:**
as Block 3, and the check by hand.

### Block 8: Distribution

1. **`tools/dist.py`**, without dependencies beyond Python:
   - `meta`: from a version tag, its version, channel (D45) and whether it
     is a pre-release, the tag checked against `manifest.json`;
     from `main`, devel, the version `<last tag>-dev.<n>+g<sha>`
     (`0.0.0` before the first tag);
   - `build`: the tree - `custom_components/massimo/` with that version
     in its `manifest.json`, and `LICENSE` - and `massimo.zip` of it,
     stored, sorted, dated 1980: the same tree gives the same bytes;
   - `zip`: the zip of a tree, for the site;
   - `targets`: the channels a release goes to, its own and each less
     stable one that holds an older version; devel alone for `main`.
2. **Tests** of `dist.py` (`tests/test_dist.py`): the channels, the
   versions Home Assistant's loader takes, the order of versions,
   the same bytes twice, the manifest's version.
3. **Keys** (D46, D51-A), each `ssh-keygen -t ed25519` in `~/.ssh`, its
   private half piped into `gh secret set`:
   `massimo-homeassistant-release` (environment `signing`),
   `massimo-homeassistant-rolling` (`signing-rolling`),
   `massimo-homeassistant-distro`, the deploy key that pushes `distro/*`
   (both); the public halves in `keys/`, and `keys/allowed_signers`
   naming the release and rolling keys for `git` and `file`.
4. **Environments:** `signing`, for `v*` tags alone, its runs approved by
   the owner; `signing-rolling`, for `main` alone; `github-pages` admitting
   `v*` tags beside `main`.
   **Ruleset** on `distro/*`: no deletion, no force push, creation and
   update by a deploy key alone.
5. **`.github/workflows/release.yml`**, called by `ci.yml` for a push of
   `main` or a `v*` tag once every check has passed:
   `build` (no secret) runs `dist.py`, attests the zip's provenance;
   `sign` (in `signing` or `signing-rolling`) signs the zip, checks the
   signature against `keys/allowed_signers`, makes the GitHub release of
   a tag (the zip, its signature, `SHA256SUMS`, the notes from
   `changelog.sh notes`, `--prerelease` by D45), and writes each target
   channel's `distro/<channel>` commit - the tree and `.distro/` with the
   version, the source commit and the zip's signature - signed, on top of
   the branch, pushed with the deploy key;
   then the site.
   `ci.yml`: pushes of `v*` tags; a tag's tests also against Massimo's
   newest release.
6. **The site** (D50, D52-A): `site/` with Massimo's `site.css`, a home
   page, a privacy page and `build.sh`, which builds it without state:
   the README as a page by `md_html.py`, `keys/`, and per channel
   `distro/<channel>.zip` and `.zip.sig`, each zip made again from its
   branch and checked against the signature there;
   `.github/workflows/site.yml` deploys it to Pages.
7. **Documents:** `README.md`, installing by channel and checking a
   download; `CONTRIBUTING.md`, "Cutting a release" without the release by
   hand, and the keys.

**Verification:**
the test gate and lint of the contract; hassfest; `actionlint` where at
hand; `site/build.sh` and `dist.py` run locally against a local
`distro/*`; a signature made and checked with a throw-away key.
The workflows run first when the branch is pushed and merged.

### Block 9: Read access

1. `massimo.get_program` registered by the integration (D53-A), no longer
   by the `climate` platform: the same name, a `target` of room `climate`s,
   `SupportsResponse.ONLY`, the answer `{entity_id: {...}}` as before.
   A non-admin caller needs `read` on each entity named, else
   `Unauthorized`; a call without a user goes through.
   An entity that is not a room's `climate` of this integration is refused,
   translated.
2. `massimo.copy_program` checks `read` on its `source` for a non-admin
   caller (D54-A); `control` on its target stays Home Assistant's check.
3. `services.yaml` unchanged in what it offers; the refusal's text in
   `en.json`, `de.json` and `strings.json`.
4. **Tests**, against the fake Cube: a read-only user reads a programme
   through the WebSocket's `call_service` as the card calls it, and is
   refused `set_program`; a user who may not read a room is refused
   `get_program` and a `copy_program` from it; a call without a user and an
   admin's read as before.
5. **CHANGELOG fragment** under `Added`.

**Verification:**
the test gate, ruff, hassfest.

### Block 10: Breno trial

1. As `pi` on `pi.breno.caleon.ch` (D38): `distro/devel` cloned into
   `/srv/homeassistant/config/custom_components/massimo`, its commit's
   signature checked; `sudo docker restart homeassistant`.
2. The owner makes a key of the role `integration` in Massimo and enters
   it in Home Assistant's setup; the entry found by zeroconf or named.
3. Checked: the Cube, the devices, the rooms and their `climate`s,
   a setpoint from Home Assistant seen in Massimo's log, the card on a
   dashboard.
   `maxcube`'s YAML stays as it is (Block 12).
4. A NOTE: how it went, Home Assistant 2026.11 included (D33-A).

**Verification:**
as step 3.

### Block 11: First release

1. `manifest.json` `categories` (D32-A); `hacs.json` with
   `zip_release` and `filename: massimo.zip`;
   the repository's topics; CI's HACS check without `ignore`.
2. `README.md`: the Marketplace and HACS (Pre-release on, D45).
3. Waits for Massimo's next tagged release with `features`:
   the tag's tests run against it.
4. The cut of 0.1.0 (D34-A) on a branch, its pull request (D35-A);
   after the merge, the tag pushed at a gate of its own; CI releases.
5. The catalog pull request's text for the owner.
6. The tests on 2026.11 where the harness has a version by then.

**Verification:**
CI's release run; the zip installed through HACS on a scratch 2026.10.

### Block 12: Breno

On the owner's word: the `maxcube` YAML removed from
`configuration.yaml`, the box's documentation updated.

**Verification:**
Home Assistant starts without `maxcube`; the rooms as in Block 10.

## Proposed commit message

For the revision, committed on its own before Block 9:

```
chore(aps): +Integration v1.7

A view-only user reads a room's week programme: read access becomes Block 9, before the trial and the release.

Key changes:
- Block 9: get_program a service of the integration that checks read; copy_program checks read on its source
- Blocks 9 to 11 of v1.6 move to 10 to 12
- D53, D54 as recommended; D55-B, D56, D57-B as the owner gave them: passing users on to Massimo waits for its integration feature

File-revision-v1: GUIDELINES/wip/2026-11-12_16-45_AP_Integration_entities_services_card_release.md::v1.7::2026-11-14::TL;DR, Discussion, Analysis, Implementation Plan, Proposed commit message, Change History::read access as Block 9; D53 to D57
Assisted-by: claude-code:claude-opus-5-5
```

For Block 9:

```
fix(integration): A view-only user reads a room's week programme

massimo.get_program needed control, as every entity service does, so a user who may only view a room could not open its programme, nor use the card. It is now a service of the integration that checks read on each room it names; copy_program also checks read on the room it copies from.

Key changes:
- get_program registered by the integration, its name, target and answer as before
- copy_program refuses a source the user may not read
- tests with a read-only user and a user without read on a room

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
- v1.5 (2026-11-13): Block 6 done (#7).
  Block 7 in steps: the view, the card with a kit of native controls,
  which the element's `.prog-days button` requires, and CSS of its own,
  its editor, its registration, its tests and the check by hand;
  from a v1.4 of the card's session that `main` never had (D30-A).
  D21-A (the standard presets), D22-A (the element fetched with the
  sign-in), D24-A (the check by hand in a scratch Home Assistant);
  D31-A (one writer per revision, building on `main`) replaces D20-A.
- v1.6 (2026-11-14): Block 7 done (#8).
  Distribution a block of its own before the release (D47-A):
  `dist.py`, signed zips and `distro/<channel>` branches by CI (D42-A,
  D48-A, D49-A, D51-A), keys made here (D46), channels by version (D45),
  the site at `ha.massimo.metaworx.ch` (D50, D52-A).
  The breno trial from `distro/devel` before the release (D38), the release
  after Massimo's next tagged release; `maxcube` removed last.
  D32 to D36 as recommended; the analysis of HACS, Pages and the Pi.
- v1.7 (2026-11-14): read access, Block 9 (D53-A, D54-A):
  `get_program` for a view-only user, `copy_program`'s source read only
  where the user may.
  The trial, the release and breno move to Blocks 10 to 12 (D56), their
  references in D33-A and D47-A with them.
  Passing users on to Massimo left to a plan of its own, after Massimo's
  `integration` feature (D55-B, D56, D57-B).
  Written on the unpushed v1.6 at the owner's word, not on `main` (D31-A).
