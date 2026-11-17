# AP ServerCompat v1.0: Massimo channels in CI

## TL;DR

CI tests the integration against every Massimo channel a box can run,
in place of Massimo's untested `main`, as a matrix the run computes.

- tests against Massimo `main` (+ newest release on a tag) → every
  `release/*` branch or tag but `nightly`, one job per commit (D1, D3)
- the newest-release step for tags → gone, `release/alpha` covers it (D2)
- a failure against any channel → the PR blocked (D5)
- one check to require → "Tests passed against Massimo", whatever the
  matrix holds; the ruleset follows it
- a manual run → still any ref of Massimo's, `main` included
- "this Massimo is too old" → not now, an open point (D4)

### Blocks

1. CI: the channel matrix, the check that sums it up
2. Documents: `CONTRIBUTING.md`, the contract's test gate
3. Ruleset: "main: checks before merge" requires the new check

## Discussion

- **D1-A** (the owner, 2026-11-17). The tests run against every branch
  and tag under Massimo's `release/` but `release/nightly`, as a matrix:
  `release/devel` (`main` after its CI), and `release/alpha`, `beta`,
  `stable` as they come; two names on one commit are one job.
  A manual run names any ref instead, `main` included.
- **D2-A.** A version tag's run no longer adds Massimo's newest release:
  `release/alpha` is it.
- **D3-A.** `release/nightly` is left out until it is clear what it is.
- **D4-A.** No "this Massimo is too old" message for now; the integration
  loses what a server's `features` do not list. Open point, below.
- **D5-A.** A failure against any channel blocks the PR, as `main`'s did.
- **The owner's word:** `PLAN++` with D1-A to D5-A (2026-11-17).

**Open point (D4):** a floor - the features the integration cannot work
without - a repair below it, and the oldest Massimo named in `README.md`.

## Analysis

- **Massimo's refs** (2026-11-17, `git ls-remote`): `refs/heads/release/alpha`
  at v0.16.0-alpha.1, `refs/tags/release/devel` moved in place by each devel
  build, `refs/tags/release/nightly` older than devel.
  Branches and tags both: the matrix reads `refs/heads/release/*` and
  `refs/tags/release/*`, a tag by its peeled commit where it is annotated,
  and checks out the commit, so that a name both a branch and a tag carry
  is not ambiguous.
- **The suite** passes against v0.16.0-alpha.1 and `main` of 2026-11-16
  (89 tests); it cannot run against a Massimo without `integration`, its
  setup registering one.
- **The required check:** the ruleset "main: checks before merge" (D58-A of
  AP Integration) names "Tests against Massimo main", the matrix job's name
  today. A matrix job's name carries its entry, so a job that needs the
  matrix and fails unless every entry passed gives the ruleset one name to
  require, as Massimo's "All tests passed" does.
  Until the ruleset names it, a PR that changes the job waits for a check
  that never comes; the owner, an admin, may bypass it.
- **`release.yml`** is called once every check passed: it needs the sum-up
  job in place of the matrix.

## Implementation Plan

### Block 1: CI

1. `ci.yml`, "Which Massimo": without `massimo_ref`, the refs of
   `git ls-remote` under `release/`, `release/nightly` left out, each name's
   commit (a tag's peeled one), grouped by commit, as a matrix of
   `{label, ref}`; none found is an error. With `massimo_ref`, that ref
   alone. The input's default becomes empty.
2. The test job: one per entry, named by its label, Massimo checked out at
   its commit.
3. "Tests passed against Massimo": needs the test job, runs always, fails
   unless it succeeded; `release` needs it in place of the test job.
4. The header and the comments say what is tested against.
5. **Verification:** actionlint (`GUIDELINES/shared/tools/actionlint.sh`);
   the matrix script run here on Massimo's refs; the suite against
   `release/devel` built here.

### Block 2: Documents

1. `CONTRIBUTING.md`: the local build from Massimo's `release/devel`; what
   CI builds; a tag's run.
2. The contract (`GUIDELINES/project/_CONTRACT.md`, v1.3.0): the test gate
   against a `massimo` built from Massimo's `release/devel`;
   `GUIDELINES/project/_README.md` likewise; `sync-docs.sh` writes
   `AGENTS.md` and `GUIDELINES/README.md`.
3. **Verification:** `sync-docs.sh --check`, `check-citations.sh`,
   `changelog.sh check` (nothing shipped).

### Block 3: Ruleset

At a gate of its own, once the branch is pushed and its run has reported
the new check: the ruleset "main: checks before merge" requires "Tests
passed against Massimo" in place of "Tests against Massimo main",
by `gh api` as the owner's account allows, or by the owner.

**Verification:** the ruleset read back; the PR mergeable once its checks
pass.

## Proposed commit message

For the plan, committed on its own before Block 1:

```
chore(aps): +ServerCompat v1.0

CI tests against Massimo's release channels, not its untested main.

Key changes:
- Blocks 1 to 3: the channel matrix, the documents, the ruleset
- D1-A to D5-A as the owner took them with PLAN++

File-revision-v1: GUIDELINES/wip/2026-11-17_11-30_AP_ServerCompat_massimo_channels_in_ci.md::v1.0::2026-11-17::All::the plan
Assisted-by: claude-code:claude-opus-5-5
```

Each block's commit message is written with the block.

## Change History

- v1.0 (2026-11-17): the plan, from PR #16's failure against Massimo's
  `main`; D1-A to D5-A with `PLAN++`.
