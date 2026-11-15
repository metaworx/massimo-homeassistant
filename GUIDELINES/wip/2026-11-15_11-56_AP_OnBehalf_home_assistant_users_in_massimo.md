# AP OnBehalf v1.0: Home Assistant users in Massimo

## TL;DR

The integration registers with Massimo by a code instead of a typed key,
and names the Home Assistant user, and the user's level, on each call made
for them (Massimo's `integration` feature, its AP IntegrationUsers v1.0).
This is the plan of its own that AP Integration's D56 calls for.

- setup → a typed key → registration by a code shown while Home Assistant
  waits, the typed key still offered beside it
- mDNS → host and port → the record's `url` where it answers, `reg`
- re-authentication, reconfiguration → register again, or a key
- writes, `get_program`, `copy_program`'s source → no user →
  `X-MassimoHA-On-Behalf-Of`: the user's id, name, level, installation id;
  `id=system` without a user (D55-B)
- refusals → every 403 an auth error → the refusal's `code`, translated
- repairs → a typed key on a server that registers; another installation
  id than the one Massimo accepted
- a Massimo without the feature, or a key that is no integration's →
  as today, no header

### Blocks

1. Client: the header, refusals with their code, registration, `/me`
2. Setup flow: registration with its code, mDNS `url` and `reg`, reauth
   and reconfigure
3. Acting for users: the header on each call made for a user, its level,
   the refusals, the repairs
4. Documents: `README.md`, `CONTRIBUTING.md`

## Discussion

- **D1-A.** The setup flow offers registration first and a typed key
  second, on one menu, wherever Massimo has the feature `integration`;
  a server without users (open mode) and an older Massimo go straight to
  the key form, as today.
- **D2-A.** An entry with a typed key, on a server with the feature, gets a
  repair saying it may register (reconfigure, then register).
  Until then the entry keeps working without the header.
- **D3-A.** The level is the user's for the call's target:
  `admin` for an administrator, otherwise `control` where the user may
  control the entity, `view` where only read.
- **D4-A.** `instance_pending` - another installation id than the one
  Massimo accepted, as after a backup restored on a new machine - raises a
  repair saying to accept the installation in Massimo;
  until then each call made for a user fails with a translated message.
- **D5-A.** From mDNS the address is the TXT `url` where the server answers
  there, host and port otherwise; `reg=0` offers only the typed key.
- **D6-A.** The plan's name is `OnBehalf`; `IntegrationUsers` is Massimo's.
- **The owner's word** (2026-11-15): PLAN++ with the recommendations.
  The owner has connected Home Assistant with Massimo by a typed key, and
  values are read; nothing of the plan changes for it.

## Analysis

**Massimo's side** (its `docs/api-v1.md`, "Integrations" and "Acting for an
integration's users"), on its `main`, not in a numbered release yet:
`/healthz` lists `integration: "1.0"`.

- `POST /api/v1/integrations/requests`, without a key:
  `{kind: "homeassistant", name, instance_id, url, version}` →
  `201 {id, code, expires_at}`; `403` with requests off, `429` too many.
- The owner approves it (`POST /api/v1/integrations/{uuid}/approve`),
  optionally attaching it to an integration registered before.
- `GET /api/v1/integrations/requests/{id}?code=` → `202` waiting,
  `200 {key, integration}`, `404` a wrong code, `410` refused, expired or
  collected and used.
- The header: `id=<32 hex>|system; level=view|control|admin;
  instance=<32 hex>; name*=UTF-8''…; system_generated`.
  The name is at most 128 bytes.
- Refusals are JSON `{error, code}`: `bad_header` (400), `not_integration`,
  `integration_disabled`, `instance_pending`, `user_disabled`, `forbidden`
  (403).
  A call with the header from a key that is no integration's is refused, so
  the header goes only where `/me` names the key's `integration`.
- `/me` answers `integration` (`uuid`, `key`, `name`, `state`,
  `instance_id`), null for any other key.
- The TXT record of `_massimo._tcp` adds `url` (`<node>.local` where the
  owner set none), `loc`, `reg`, `api=1`.

**The integration today.**

- `api.py`: `_check` turns every 401 and 403 into `MassimoAuthError`; the
  coordinator turns that into re-authentication.
  Polls and the stream go without the header, so of the codes only
  `integration_disabled` and `forbidden` can reach them; re-authentication
  stays right for those (a new key, or a new registration attached in
  Massimo).
- Each write, and the programme read, goes through `MassimoEntity.write`.
  Home Assistant sets the call's context on the entity before an entity
  service runs (`entity.async_set_context`), so the call's user is
  `self._context.user_id`; an automation's context has no user.
  `get_program` is a service of the integration since Block 9 of AP
  Integration, and `copy_program` reads another room, so both pass the
  context explicitly rather than read another entity's.
- The installation id is `homeassistant.helpers.instance_id.async_get`,
  32 hex digits, Massimo's `instance_id`.
- A user's id is 32 hex digits; `user.system_generated` marks the
  Supervisor's, Cloud's and the like; `user.name` may be empty.

**The design.**

- The client stays free of Home Assistant: `MassimoClient.acting_for(header)`
  answers a client sharing the session that sends the header; the header
  is built in `entity.py`.
- An entity's call takes the client it is to use:
  `self.write(lambda client: client.set_lock(…))`, the client acting for the
  call's user where the key is an integration's.
- The coordinator reads `/me` with its update where the server has the
  feature, and keeps `integration`; where its `instance_id` is not this
  installation's, one call with the header makes Massimo record the new id,
  and the repair says to accept it.
- The registration's wait is Home Assistant's progress step, a task polling
  every two seconds until the request is approved, refused or expired.

## Implementation Plan

### Block 1: Client

1. `MassimoRefusedError(MassimoAuthError)` with `code`, raised by `_check`
   for a JSON body with a `code`, 400 or 403; `MassimoAuthError` otherwise
   as before.
2. `acting_for(header)`, and the header sent by `_headers`.
3. `request_registration(…)` and `collect_registration(id, code)`
   (`None` while waiting; `MassimoRegistrationGone` for 404 and 410;
   registration refused, 403, as `MassimoRefusedError` with code
   `requests_off`).
4. **Verification:** `tests/test_api.py` against the server: a request
   approved with the owner's token and collected; the header acting for a
   user; a refusal's code; ruff.

### Block 2: Setup flow

1. `user`: the address and the certificate check; then the menu
   (`register`, `api_key`) where `/healthz` has the feature and `/me`
   without a key says users, else the key form.
2. `register`: the request, then the progress step showing the code;
   `register_done` makes the entry, or updates it in reauth and
   reconfigure; refused or expired aborts with its reason.
3. `zeroconf`: the TXT `url` where `/healthz` answers there, else host and
   port; `reg=0` → the key form.
4. `reauth_confirm` and a new `reconfigure` step: the same menu.
5. Texts in `strings.json`, `en.json`, `de.json`.
6. **Verification:** `tests/test_config_flow.py`: registration approved,
   refused; the key form as before; zeroconf with `url`; reauth by
   registration; hassfest.

### Block 3: Acting for users

1. `entity.py`: `on_behalf_header(hass, context, entity_id)` - the level per
   D3-A, `system` without a user, `system_generated`, the name encoded by
   RFC 8187 and cut at 128 bytes, the installation id.
2. `MassimoEntity.write(call, context=None)`: the client acting for the
   call's user where `coordinator.integration` is set; refusals translated
   by code; `instance_pending` raises the repair.
3. Each write and `read_program` through it; `get_program` and
   `copy_program` pass the call's context.
4. The coordinator reads `/me`; the repairs `register` (D2-A) and
   `instance_pending` (D4-A), each removed once it no longer holds.
5. **Verification:** tests: a write by an administrator, a control user and
   an automation, each seen in Massimo's integration users with its level;
   `get_program` by a viewer as `view`; a key typed by hand sends no header
   and gets the repair; an installation id changed gets the other; ruff,
   hassfest.

### Block 4: Documents

1. `README.md`: setting up by registration; what Massimo then shows.
2. `CONTRIBUTING.md`: the tests' registration with the owner's token.
3. The changelog fragments of Blocks 1 to 3 checked together.
4. **Verification:** `changelog.sh check`, `check-citations.sh`.

## Proposed commit message

For the revision, committed on its own before Block 1:

```
chore(aps): +OnBehalf v1.0

The integration's side of Massimo's integration feature: registration by a code, and the user named on each call made for one.

Key changes:
- Blocks 1 to 4: client, setup flow, acting for users, documents
- D1-A to D6-A, as the owner took them with PLAN++

File-revision-v1: GUIDELINES/wip/2026-11-15_11-56_AP_OnBehalf_home_assistant_users_in_massimo.md::v1.0::2026-11-15::All::the plan
Assisted-by: claude-code:claude-opus-5-5
```

Each block's commit message is written with the block, under PLAN++.

## Change History

- v1.0 (2026-11-15): the plan, from AP Integration's D55-B and D56 and
  Massimo's integration feature; D1-A to D6-A with PLAN++.
