> **Fragment** — inlined by `tools/sync-docs.sh`; not a standalone document.

# {{project_name}} (v1.0.0)

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
# a massimo binary, built from Massimo's main:
(cd ../massimo && go build -o /tmp/massimo ./cmd/massimo)
MASSIMO_REQUIRED=1 MASSIMO_BIN=/tmp/massimo .venv/bin/python -m pytest
```

To try it in a Home Assistant, copy `custom_components/massimo` into its
configuration's `custom_components` and restart it.

## The rules that apply here

The conventions below are not AI configuration:
they are how this project is written,
and an agent is simply another party required to follow them.

- The contract that follows is generated into `/AGENTS.md` as well,
  so people and agents are held to the same text.
- The shared conventions live in `{{shared_root}}` — commit policy,
  quality pass, per-language testing, linting and code style.
- `{{guidelines_root}}/README.md` explains the gate protocol:
  what an agent asks before it changes anything,
  and what `EXEC` and its relatives authorise.

Both generated documents come from the fragments in `{{guidelines_root}}`.
Editing a generated file is wasted work — change the fragment and re-run
`{{shared_root}}/tools/sync-docs.sh`.
