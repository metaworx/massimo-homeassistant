> **Fragment** — inlined by `tools/sync-docs.sh`; not a standalone document.

# {{project_name}} — Project Contract (v1.1.0)

What binds work in this project, for everyone working on it.
Inlined into `/AGENTS.md` for agents and into `{{guidelines_root}}/README.md` for people,
so that the two cannot drift apart.

> `{{TODO: …}}` is a value you replace, braces and all.
> The other double-braced names, such as `{{project_name}}`,
> are filled in when the documents are generated: leave them as they are.

## 1. Project Facts

> No absolute paths here.
> An agent is already inside the checkout,
> so the repository root is `git rev-parse --show-toplevel`;
> a checkout can live anywhere and this file is committed.
> Machine-specific values belong in `{{guidelines_root}}/config.local.ini`,
> which is not tracked.

| Fact                  | Value |
|-----------------------|-------|
| Project name          | {{project_name}} |
| Language(s)           | declared as `project.languages` in `{{guidelines_root}}/config.ini`, kept honest by `{{shared_root}}/tools/detect-languages.sh --check` |
| Source directories    | `custom_components/massimo/` (the integration: `api.py` the client of Massimo's API, `config_flow.py`, `coordinator.py`, the platforms to come, `translations/`), `tests/` (pytest against a real Massimo server), `.github/workflows/` (CI) |
| Shipped-code paths    | declared as `project.shipped` in `{{guidelines_root}}/config.ini` and listed below; kept honest by `{{shared_root}}/tools/changelog.sh check` (rule: `{{shared_root}}/COMMIT.md` §5) |
| Version manifest      | `custom_components/massimo/manifest.json`, its `version`, which `changelog.sh cut` writes; a release is a signed tag `v<version>` and a GitHub release made from it, which HACS offers (`CONTRIBUTING.md`, "Cutting a release") |
| Test gate command     | `MASSIMO_REQUIRED=1 MASSIMO_BIN=<massimo> .venv/bin/python -m pytest` against a `massimo` built from Massimo's `main` (where its checkout is on this machine: `GUIDELINES/config.local.ini`, section `[massimo]`); then hassfest: `docker run --rm -v "$PWD":/github/workspace ghcr.io/home-assistant/hassfest`; CI runs both, and HACS's validation |
| Lint command          | `ruff check custom_components tests` and `ruff format --check custom_components tests` print nothing to fix, with the settings of `pyproject.toml` (ruff 0.17.4, as CI pins it) |
| Commit summary        | declared as `[commit]` in `{{guidelines_root}}/config.ini` and shown below; held to it by `{{shared_root}}/tools/commit-msg.sh` (rule: `{{shared_root}}/COMMIT.md` §3.1) |

A commit touching any path listed below must carry a `CHANGELOG.md` bullet.
The list is generated from `project.shipped`,
so it cannot drift from what the check enforces - edit the config,
not this block:

<!-- BEGIN GENERATED SHIPPED-PATHS - do not edit; run "{{shared_root}}/tools/changelog.sh update-contract" -->
- `custom_components/**`
- `hacs.json`
- `:!tests/**`
- `:!GUIDELINES/**`
- `:!*.md`
- `:!.gitignore`
- `:!.gitattributes`
- `:!.gitmodules`
- `:!LICENSE`
<!-- END GENERATED SHIPPED-PATHS -->

A change touching only the paths listed below may skip the test suite:
no test reads them, and `{{shared_root}}/tools/fingerprint.sh` leaves them out
of the code fingerprint a CI gate compares.
None of them is shipped.
The list is generated from `[ci] untested` - edit the config, not this block,
and delete both where the project declares no such list:

<!-- BEGIN GENERATED UNTESTED-PATHS - do not edit; run "{{shared_root}}/tools/fingerprint.sh update-contract" -->
- `GUIDELINES/wip/**`
- `GUIDELINES/project/**`
- `AGENTS.md`
- `GUIDELINES/README.md`
- `CHANGELOG.md`
- `CHANGELOG.d/**`
- `LICENSE`
<!-- END GENERATED UNTESTED-PATHS -->

The commit form is generated from `[commit]` in `{{guidelines_root}}/config.ini` -
edit the config, not this block:

<!-- BEGIN GENERATED COMMIT-FORM - do not edit; run "{{shared_root}}/tools/sync-docs.sh" -->
<!-- END GENERATED COMMIT-FORM -->

## 2. Primary References

- `/AGENTS.md` — runtime behavior contract, gating flow, action-plan workflow.
- `{{shared_root}}/lang/<language>/TESTING.md` and `LINTING.md` — language
  baselines for each language in `project.languages`;
  this file's facts table overrides their example commands.
- `{{shared_root}}/COMMIT.md` — commit workflow, gating, message policy.
- `{{shared_root}}/ENVIRONMENTS.md` — host/agent command conventions.
- `CONTRIBUTING.md` — repository-specific contributor conventions.

## 3. Project-Specific Conventions

- **Massimo is the other side.**
  The integration is one more client of Massimo's HTTP API
  (Massimo's `docs/api-v1.md` and `docs/api-v1-openapi.yaml`),
  signed in with an API key of the role `integration`.
  A change the integration needs from Massimo's API is made in Massimo,
  under a plan of Massimo's, and tested there first;
  the integration then requires that Massimo version or skips what an older one
  cannot do, as `tests/` does for the event ids.
  Massimo's own documents on Home Assistant are its `docs/homeassistant.md`.
- **Tests run against a real `massimo serve` with the fake Cube**,
  never against mocks of the API: `tests/conftest.py` starts both on free ports.
  The fake Cube serves Massimo's fixture `rooms` and carries out what it
  acknowledges, as the devices would;
  its control port sets a device's state as a device's report would.
  The tests read the server as the integration does, with `?devices=real`.
  Nothing is ever sent to a real Cube from here.
- **Home Assistant 2026.10 and newer.**
  Schemas are written with `probatio`, not `voluptuous`; overrides carry
  `typing.override`; `async_setup_entry` returns `True`, as 2026.10 wants and
  2026.11 accepts.
  The tests run on the Home Assistant that
  `pytest-homeassistant-custom-component` in `requirements_test.txt` pins.
- **Python 3.14** through `uv`:
  `uv python install 3.14`, then
  `uv venv --python-preference only-managed --python 3.14 .venv`.
  A plain `uv venv --python 3.14` takes the Windows Python through WSL's
  interop and makes a Windows venv.
- **Texts** in `translations/en.json` and `de.json`,
  `strings.json` the same as English; hassfest refuses a URL inside a text.
- **Secrets and identities**, as in Massimo: no keys, tokens,
  real serials or real device names in code, tests or commit messages;
  the fake Cube's `KEQ0000100` and its devices are the placeholders.
- **Branches and pull requests**:
  develop on `main` through pull requests the owner merges;
  commits are signed (SSH, the repository's git config),
  run as `timeout 60 git commit …` because a locked key agent hangs.

## 4. Document Governance

- This document follows the shared governance rules in `{{shared_root}}/GOVERNANCE.md`.
