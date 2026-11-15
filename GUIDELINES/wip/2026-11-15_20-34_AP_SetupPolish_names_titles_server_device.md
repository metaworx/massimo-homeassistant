# AP SetupPolish v1.0: names, titles, server device

## TL;DR

Follow-ups from the owner's first registration on the Pi (2026-11-15).
The setup flow checks the server again when it is opened and asks for two
names; the entry's title says whose key it signs in with; a server device
shows the connection.

- discovered flow → menu or key form decided at discovery → checked again
  whenever the sign-in step is opened again; a debug line says why (D1)
- Register → a form first: the name Home Assistant gives itself in Massimo
  (D2), the entry's name in Home Assistant (D6)
- discovery of a configured server → address always overwritten → only an
  address taken from an announcement, or the announced `url` of a
  registered entry (D3)
- "Add Massimo" by hand → empty address → a discovered, unconfigured
  server's (D5)
- title "Massimo (martin)" → the name; `<name> (key of martin)` for a
  person's key; a title renamed by hand kept (D7)
- connection details → a server device: version, "Visit", *Connected*,
  *Last contact*, *Signed in as*; diagnostics (D8)

### Blocks

1. Setup flow: checked again when opened, the two names, the address's
   origin, the address from discovery
2. Titles: from the name and the way the entry signs in; automatic titles
   kept current
3. Server device: device, diagnostic entities, diagnostics
4. Documents: `README.md`, changelog

## Discussion

- **D1-A.** The flow reads the server again whenever its sign-in step - the
  menu or the key form - is opened again, as when the card of a discovered
  server is clicked long after the discovery; the record's `reg` it was
  discovered with no longer counts then, since only the request itself
  says whether requests are taken. A debug line names what decided.
- **D2-A.** The name Home Assistant gives itself in Massimo is a field of a
  form before the request, filled in with Home Assistant's name.
- **D3-A.** A discovery updates the address of an entry only where the
  entry took it from an announcement, or where the entry is registered
  and the address is the record's `url`, which answered; an address typed
  by hand is kept otherwise.
- **D4.** Massimo's side - a display name beside the native one, the found
  URL as a link and copyable, a "Register" button opening Home
  Assistant's "Add Massimo", the "not registered" check, the panel's
  "Key issued" - went to Massimo's session "HA Bridgehead" as a briefing.
- **D5-A.** The address field of "Add Massimo" is filled in from a server
  Home Assistant discovered and has not configured.
- **D6-A.** The entry's name is a field of the Register and key steps,
  filled in with "Massimo <loc>", the record's location, or the address's
  host where none is known.
- **D7-A.** The title is the name, followed by `(key of <user>)` where the
  key is a person's; a title renamed by hand is kept.
- **D8-A.** A device for the server, the Cubes under it, with diagnostic
  entities and the integration's diagnostics.
- **The owner's word** (2026-11-15): PLAN++ with D1-A to D3-A, D5-A to D8-A.

## Analysis

- **Why the Pi showed the key form.** `async_step_zeroconf` reads the
  server, then `_sign_in` decides between the menu and the key form; Home
  Assistant shows the result when the card is clicked, by calling the
  current step again without input, and nothing reads the server again.
  Against jaguar's Massimo as it answered later, the same flow shows the
  menu; what it answered at the discovery cannot be seen any more.
- **Opened again.** Home Assistant resumes a flow with
  `async_configure(flow_id)`, the current step called without input.
  `async_step_sign_in` is reached only that way (the menu is no option of
  itself). `async_step_api_key` without input is reached both by the menu's
  option and by a resume; the flow's `cur_step` tells them apart: on a
  resume it is the key form itself.
- **The register step** is a progress step; a form before it, of the same
  step id, takes the two names; Home Assistant resumes the progress by the
  same step.
- **The address's origin** is kept in the entry's data (`announced`), and
  whether the entry was registered (`registered`); the coordinator's
  `integration` says it for a loaded entry.
- **A discovered server's address** is in the flow's context as
  `configuration_url`, which Home Assistant's discovery card shows too;
  `async_progress_by_handler` lists the flows in progress.
- **Titles.** An entry's title is plain text, no icon or tooltip. The
  name chosen is kept in the data (`name`), and the title last set
  automatically (`auto_title`); a title that differs from it was renamed
  by hand. An entry made before has neither: a title `Massimo` or
  `Massimo (<user>)` is automatic, its name `Massimo`.
  The words `key of` come from the translations (`exceptions` category,
  the one Home Assistant lets an integration fill freely).
- **The server device** is identified by the node id, the entry's unique
  id; it is registered before the Cubes, which name it as `via_device`.
  The coordinator reads `/me` on every update (it read it only with the
  feature `integration`), keeps the time of its last read or event as the
  last contact, and the entities follow it.

## Implementation Plan

### Block 1: Setup flow

1. `async_step_sign_in` and a resumed `async_step_api_key` read the server
   again (`reg` no longer counted), with a debug line naming the feature,
   the mode and the record's `reg`.
2. `register`: a form with `name` (in Massimo, default Home Assistant's
   name) and `title` (in Home Assistant, default "Massimo <loc|host>"),
   then the request and the progress as before.
3. The key form takes `title` too, except in re-authentication.
4. `announced` and `registered` in the entry's data; the discovery's
   update of a configured entry per D3-A.
5. The user step's address filled in from a discovered, unconfigured
   server (`configuration_url` in the context).
6. Texts in `strings.json`, `en.json`, `de.json`.
7. **Verification:** `tests/test_config_flow.py`: a resumed key form
   offers the menu; the names reach Massimo and the entry; discovery keeps
   a typed address and follows the record for a registered entry; the
   user step's default; ruff, hassfest.

### Block 2: Titles

1. `entry_title(name, user, registered)`, with the `key of` text
   translated.
2. The flow sets it on creation, and on re-authentication or
   reconfiguration where the title was automatic.
3. The coordinator sets it after reading `/me` where the title is
   automatic; an entry made before gets `name` and `auto_title`.
4. **Verification:** tests: a registered entry's title is its name; a
   person's key adds `(key of …)`; a title renamed by hand is kept; an old
   `Massimo (<user>)` becomes `Massimo`; ruff.

### Block 3: Server device

1. The server's device: the entry's name, model `Massimo`, Massimo's
   version, the address as `configuration_url`; the Cubes `via_device` it.
2. Diagnostic entities of it: `connected` (connectivity, always available),
   `last_contact` (timestamp, disabled by default), `signed_in_as` (enum:
   `registered`, `user_key`, `no_users`; the user as an attribute).
3. `diagnostics.py`: the entry's data without the key, the server's health,
   `/me` without secrets, the Cubes counted, the last contact.
4. **Verification:** tests: the device and its Cubes beneath; the three
   entities' states; a stream broken turns `connected` off; diagnostics
   carry no key; ruff, hassfest.

### Block 4: Documents

1. `README.md`: the names asked, the titles, the server device.
2. The changelog fragments of Blocks 1 to 3 checked together.
3. **Verification:** `changelog.sh check`, `check-citations.sh`,
   `check-plans.sh`.

## Proposed commit message

For the revision, committed on its own before Block 1:

```
chore(aps): +SetupPolish v1.0

Follow-ups from the first registration: the flow checked again when opened, two names, titles that say whose key, a server device.

Key changes:
- Blocks 1 to 4: setup flow, titles, server device, documents
- D1-A to D3-A, D5-A to D8-A, as the owner took them with PLAN++

File-revision-v1: GUIDELINES/wip/2026-11-15_20-34_AP_SetupPolish_names_titles_server_device.md::v1.0::2026-11-15::All::the plan
Assisted-by: claude-code:claude-opus-5-5
```

Each block's commit message is written with the block, under PLAN++.

## Change History

- v1.0 (2026-11-15): the plan, from the owner's first registration on the
  Pi; D1-A to D3-A and D5-A to D8-A with PLAN++, D4 sent to Massimo.
