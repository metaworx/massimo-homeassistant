#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""What a release of the integration is, and its files: the version and
channel of a run, the tree a channel's branch holds, its zip, the channels a
release goes to, and the signed commit of a ``distro/<channel>`` branch.

Called by .github/workflows/release.yml and site/build.sh (CONTRIBUTING.md,
"Releases and channels"); Python's standard library and git alone.

  dist.py meta --ref <ref> [--sha <commit>]
      the run's version, channel, whether it is a pre-release, and the tag,
      as name=value lines for $GITHUB_OUTPUT; a tag is checked against
      manifest.json
  dist.py build --version <v> --source <commit> --out <dir>
      <dir>/tree: custom_components/massimo with <v> in its manifest,
      LICENSE, and .distro/ (VERSION, SOURCE); <dir>/massimo.zip of the
      tree without .distro/; <dir>/SHA256SUMS
  dist.py zip <tree> <zip>
      the zip of a tree, without its .distro/, the same bytes every time
  dist.py targets --version <v> --channel <c> [--held <channel>=<version>]...
      the channels a release goes to: its own, and each less stable one
      that holds an older version or none
  dist.py commit --tree <dir> --parent <commit|""> --key <file>
                 --name <name> --email <email> --message <text>
      a commit of the tree on top of the parent, signed with the SSH key;
      prints its id
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = Path("custom_components/massimo")
MANIFEST = SOURCE / "manifest.json"
ZIP_NAME = "massimo.zip"
DISTRO_DIR = ".distro"

# The channels, the most stable first: a release goes to its own channel and
# to every less stable one (D45). devel stands apart: it takes main alone.
CHANNELS = ("stable", "beta", "alpha")
DEVEL = "devel"

TAG = re.compile(r"^v(?P<core>(?P<major>0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*))(?:-(?P<pre>[0-9A-Za-z.-]+))?$")
VERSION = re.compile(
    r"^(?P<core>(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*))(?:-(?P<pre>[0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$"
)
MANIFEST_VERSION = re.compile(r'("version"\s*:\s*")([^"]*)(")')


class DistError(Exception):
    """A release that cannot be made as asked."""


def channel_of(version: str) -> str:
    """The channel of a version (D45): alpha where it carries ``alpha``,
    beta for any other pre-release part and below 1.0.0, else stable."""
    match = VERSION.match(version)
    if not match:
        raise DistError(f"not a version: {version}")
    pre = match["pre"] or ""
    if "alpha" in pre.split(".")[0]:
        return "alpha"
    if pre or match["core"].startswith("0."):
        return "beta"
    return "stable"


def is_prerelease(version: str) -> bool:
    """Below 1.0.0, or with a pre-release part: a GitHub pre-release (D45)."""
    return channel_of(version) != "stable"


def _key(version: str) -> tuple:
    """SemVer's precedence: the core numerically, a pre-release before its
    release, its identifiers numeric before alphanumeric; build ignored."""
    match = VERSION.match(version)
    if not match:
        raise DistError(f"not a version: {version}")
    core = tuple(int(part) for part in match["core"].split("."))
    if not match["pre"]:
        return (core, 1, ())
    ids = tuple((0, int(i), "") if i.isdigit() else (1, 0, i) for i in match["pre"].split("."))
    return (core, 0, ids)


def newer(a: str, b: str) -> bool:
    """Whether version a comes after version b."""
    return _key(a) > _key(b)


def targets(version: str, channel: str, held: dict[str, str | None]) -> list[str]:
    """The channels a release goes to: its own, and each less stable one
    that holds an older version or none."""
    if channel == DEVEL:
        return [DEVEL]
    out = []
    for name in CHANNELS[CHANNELS.index(channel) :]:
        have = held.get(name)
        if name == channel or have is None or newer(version, have):
            out.append(name)
    return out


def _git(*args: str, cwd: Path = ROOT, env: dict[str, str] | None = None) -> str:
    return subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True, text=True).stdout.strip()


def manifest_version(root: Path = ROOT) -> str:
    return json.loads((root / MANIFEST).read_text())["version"]


def devel_version(root: Path = ROOT, sha: str = "HEAD") -> str:
    """``<last tag>-dev.<n>+g<sha>``, as git describe counts; ``0.0.0`` and
    every commit before the first tag."""
    short = _git("rev-parse", "--short=7", sha, cwd=root)
    try:
        described = _git("describe", "--tags", "--match", "v[0-9]*", "--long", sha, cwd=root)
        tag, count, _ = described.rsplit("-", 2)
        base = tag[1:]
    except subprocess.CalledProcessError:
        base, count = "0.0.0", _git("rev-list", "--count", sha, cwd=root)
    joiner = "." if "-" in base else "-"
    return f"{base}{joiner}dev.{count}+g{short}"


def meta(ref: str, sha: str = "HEAD", root: Path = ROOT) -> dict[str, str]:
    """The run's version, channel, pre-release flag and tag."""
    if ref.startswith("refs/tags/"):
        tag = ref.removeprefix("refs/tags/")
        if not TAG.match(tag):
            raise DistError(f"not a version tag: {tag}")
        version = tag[1:]
        have = manifest_version(root)
        if have != version:
            raise DistError(f"the tag {tag} and manifest.json's version {have} differ")
        channel = channel_of(version)
        return {
            "kind": "tag",
            "tag": tag,
            "version": version,
            "channel": channel,
            "prerelease": str(is_prerelease(version)).lower(),
        }
    if ref == "refs/heads/main":
        return {"kind": "devel", "tag": "", "version": devel_version(root, sha), "channel": DEVEL, "prerelease": "true"}
    raise DistError(f"no release from {ref}: a version tag or main")


def write_zip(tree: Path, out: Path) -> None:
    """The tree's files without .distro/, sorted, stored, dated 1980 and
    mode 644: the same tree gives the same bytes."""
    files = sorted(
        p.relative_to(tree).as_posix()
        for p in tree.rglob("*")
        if p.is_file() and p.relative_to(tree).parts[0] != DISTRO_DIR
    )
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as zf:
        for name in files:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            zf.writestr(info, (tree / name).read_bytes())


def build(version: str, source: str, out: Path, root: Path = ROOT) -> None:
    """The tree, its zip and SHA256SUMS."""
    if not VERSION.match(version):
        raise DistError(f"not a version: {version}")
    tree = out / "tree"
    if tree.exists():
        shutil.rmtree(tree)
    tree.mkdir(parents=True)
    names = _git("ls-files", "-z", "--", SOURCE.as_posix(), cwd=root).split("\0")
    for name in filter(None, names):
        target = tree / Path(name).relative_to(SOURCE)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, target)
    manifest = tree / "manifest.json"
    text, count = MANIFEST_VERSION.subn(lambda m: m[1] + version + m[3], manifest.read_text(), count=1)
    if count != 1:
        raise DistError("manifest.json has no version")
    manifest.write_text(text)
    shutil.copyfile(root / "LICENSE", tree / "LICENSE")
    distro = tree / DISTRO_DIR
    distro.mkdir()
    (distro / "VERSION").write_text(version + "\n")
    (distro / "SOURCE").write_text(source + "\n")
    write_zip(tree, out / ZIP_NAME)
    digest = hashlib.sha256((out / ZIP_NAME).read_bytes()).hexdigest()
    (out / "SHA256SUMS").write_text(f"{digest}  {ZIP_NAME}\n")


def commit(tree: Path, parent: str, key: Path, name: str, email: str, message: str, root: Path = ROOT) -> str:
    """A commit of the tree on top of the parent, signed with the SSH key."""
    with tempfile.TemporaryDirectory() as tmp:
        env = {
            **os.environ,
            "GIT_INDEX_FILE": str(Path(tmp) / "index"),
            "GIT_AUTHOR_NAME": name,
            "GIT_AUTHOR_EMAIL": email,
            "GIT_COMMITTER_NAME": name,
            "GIT_COMMITTER_EMAIL": email,
        }
        git_dir = _git("rev-parse", "--absolute-git-dir", cwd=root)
        work = ("--git-dir", git_dir, "--work-tree", str(tree.resolve()))
        _git(*work, "add", "--all", "--force", ".", cwd=tree, env=env)
        tree_id = _git("write-tree", cwd=root, env=env)
        args = ["-c", "gpg.format=ssh", "-c", f"user.signingkey={key}", "commit-tree", "-S", tree_id, "-m", message]
        if parent:
            args += ["-p", parent]
        return _git(*args, cwd=root, env=env)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("meta")
    p.add_argument("--ref", required=True)
    p.add_argument("--sha", default="HEAD")
    p = sub.add_parser("build")
    p.add_argument("--version", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("zip")
    p.add_argument("tree", type=Path)
    p.add_argument("zip", type=Path)
    p = sub.add_parser("targets")
    p.add_argument("--version", required=True)
    p.add_argument("--channel", required=True, choices=(*CHANNELS, DEVEL))
    p.add_argument("--held", action="append", default=[], metavar="CHANNEL=VERSION")
    p = sub.add_parser("commit")
    p.add_argument("--tree", type=Path, required=True)
    p.add_argument("--parent", default="")
    p.add_argument("--key", type=Path, required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--email", required=True)
    p.add_argument("--message", required=True)
    args = parser.parse_args(argv)
    try:
        if args.cmd == "meta":
            for key, value in meta(args.ref, args.sha).items():
                print(f"{key}={value}")
        elif args.cmd == "build":
            build(args.version, args.source, args.out)
        elif args.cmd == "zip":
            write_zip(args.tree, args.zip)
        elif args.cmd == "targets":
            held = dict(item.split("=", 1) for item in args.held)
            print(" ".join(targets(args.version, args.channel, {k: v or None for k, v in held.items()})))
        elif args.cmd == "commit":
            print(commit(args.tree, args.parent, args.key, args.name, args.email, args.message))
    except (DistError, subprocess.CalledProcessError) as err:
        detail = getattr(err, "stderr", "") or ""
        print(f"dist.py: {err}{': ' + detail.strip() if detail else ''}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
