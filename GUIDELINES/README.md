<!-- GENERATED FILE - DO NOT EDIT.
     Source: project/_README.md + project/_CONTRACT.md + shared/_README.md
     Regenerate: GUIDELINES/shared/tools/sync-docs.sh
     Contract version: v1.0.0 -->


# Massimo for Home Assistant (v1.0.0)

The Home Assistant integration for Massimo, the server that holds eQ-3 MAX!
Cubes: Massimo keeps the Cubes, their radio budget, pairing and week programmes,
and Home Assistant becomes one more client of its HTTP API.
It is for a Home Assistant that is a site's hub,
with Massimo running beside it for the MAX! heating.

## Working on it

```bash
git clone --recurse-submodules git@github.com:metaworx/massimo-homeassistant.git
cd massimo-homeassistant
uv python install 3.14
uv venv --python-preference only-managed --python 3.14 .venv
VIRTUAL_ENV=.venv uv pip install -r requirements_test.txt
# a massimo binary and the fake Cube's greeting, from Massimo's checkout:
(cd ../massimo && go build -o /tmp/massimo ./cmd/massimo)
MASSIMO_REQUIRED=1 MASSIMO_BIN=/tmp/massimo \
MASSIMO_GREETING=../massimo/tools/ui-test/greeting.txt .venv/bin/python -m pytest
```

To try it in a Home Assistant, copy `custom_components/massimo` into its
configuration's `custom_components` and restart it.

## The rules that apply here

The conventions below are not AI configuration:
they are how this project is written,
and an agent is simply another party required to follow them.

- The contract that follows is generated into `/AGENTS.md` as well,
  so people and agents are held to the same text.
- The shared conventions live in `GUIDELINES/shared` — commit policy,
  quality pass, per-language testing, linting and code style.
- `GUIDELINES/README.md` explains the gate protocol:
  what an agent asks before it changes anything,
  and what `EXEC` and its relatives authorise.

Both generated documents come from the fragments in `GUIDELINES`.
Editing a generated file is wasted work — change the fragment and re-run
`GUIDELINES/shared/tools/sync-docs.sh`.

---


# Massimo for Home Assistant — Project Contract (v1.0.0)

What binds work in this project, for everyone working on it.
Inlined into `/AGENTS.md` for agents and into `GUIDELINES/README.md` for people,
so that the two cannot drift apart.

> `{{TODO: …}}` is a value you replace, braces and all.
> The other double-braced names, such as `Massimo for Home Assistant`,
> are filled in when the documents are generated: leave them as they are.

## 1. Project Facts

> No absolute paths here.
> An agent is already inside the checkout,
> so the repository root is `git rev-parse --show-toplevel`;
> a checkout can live anywhere and this file is committed.
> Machine-specific values belong in `GUIDELINES/config.local.ini`,
> which is not tracked.

| Fact                  | Value |
|-----------------------|-------|
| Project name          | Massimo for Home Assistant |
| Language(s)           | declared as `project.languages` in `GUIDELINES/config.ini`, kept honest by `GUIDELINES/shared/tools/detect-languages.sh --check` |
| Source directories    | `custom_components/massimo/` (the integration: `api.py` the client of Massimo's API, `config_flow.py`, `coordinator.py`, the platforms to come, `translations/`), `tests/` (pytest against a real Massimo server), `.github/workflows/` (CI) |
| Shipped-code paths    | declared as `project.shipped` in `GUIDELINES/config.ini` and listed below; kept honest by `GUIDELINES/shared/tools/changelog.sh check` (rule: `GUIDELINES/shared/COMMIT.md` §5) |
| Version manifest      | `custom_components/massimo/manifest.json`, its `version`; HACS and the Marketplace read the repository's release tags; how a release is cut is still to be decided (the plan's release block) |
| Test gate command     | `MASSIMO_REQUIRED=1 MASSIMO_BIN=<massimo> MASSIMO_GREETING=<greeting.txt> .venv/bin/python -m pytest` against a `massimo` built from Massimo's checkout and its `tools/ui-test/greeting.txt` (where they are on this machine: `GUIDELINES/config.local.ini`, section `[massimo]`); then hassfest: `docker run --rm -v "$PWD":/github/workspace ghcr.io/home-assistant/hassfest`; CI runs both, and HACS's validation |
| Lint command          | `ruff check custom_components tests` and `ruff format --check custom_components tests` print nothing to fix, with the settings of `pyproject.toml` (ruff 0.17.4, as CI pins it) |
| Commit summary        | declared as `[commit]` in `GUIDELINES/config.ini` and shown below; held to it by `GUIDELINES/shared/tools/commit-msg.sh` (rule: `GUIDELINES/shared/COMMIT.md` §3.1) |

A commit touching any path listed below must carry a `CHANGELOG.md` bullet.
The list is generated from `project.shipped`,
so it cannot drift from what the check enforces - edit the config,
not this block:

<!-- BEGIN GENERATED SHIPPED-PATHS - do not edit; run "GUIDELINES/shared/tools/changelog.sh update-contract" -->
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
no test reads them, and `GUIDELINES/shared/tools/fingerprint.sh` leaves them out
of the code fingerprint a CI gate compares.
None of them is shipped.
The list is generated from `[ci] untested` - edit the config, not this block,
and delete both where the project declares no such list:

<!-- BEGIN GENERATED UNTESTED-PATHS - do not edit; run "GUIDELINES/shared/tools/fingerprint.sh update-contract" -->
- `GUIDELINES/wip/**`
- `GUIDELINES/project/**`
- `AGENTS.md`
- `GUIDELINES/README.md`
- `CHANGELOG.md`
- `CHANGELOG.d/**`
- `LICENSE`
<!-- END GENERATED UNTESTED-PATHS -->

The commit form is generated from `[commit]` in `GUIDELINES/config.ini` -
edit the config, not this block:

<!-- BEGIN GENERATED COMMIT-FORM - do not edit; run "GUIDELINES/shared/tools/sync-docs.sh" -->
Every commit summary opens as `config.ini`'s `[commit]` keys ask (COMMIT.md §3.1):
`format = conventional`, `component = required`, `keywords = conventional`, `attribution = assisted-by`.

- **Form:** `type(component): headline`, for example `feat(api): Cache registry lookups`.
- **Component:** required, but of a release and a merge: a name of letters, digits, `.`, `_`, `/` and `-`; behind a role's token, after a colon: `fix(security:api): Close a hole`.
- **An incompatible change:** `feat(api)!: Remove a call`, or a `BREAKING CHANGE:` trailer.
- **A plan's own commit:** `chore(aps): +Name v1.0` (COMMIT.md §6).
- **An agent's commit:** ends with `Assisted-by: AGENT_NAME:MODEL_VERSION` - the tool or harness, then the exact model id, e.g. `Assisted-by: claude-code:claude-opus-5-5` (COMMIT.md §3.3).

| Role | Opens with | For |
|------|------------|-----|
| task | `feat:`, `docs:`, `refactor:`, `perf:`, `test:`, `build:`, `ci:`, `revert:` | features, logic changes, documentation updates |
| fix | `fix:` | bug fixes |
| security | `fix(security):` | security fixes and hardening |
| cleanup | `style:` | formatting and layout only, no functional change |
| wip | `wip:` | an intermediate state; a non-wip commit follows |
| update | `chore:` | environment, dependency or test-config updates, plans |
| release | `chore(release):` | the version bump, made by changelog.sh cut |
| merge | `merge:` | a commit with more than one parent |
<!-- END GENERATED COMMIT-FORM -->

## 2. Primary References

- `/AGENTS.md` — runtime behavior contract, gating flow, action-plan workflow.
- `GUIDELINES/shared/lang/<language>/TESTING.md` and `LINTING.md` — language
  baselines for each language in `project.languages`;
  this file's facts table overrides their example commands.
- `GUIDELINES/shared/COMMIT.md` — commit workflow, gating, message policy.
- `GUIDELINES/shared/ENVIRONMENTS.md` — host/agent command conventions.
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
  The fake Cube acknowledges a setpoint but changes no state,
  so no state event follows one;
  a room rename (a metadata write) makes the server announce events.
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

- This document follows the shared governance rules in `GUIDELINES/shared/GOVERNANCE.md`.

---


# Working with the agent (v1.8.0)

This is the human half of the contract.
The agent's rules live in `/AGENTS.md`;
this explains what the agent will do to you, what the words it sends you mean,
and what it needs back.

## 1. The short version

The agent does not change your repository and then tell you.
For anything non-trivial it **stops and asks first**,
in a fixed format called a *gate message*, and waits.
You reply with one word — usually `EXEC` — and it proceeds.

Two moments always stop:
before a non-trivial code change (you approve the plan) and before every
`git commit` (you approve the message).
Everything else is ordinary work.

## 2. Gate messages

A gate message is the agent's request for permission.
It always carries its fields in the same order, so you can skim it;
the ones in italics appear only where they apply:

- **Checkpoint** — where the work stands
- **Last Action** — what it just did, in a line, with IDs you can check
- *Pending* — work the gate does not cover: an unpushed commit, a running job
- *CHANGELOG bullet*, *Proposed commit message*, *Files to be committed* —
  wherever a signal would commit
- *Open decisions* — numbered `D1`, `D2`, the options lettered,
  the recommended one first
- *Important notes* — numbered: what you need in order to decide
  and would not otherwise see
- **Confirmation needed** — each signal it offers,
  and everything that signal does

After sending one the agent must be silent until you answer.
If you see it send a gate and then keep working,
that is a violation of its own contract, and worth saying so.

Read **Confirmation needed** first, then the open decisions.
You can answer briefly - `EXEC+ D2-B`, or "as recommended".
A reply without a signal is taken as a question to weigh, and nothing is done.

## 3. Execution signals

One word, at the start or anywhere in your reply:

| Signal      | Means |
|-------------|-------|
| `EXEC`      | Do the gated action. Only that. |
| `EXEC+`     | Do it, then carry on with the next planned step. |
| `ROLLBACK`  | Undo the last edit. Required — the agent may not undo unasked. |
| `ERR`       | That went wrong; stop and diagnose before trying again. |
| `PLAN`      | Produce or revise the plan; do not execute yet. |
| `ASK`       | Answer my question; do not treat it as an instruction to act. |

The gate always tells you what `EXEC` will do and where `EXEC+` will go next.
If it doesn't, that is a defect in the gate, not something for you to infer.

`EXEC++` and `EXEC+++` are retired — say it in words instead.

You can also just answer in prose.
"Yes, but rename the second one first" is a perfectly good reply;
the signals exist for speed, not ceremony.

## 4. Action Plans

For anything beyond a trivial edit the agent writes an **Action Plan** before
touching code: what it found, what it intends to do step by step,
and the commit message it expects to propose.
You see a summary in the gate;
the full plan is written to a file (see §5) so it survives the conversation.

Plans are versioned — `AP Bild v1.2` — and each revision is a new file,
never an overwrite.
If you reject a plan, the next one is v1.3 and the reasoning that led there is
still on disk.

## 5. UAMF — where the agent's writing goes

A **User-Accessible Message File** is anything the agent wrote for you to read
rather than for the machine to run: action plans, analyses, migration notes.
They land in `GUIDELINES/messages/` with a timestamp in the name,
and they are **never overwritten** — a revision is always a new file.

This matters when a session ends badly.
The conversation may be gone; the reasoning is still there.

## 6. Recovering from a bad turn

Send `ERR`.
The agent stops and replies with a compact recovery block:
what it believes happened, what state things are in, and what it proposes.
Send `ERR` twice in a row and it escalates — it stops proposing and asks you to direct it.

`ROLLBACK` is separate and stronger: it authorises undoing the last edit.
The agent cannot do this on its own initiative, by design,
so if something needs reverting you have to say so.

## 7. What the agent must never do without you

- Commit — every commit is gated, with the full message shown first
- Undo your work — `ROLLBACK` only
- Overwrite a UAMF — revisions are new files
- Delete and recreate a file to make a large edit — it edits in place,
  so your IDE's local history survives
- Push, or anything else that leaves your machine, unless you asked

If any of these happens without your say-so, the agent has broken its contract.
Tell it; the rule it violated is in `/AGENTS.md` and it can name the section.

## 8. If this directory looks empty

Everything under `GUIDELINES/shared` lives in a git submodule,
which a plain clone leaves unpopulated.
The document you are reading is committed in the project,
so it survives that — but every link into `GUIDELINES/shared` will be dead until:

```bash
git submodule update --init GUIDELINES/shared
```

Cloning with `--recurse-submodules` does it up front.
In an overlay - a `GUIDELINES` that is a repository of its own,
in a project that does not carry the guidelines -
this document and the submodule are the overlay's,
and the command is run there:
`git -C GUIDELINES submodule update --init`.
If the same checkout is used from both Windows and WSL,
this saves a recurring annoyance:

```bash
git -C GUIDELINES/shared config core.fileMode false
```

## 9. Document Governance

- This document follows the shared governance rules in `GUIDELINES/shared/GOVERNANCE.md`.
