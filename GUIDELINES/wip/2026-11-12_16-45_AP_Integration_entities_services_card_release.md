# AP Integration v1.8: Entities, services, card, release

## TL;DR

The integration gets its rooms, services and week-programme card on
Massimo's room thermostat, is released through the Marketplace,
and replaces `maxcube` on breno.
Each block requires the Massimo feature it uses, by name, from `/healthz`.

- devices, rooms, boost, programmes, brand images, card, distribution,
  read access → done (1-9)
- users to Massimo → built under a plan of its own (#14): registration,
  the user and level on each call, `system` for a call without one
- setup → reread when opened, two names, a typed address kept, titles by
  the key's display name, the server as a device (#15, #16)
- breno trial → resumed 2026-11-15: `distro/devel` on the Pi, registered;
  the checks of step 3 open
- release → 0.1.0, beta, a pre-release; Massimo v0.16.0-alpha.1 has
  `features` and the suite passes against it
- the NOTEs of v1.2 to v1.7 → folded in, at the owner's word

### Blocks

1. Devices and their entities - done
2. Release mechanics - done
3. Rooms: room devices, `climate`, `set_vacation`, `temp_method` - done
4. Boost: the preset `boost` - done
5. Programmes: get, set, copy with the ETag, `program_changed` - done
6. Brand images - done
7. Card - done
8. Distribution: `dist.py`, the release workflow, `distro/*`, keys, site - done
9. Read access: `get_program` for a view-only user, `copy_program`'s source - done
10. Breno trial: the integration from `distro/devel` on the Pi - steps 1 and 2 done
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

**Decided at this plan's gates (2026-11-12 to 14):**

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
- **D56, as since built** (the owner, 2026-11-14).
  Read access is Block 9, after Block 8; the trial, the release and breno
  move down to 10 to 12.
  Passing the Home Assistant user on to Massimo - its id and name, and the
  call's access level, `admin`, `control` or `view` for the call's target -
  was not this plan's: it waited for Massimo's `integration` feature and was
  built as Massimo specifies it, under a plan of its own, merged as #14
  (2026-11-15).
- **D57, superseded** (2026-11-14). D57-B, "nothing is asked of Massimo for
  it yet", no longer held once the owner asked: the session
  "HA Integration 1" briefed Massimo's session "Windhager Webserver 2" on
  the feature `integration: 1.0`, which Massimo then built.
- **D58-A** (the owner, 2026-11-14).
  A ruleset on `main` requires CI's checks before a merge:
  hassfest, HACS, ruff and "Tests against Massimo main"; a repository admin
  may bypass it. As Massimo's "main: checks before merge"; made.
- **D59-A** (the owner, 2026-11-14).
  A release signs its `SHA256SUMS` too, with the zip's key:
  `SHA256SUMS.sig` beside it, one check for every file a release carries.
- **D60-A** (the owner, 2026-11-14).
  actionlint comes from the guidelines: `GUIDELINES/shared/tools/actionlint.sh`,
  one pinned version, from its Docker image or as a checked binary;
  the guidelines carry it since #12. CI does not run it yet.
- **D61-A** (the owner, 2026-11-14).
  The warnings Home Assistant 2026.11 gives on `climate.py` are fixed before
  the first release, on a branch of their own, with a test: merged as #13.
- **D62-A** (the owner, 2026-11-14).
  The clone of `distro/devel` on the Pi stays; a `git pull` brings it up to
  date when the trial goes on.
- **Areas.**
  Every device suggests its room's name as its area, once;
  the areas stay the owner's.
- **Never half-way** (the owner, 2026-11-13).
  A step that needs Massimo waits until Massimo has it on its `main`,
  and is then built as Massimo specifies.
- **The NOTEs folded** (the owner, 2026-11-17).
  v1.8 takes in every NOTE of v1.2 to v1.7, those recording how a run went
  among them, and the work of the plans that passed users on (#14) and
  polished the setup (#15, #16), so that the plan reads alone.

## Analysis

**What a server supports** (Massimo's `docs/api-v1.md`, `GET /healthz`):
`features` names `event_ids`, `idempotency`, `commands`, `vwt`,
`program_etag`, `boost`, `proxy_virtual` and `integration`, each `"1.0"`;
a server without a store leaves out `idempotency`, `commands`,
`proxy_virtual` and `integration`; a server without the field has none.
`vwt`, `program_etag`, `boost`, `proxy_virtual` and `integration` are first in
v0.16.0-alpha.1, Massimo's newest release (2026-11-15).
The coordinator reads it with the health it already reads.
A block's entities need its feature's major 1, and a feature of another
major counts as absent;
the client retries a lost write only where `idempotency` is listed.
The suite passes against v0.16.0-alpha.1 (89 tests, 2026-11-17); it cannot
run against an older Massimo, its setup registering an integration.

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
Massimo's default view adds a virtual wall thermostat to each room without a
real one; the integration and the tests' own reads use `?devices=real`
where they want the real devices.

**Home Assistant's climate** (2026.10):
`HVACMode` `auto`, `heat`, `off`; `HVACAction` `heating`, `idle`, `off`;
presets `eco`, `comfort`, `away`, `boost`, `none`;
`ClimateEntityFeature` `TARGET_TEMPERATURE`, `PRESET_MODE`, `TURN_ON`,
`TURN_OFF`; an invalid mode raises `ServiceValidationError`.
An entity service is registered on the platform with a `probatio` schema,
as core's climate integrations do.

**Home Assistant 2026.11** (checked by its source on 2026-11-13, and on the
Pi's 2026.11.0):

- climate names its temperatures `native_*` and warns of an entity giving
  an old name alone, which stops working in 2027.11; 2026.10 reads only the
  old names. Given both, 2026.11 takes the native ones without a warning
  (`migrate_deprecated_entity_members`): `RoomClimate` gives both (D61-A).
- A device naming its Cube by identifier (`via_device`) is deprecated since
  2026.10 and goes in 2027.8: devices, and the Cubes their server, are named
  by device id (`via_device_id`).
- `async_setup_entry` returns `True` while the integration supports 2026.10,
  which fails a setup returning anything but a boolean; `None` once it
  requires 2026.11, which ignores a boolean from a custom integration.
- `DeviceInfo` is a dataclass in 2026.11; the integration builds it with
  keyword arguments only, which both versions take.
- Nothing else the integration imports changed in a way it uses;
  2026.11's opt-in to changing an entity's id in place is not taken.
- The tests cannot run on 2026.11 yet: `pytest-homeassistant-custom-component`
  0.13.375 is for 2026.10.4, and with 2026.11 in its place the harness does
  not load (it imports `httpx` before Home Assistant, which 2026.11 refuses).

**Brand images** (Home Assistant 2026.10, `homeassistant/components/brands`):
a custom integration's `brand/` holds `icon.png`, `logo.png`, their `@2x`
and their `dark_` ones; a missing one falls back (`logo` to `icon`, `dark_` to
the light one); Home Assistant serves them through its brands view, and the
loader says `has_branding` where `brand/` is there.
Its code checks the names, not the sizes; the brand rules ask for an icon of
1:1 at 256 px (512 at `@2x`), a logo whose short side is 128 to 256 px,
transparent, trimmed.

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
- **`git verify-commit`** takes any key of `allowed_signers`, whoever the
  committer: `site/build.sh` also checks that the principal is the channel's
  (release, or rolling for devel).
- **A called workflow** sees no secret, not even its environment's, unless
  the caller passes `secrets: inherit`, as `ci.yml` does for `release.yml`.

**The Pi** (`pi.breno.caleon.ch`, 2026-11-15):
Home Assistant 2026.11.0, the container `homeassistant`
(`ghcr.io/home-assistant/home-assistant:stable`) on the host network,
`/srv/homeassistant/config` as `/config`;
the integration a clone of `distro/devel` owned by `pi` at
`/srv/homeassistant/config/custom_components/massimo`, its commits checked
against the clone's `.git/allowed_signers`; updated by
`git -C /srv/homeassistant/config/custom_components/massimo pull` and
`sudo docker restart homeassistant`.
Its Massimo, a service, announces itself with the record's `url`
`https://massimo.breno.caleon.ch`; Home Assistant is registered with it.
A second Massimo on the LAN, on the owner's workstation, is discovered too.
`maxcube` failed its setup on 2026-11-12 (the proxy refused) and has not
run since.

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

**Tests** run on Massimo's fixture `rooms`:
room 1 "Wohnen", a wall thermostat at 21.4 °C and two radiator thermostats;
room 2 "Schlafen", three radiator thermostats at 19.0, 19.5 and 23.5;
room 3 "Flur", a window contact alone.
The fake Cube carries out what it acknowledges;
its control port sets a device's state, removes a device from its room and
restores it, and drops the connection;
`-boost-for` shortens a boost.
Massimo's server embeds a web UI bundle that git does not keep: CI, and a
local build, run Massimo's bundler first where Massimo has one.
Since Massimo's AP StoreRaise, an integration's users are named
`<integration uuid>:<subject>`: the tests find them by the names Massimo
gives, never by a name written in.

## Implementation Plan

### Block 1: Devices and their entities - done

Merged as #2, #3 and #4: the Cube as a hub, a device per real device in its
room's area, sensors, binary sensors, a key-lock switch, availability;
writes with an `Idempotency-Key`; a device names its Cube by its device id.
The tests start the fake Cube on Massimo's fixture `rooms` with its control
port, not on a recorded greeting (`MASSIMO_GREETING` no longer read), and
cover a wall thermostat, the key lock as reported, a report reaching its
sensor, and a device without state unavailable until it reports.

### Block 2: Release mechanics - done

Merged as #2: `changelog.sh cut` writes `manifest.json`'s `version`;
`CONTRIBUTING.md`.

### Block 3: Rooms - done

Merged as #5: features kept by the coordinator, `?devices=all` with `vwt`;
a device per room with a thermostat, its `climate` (modes, presets, the
attributes), `massimo.set_vacation`, `temp_method` as a `select`, translated
refusals, texts and icons, tests on the fixture.
Where it differs from the steps v1.3 gave:

- A room gets a device only where it has a thermostat: Home Assistant
  registers a device through its entities, and a room without one has
  nothing to control. A room that loses its last thermostat keeps its device,
  its `climate` unavailable.
- `off` holds 4.5 °C, MAX!'s off, not the room's minimum setpoint.
- The tests find rooms by id, not by name.

### Block 4: Boost - done

Merged as #5: the preset `boost` where `boost` 1.x is listed, shown while any
thermostat of the room boosts; tested with the fake Cube's `-boost-for`.

### Block 5: Programmes - done

Merged as #6: `massimo.get_program`, `set_program` with `If-Match`,
`copy_program`, `program_changed` from the `config` event; a `412` tested.

### Block 6: Brand images - done

Merged as #7: the eight images of Massimo's tool
(`--flavour grayorange --scope homeassistant`) in
`custom_components/massimo/brand/`, tested for names and sizes;
`CONTRIBUTING.md` says how to make them again.

### Block 7: Card - done

Merged as #8: the signed-in view `/api/massimo/ui/{name}`, the card
`massimo-week-program-card` with Massimo's element and a kit of native
controls, its editor, its registration on every page, tests.
Where it differs: `massimo.get_program` also names the device the programme
was read from (`source`), which the card shows as Massimo's page does.
The check by hand (D24-A) ran on Home Assistant 2026.10.4 with
`home-assistant-frontend` 20260930.5, against Massimo's `main` and the fake
Cube, dark theme, English, in two frames of 1100 and 390 px on one page:
reading, editing and sending, a change made meanwhile loaded or, with an
edit held, refused with the edit kept and a reload offered, the phone layout
without sideways scrolling, the card picker and its editor.
Not checked by hand: the light theme, a language other than English.

### Block 8: Distribution - done

Merged as #10, with #11 (the release's environment keys, D59-A) and #12
(the guidelines with actionlint, D60-A): `tools/dist.py` and its tests,
`release.yml` called by `ci.yml` once every check passed, signed zips and
`distro/<channel>` commits, the site at `ha.massimo.metaworx.ch`,
`README.md` and `CONTRIBUTING.md`.
Where it differs:

- The zip is signed itself, kept in its branch as `.distro/massimo.zip.sig`,
  so that the site can check a zip it makes again; a release also carries
  `SHA256SUMS` and, since D59-A, `SHA256SUMS.sig`.
- The tests against Massimo's newest release are a second entry of the test
  job's matrix, for a tag's run alone.
- CI's HACS check keeps `ignore: topics` alone; the contract rose to v1.2.0
  (`tools/`, `site/` and `keys/` among the source directories, the release
  by CI, `tools` linted).
- actionlint was not run then; the workflows were parsed and their steps run
  by hand.

Made on GitHub: the environments `signing` (version tags, the owner
approves), `signing-rolling` (`main`), and `github-pages` admitting the same
tags beside `main`; `SIGNING_KEY` in each, `DISTRO_DEPLOY_KEY` in both; the
deploy key for `distro/*`; the rulesets "distro/* branches: written by
release.yml alone" and, by D58-A, "main: checks before merge".
`release.yml`'s first run on `main` stopped at signing, `ci.yml` calling it
without `secrets: inherit`; #11 fixed it.

### Block 9: Read access - done

Merged as #9: `massimo.get_program` a service of the integration checking
`read` on each room for a non-admin caller (D53-A), `copy_program` checking
`read` on its source (D54-A), the refusal translated, tested with a
read-only user and a user without read on a room.

### Block 10: Breno trial

1. **Done** (2026-11-14, D38, D62-A): `distro/devel` cloned as `pi` into
   `/srv/homeassistant/config/custom_components/massimo`, the folder made
   with `sudo install -d -o pi -g pi`; its commit's signature checked against
   `keys/allowed_signers` (good, `rolling@ha.massimo.metaworx.ch`);
   Home Assistant 2026.11.0 loads `massimo` without an error.
   The trial halted there that day, until it was settled which Massimo, and
   which user, Home Assistant signs in to; it resumed on 2026-11-15, the
   clone pulled to `0.0.0-dev.56+ge80d339`.
2. **Done** (2026-11-15): Home Assistant registered with the Pi's Massimo
   through the setup flow's Register, which collects a key of the role
   `integration` once the owner approves the request in Massimo.
   The owner had first added the
   server by its URL; since #15 a typed address is kept when the server is
   found again.
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
3. Massimo's tagged release with `features`, which the tag's tests run
   against: v0.16.0-alpha.1 (2026-11-15), against which the suite passes.
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

For this revision, with the retirement of the plans that passed users on
and polished the setup, and the NOTEs it folds in:

```
chore(aps): -OnBehalf, -SetupPolish, +Integration v1.8, -NOTE Integration

Two plans retire, all their work merged; AP Integration reads alone again, its NOTEs and what the two plans built folded in.

Key changes:
- -OnBehalf: its four blocks merged as #14, with its NOTE
- -SetupPolish: its four blocks merged as #15, its display-name NOTE as #16, with both NOTEs
- Integration v1.8: Blocks 8 and 9 done, Block 10 resumed with steps 1 and 2 done, Block 11's wait for a Massimo with features over
- D56 and D57 as since built and superseded; D58 to D62 from their NOTE
- the nine NOTEs of v1.2 to v1.7 folded in and removed, those of how a run went among them, at the owner's word

File-revision-v1: GUIDELINES/wip/2026-11-12_16-45_AP_Integration_entities_services_card_release.md::v1.8::2026-11-17::TL;DR, Discussion, Analysis, Implementation Plan, Proposed commit message, Change History::the NOTEs and the two plans' work folded in
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
- v1.8 (2026-11-17): the plan reads alone again, at the owner's word.
  Folded: NOTE Integration v1.2: Block 1 on the rooms fixture;
  NOTE Integration v1.2: Home Assistant 2026.11;
  NOTE Integration v1.3: how Blocks 3 and 4 went;
  NOTE Integration v1.5: how Block 7 went;
  NOTE Integration v1.6: how Block 8 went;
  NOTE Integration v1.7: Massimo asked, and block numbers;
  NOTE Integration v1.7: decisions D58 to D60;
  NOTE Integration v1.7: breno trial halted;
  NOTE Integration v1.7: climate's native temperatures.
  Blocks 8 and 9 done (#9 to #12), D61-A done (#13); D56 as built and D57
  superseded (#14); the setup's work of #15 and #16 where it touches the
  trial; Block 10 resumed, steps 1 and 2 done; Block 11's step 3 met by
  Massimo v0.16.0-alpha.1. Done blocks shortened to what they built and where
  they differed from their steps; their steps stay in git's history.
  The analysis brought up to date: the features, Home Assistant 2026.11,
  the Pi, the tests' Massimo build and user names.
