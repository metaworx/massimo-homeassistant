# NOTE Integration v1.6: how Block 8 went

The `PLAN++` run of 2026-11-14, Block 8 (distribution), and where it went
differently from v1.6.

## Where the work differs from the plan

1. **`actionlint` was not run**: it is not installed here, and its install
   was refused. The workflows were parsed as YAML and their steps run by
   hand (below); they run in full first when the branch is pushed and
   merged.
2. **The zip is signed itself**, not `SHA256SUMS`: one signature per zip,
   kept in its branch as `.distro/massimo.zip.sig`, so that the site can
   check a zip it makes again from the branch. A release still carries
   `SHA256SUMS`, unsigned, for `sha256sum -c`.
3. **The check of a branch's key**: `git verify-commit` takes any key of
   `allowed_signers`, whoever the committer; `site/build.sh` therefore also
   checks that the principal is the channel's (release, or rolling for
   devel).
4. **The tests against Massimo's newest release** are a second entry of the
   test job's matrix, for a tag's run alone; Massimo's newest release today,
   v0.15.0-alpha.1, has no `features`, so a tag's run fails there until
   Massimo's next release (Block 10 waits for it anyway).
5. **CI's HACS check** keeps `ignore: topics` alone: the brand images are
   in `brand/` since #7.
6. **The contract** rises to v1.2.0: `tools/`, `site/` and `keys/` among the
   source directories, the release by CI, `tools` in the lint command.

## Made on GitHub

- Environments: `signing` (tags `v[0-9]*.[0-9]*.[0-9]*`, the owner
  approves), `signing-rolling` (`main`); `github-pages` admits the same
  tags beside `main`. As Massimo's.
- Secrets: `SIGNING_KEY` in each (the release key, the rolling key),
  `DISTRO_DEPLOY_KEY` in both, piped from `~/.ssh`, never shown.
- The deploy key "distro/* branches (release.yml)", with write access.
- The ruleset "distro/* branches: written by release.yml alone":
  creation, update, deletion and force pushes refused but to a deploy key.
- Not made: a ruleset requiring checks on `main` - not decided.

## The check by hand

On this machine, into a scratch bare repository:
a devel build and a 0.1.0 built, signed with the real keys from `~/.ssh`,
each signature checked against `keys/allowed_signers`;
0.1.0 written to `distro/beta` and `distro/alpha`, devel to `distro/devel`,
each commit signed and checked;
`site/build.sh` built the site from them: the three channels in the home
page's table, each zip the same bytes as the build's, the README as a page
with its links to GitHub.
The scratch refs were removed afterwards; nothing was pushed.
