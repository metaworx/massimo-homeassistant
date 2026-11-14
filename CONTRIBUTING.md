# Contributing to Massimo for Home Assistant

How to work on the integration: setting up, testing, committing,
and cutting a release.
What binds every change - agents' and people's alike - is the project contract,
in [GUIDELINES/README.md](GUIDELINES/README.md),
and the shared rules it names (`GUIDELINES/shared/COMMIT.md` above all).
This file does not repeat them; it says how to do the work.

## Setting up

Python 3.14 through [uv](https://docs.astral.sh/uv/):

```bash
uv python install 3.14
uv venv --python-preference only-managed --python 3.14 .venv
VIRTUAL_ENV=.venv uv pip install -r requirements_test.txt
```

Under WSL, keep `--python-preference only-managed`:
a plain `uv venv --python 3.14` can take the Windows Python and make a Windows
venv.

The tests need a `massimo` binary,
built from `main` of [metaworx/massimo](https://github.com/metaworx/massimo):

```bash
git clone https://github.com/metaworx/massimo ../massimo
(cd ../massimo && CGO_ENABLED=0 go build -o "$PWD/massimo" ./cmd/massimo)
```

Where the checkout is on your machine goes in `GUIDELINES/config.local.ini`,
which is not tracked:

```ini
[massimo]
	checkout = /path/to/massimo
```

## Testing

The tests run against a real `massimo serve` and Massimo's fake Cube,
never against mocks of the API; `tests/conftest.py` starts both on free ports.
Nothing is ever sent to a real Cube from here.

```bash
MASSIMO_REQUIRED=1 \
MASSIMO_BIN=../massimo/massimo \
.venv/bin/python -m pytest
```

The fake Cube serves Massimo's fixture `rooms`
and carries out what it acknowledges;
its control port sets a device's state as the device's report would.
Without `MASSIMO_REQUIRED=1`,
the tests that need a server are skipped where `MASSIMO_BIN` is missing;
with it, as in CI, they fail.
CI builds `massimo` from Massimo's `main`,
or from the branch, tag or commit a manual run names,
so a change that needs something new in Massimo waits until Massimo has it on
`main`.

Then Home Assistant's own check of the integration:

```bash
docker run --rm -v "$PWD":/github/workspace ghcr.io/home-assistant/hassfest
```

And lint, with ruff 0.17.4, as CI pins it:

```bash
uvx ruff@0.17.4 check custom_components tests tools
uvx ruff@0.17.4 format --check custom_components tests tools
```

CI runs all three, and HACS's validation.

## Changing the code

- **Home Assistant 2026.10 and newer.**
  Schemas in `probatio`, overrides marked with `typing.override`;
  the tests run on the Home Assistant that
  `pytest-homeassistant-custom-component` in `requirements_test.txt` pins.
- **Texts** go in `translations/en.json` and `de.json`,
  with `strings.json` the same as `en.json`;
  hassfest refuses a URL inside a text.
- **Placeholders only**: no keys, tokens, real serials or real device names in
  code, tests or commit messages.
  The fake Cube's `KEQ0000100` and its devices are the ones to use.
- **Massimo is the other side.**
  What the integration needs from Massimo's API is made in Massimo first,
  and tested there; the integration then uses it.
- **The brand images** in `custom_components/massimo/brand/` are Massimo's
  mark, made by Massimo's `tools/brand/make_brand.py`, never edited here.
  To make them again, in Massimo's checkout (`tools/brand/README.md` there
  has the set-up):

  ```bash
  tools/brand/.venv/bin/python tools/brand/make_brand.py --flavour grayorange --scope homeassistant --yes
  ```

  and copy the eight files of `GUIDELINES/temp/brand/grayorange/homeassistant-brand/`
  into `custom_components/massimo/brand/`.

## Committing

- **Branches and pull requests** into `main`, which the owner merges.
- **Signed commits** (SSH, through the repository's git config).
  A locked key agent makes `git commit` hang,
  so run it as `timeout 60 git commit …`.
- **The summary** is `type(component): Headline`,
  for example `feat(integration): …` or `fix(tests): …`;
  `GUIDELINES/shared/tools/commit-msg.sh <message file>` checks a message
  before you commit it.
- **A changelog bullet** goes with every change to a shipped path
  (`custom_components/`, `hacs.json`),
  as a fragment of its own: `CHANGELOG.d/<Heading>/<slug>.md`,
  under a Keep a Changelog heading such as `Added` or `Fixed`,
  one bullet of at most three lines.
  `GUIDELINES/shared/tools/changelog.sh check --staged` says whether the
  change staged carries the bullet it owes,
  and `changelog.sh preview` shows the next release's section.

## Releases and channels

CI releases; nobody makes a GitHub release or writes a `distro/*` branch by
hand.
`ci.yml` calls `release.yml` for a push of `main` or of a version tag once
every check has passed, and `tools/dist.py` says what the run releases:

| Ref | Version | Channel | Released as |
|-----|---------|---------|-------------|
| `main` | `<last tag>-dev.<n>+g<commit>` (`0.0.0` before the first tag) | `devel` | `distro/devel` alone |
| `vX.Y.Z-alpha.N` | `X.Y.Z-alpha.N` | `alpha` | a GitHub pre-release |
| `v0.Y.Z`, `vX.Y.Z-beta.N`, `-rc.N` | as tagged | `beta` | a GitHub pre-release |
| `vX.Y.Z`, from 1.0.0 | `X.Y.Z` | `stable` | a GitHub release |

A release goes to its channel's branch `distro/<channel>`,
and to each less stable channel that holds an older version or none:
0.1.0 goes to `distro/beta` and `distro/alpha`.
A branch's root is the integration's folder, with its version in
`manifest.json`, `LICENSE`, and `.distro/` (`VERSION`, `SOURCE`, and the
zip's signature `massimo.zip.sig`);
each commit is on top of the last, so a clone follows it with `git pull`.
A tag's GitHub release carries the same tree as `massimo.zip`, its signature,
and `SHA256SUMS` with its own signature, one check for every file the
release carries; `devel` has no GitHub release, since HACS offers every
release it finds.

**Keys.**
Two keys sign, with SSH signatures (`ssh-keygen -Y sign`, namespace `file`
for a zip, `git` for a commit), and `keys/allowed_signers` names both:
the release key (`release@ha.massimo.metaworx.ch`) every tag's zip and
`distro/stable`, `beta` and `alpha`,
the rolling key (`rolling@ha.massimo.metaworx.ch`) `distro/devel`.
Each is the secret `SIGNING_KEY` of its environment:
`signing`, which only version tags may use and whose runs the owner
approves, and `signing-rolling`, which only `main` may use.
`DISTRO_DEPLOY_KEY`, in both, is the deploy key that pushes `distro/*`;
the ruleset on `distro/*` lets nothing else create, move or delete them.
The private halves are kept on the owner's machine, in
`~/.ssh/massimo-homeassistant-{release,rolling,distro}`.
A key replaced is replaced in its secret, in `keys/`, and, for the deploy
key, in the repository's deploy keys.

## The site

<https://ha.massimo.metaworx.ch>, GitHub Pages of this repository,
built by `site/build.sh` without a key and without state,
and deployed by `.github/workflows/site.yml`, which `release.yml` calls at
every run:
`site/`'s pages, the README as `readme.html`, `keys/`, and per channel
`distro/<channel>.zip` and its `.sig`.
Each zip is made again from its branch (`tools/dist.py zip`, the same bytes
for the same tree) and checked against the signature the branch carries,
and each branch's commit against `keys/allowed_signers`:
a mismatch fails the build, and nothing is deployed.
Pages keeps the first deploy of a commit, so a change to the site alone
shows with the next run for a new commit.
To look at it before a push:

```bash
site/build.sh --out /tmp/site
```

## Cutting a release

A release is a version in `CHANGELOG.md` and in
`custom_components/massimo/manifest.json`, and a signed tag `v<version>`;
CI makes the rest (above).

Every command of `changelog.sh` below only says what it would do,
until it is given `--force`.

1. **Choose the version.**
   `changelog.sh cut` without a version says what the fragments ask for:
   a patch where only `Fixed` and `Security` carry bullets,
   a minor where anything else does.
   A major is the author's call; no heading can tell it.
2. **Cut it** on a branch from an up-to-date `main`:

   ```bash
   GUIDELINES/shared/tools/changelog.sh cut X.Y.Z --commit --tag create
   ```

   This gathers the fragments into a section `## [X.Y.Z]`, removes them,
   writes `X.Y.Z` into `manifest.json`, commits that as
   `chore(release): …`, and tags the commit `vX.Y.Z`, signed.
   Read what it says, then run it again with `--force`.
3. **Merge it, then publish the tag.**
   The release commit goes into `main` through a pull request like any other,
   merged with a merge commit, so that the tagged commit stays in `main`'s
   history.
   Then `changelog.sh tag X.Y.Z --push --force` publishes the tag and nothing
   else.
4. **Approve the release.**
   The tag's run tests against Massimo's `main` and its newest release,
   then waits in the environment `signing` for the owner's approval;
   approved, it makes the GitHub release, writes the `distro/*` branches
   and deploys the site.
