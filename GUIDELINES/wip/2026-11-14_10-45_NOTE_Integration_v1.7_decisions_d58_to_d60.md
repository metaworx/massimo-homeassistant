# NOTE Integration v1.7: decisions D58 to D60

The owner's decisions of 2026-11-14 on Block 8, after its first run on
`main`, and the fix that run asked for.

## Decisions

- **D58-A.** A ruleset on `main` requires CI's checks before a merge:
  hassfest, HACS, ruff and "Tests against Massimo main"; a repository admin
  may bypass it. As Massimo's "main: checks before merge".
- **D59-A.** A release signs its `SHA256SUMS` too, with the zip's key:
  `SHA256SUMS.sig` beside it, one check for every file a release carries.
- **D60-A.** actionlint comes from the guidelines: a `tools/actionlint.sh`
  running one pinned version from its Docker image or as a checked binary,
  chosen by a flag; the owner's Claude Code settings allow that script
  alone. Asked of the guidelines' session "CLI scripts libraries";
  workflows here are linted with it once the submodule carries it.

## The first run on `main`

Block 8's merge ran `release.yml` for the first time:
the checks and the build passed, and signing stopped at "SIGNING_KEY is not
set in this environment".
`ci.yml` called `release.yml` without `secrets: inherit`, and a called
workflow then sees no secret, not even its environment's;
Massimo's `ci.yml` carries it for the same call.
Fixed beside D59-A; `distro/devel` and the site come with that fix's merge.
