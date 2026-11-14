"""tools/dist.py: the channels and versions of a release, the zip's bytes,
and the signed commit of a distro branch."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from awesomeversion import AwesomeVersion, AwesomeVersionStrategy

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import dist  # noqa: E402

HA_STRATEGIES = [
    AwesomeVersionStrategy.CALVER,
    AwesomeVersionStrategy.SEMVER,
    AwesomeVersionStrategy.SIMPLEVER,
    AwesomeVersionStrategy.BUILDVER,
    AwesomeVersionStrategy.PEP440,
]


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false",
         "-c", "tag.gpgsign=false", *args],
        cwd=cwd, check=True, capture_output=True, text=True,
    ).stdout.strip()  # fmt: skip


@pytest.mark.parametrize(
    ("version", "channel", "prerelease"),
    [
        ("0.1.0", "beta", True),
        ("0.1.0-alpha.1", "alpha", True),
        ("0.9.3-beta.2", "beta", True),
        ("1.0.0", "stable", False),
        ("1.2.0-beta.1", "beta", True),
        ("1.2.0-rc.1", "beta", True),
        ("2.0.0-alpha.3", "alpha", True),
    ],
)
def test_channel_by_version(version: str, channel: str, prerelease: bool) -> None:
    """Below 1.0.0 every version is a pre-release, beta unless it carries
    alpha; from 1.0.0 a version without a pre-release part is stable."""
    assert dist.channel_of(version) == channel
    assert dist.is_prerelease(version) is prerelease


def test_order_of_versions() -> None:
    """SemVer's precedence, the build part ignored."""
    ordered = [
        "0.1.0-alpha.1",
        "0.1.0-alpha.2",
        "0.1.0-alpha.10",
        "0.1.0-beta.1",
        "0.1.0",
        "0.2.0-dev.3+gabc1234",
        "0.2.0",
        "1.0.0",
    ]
    for earlier, later in zip(ordered, ordered[1:], strict=False):
        assert dist.newer(later, earlier), (later, earlier)
        assert not dist.newer(earlier, later), (earlier, later)


def test_targets() -> None:
    """A release goes to its channel, and to each less stable one that holds
    an older version or none; devel takes main alone."""
    assert dist.targets("0.1.0", "beta", {}) == ["beta", "alpha"]
    assert dist.targets("0.2.0-alpha.1", "alpha", {"beta": "0.1.0"}) == ["alpha"]
    held = {"stable": "1.0.0", "beta": "1.1.0-beta.1", "alpha": "1.0.0"}
    assert dist.targets("1.0.1", "stable", held) == ["stable", "alpha"]
    assert dist.targets("0.0.0-dev.4+gabc1234", "devel", held) == ["devel"]


def test_versions_home_assistant_takes(tmp_path: Path) -> None:
    """The versions of a tag and of main, before and after the first tag;
    Home Assistant's loader takes each."""
    repo = tmp_path / "repo"
    shutil.copytree(dist.ROOT / "custom_components", repo / "custom_components")
    _git(tmp_path, "init", "-q", "-b", "main", str(repo))
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "one")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "two")
    sha = _git(repo, "rev-parse", "--short=7", "HEAD")
    versions = [dist.meta("refs/heads/main", root=repo)["version"]]
    assert versions[0] == f"0.0.0-dev.2+g{sha}"
    _git(repo, "tag", "v0.1.0")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "three")
    versions.append(dist.devel_version(repo))
    assert versions[1].startswith("0.1.0-dev.1+g")
    _git(repo, "tag", "v0.2.0-alpha.1")
    versions.append(dist.devel_version(repo))
    assert versions[2].startswith("0.2.0-alpha.1.dev.0+g")
    manifest = repo / dist.MANIFEST
    data = json.loads(manifest.read_text())
    data["version"] = "0.2.0-alpha.1"
    manifest.write_text(json.dumps(data))
    tag = dist.meta("refs/tags/v0.2.0-alpha.1", root=repo)
    assert tag == {
        "kind": "tag",
        "tag": "v0.2.0-alpha.1",
        "version": "0.2.0-alpha.1",
        "channel": "alpha",
        "prerelease": "true",
    }
    versions.append(tag["version"])
    for version in versions:
        AwesomeVersion(version, ensure_strategy=HA_STRATEGIES)


def test_a_tag_must_match_the_manifest(tmp_path: Path) -> None:
    """A tag whose version manifest.json does not carry makes no release;
    neither does a branch other than main, or a tag that is no version."""
    (tmp_path / dist.MANIFEST).parent.mkdir(parents=True)
    (tmp_path / dist.MANIFEST).write_text('{"version": "0.1.0"}')
    with pytest.raises(dist.DistError, match="differ"):
        dist.meta("refs/tags/v0.2.0", root=tmp_path)
    with pytest.raises(dist.DistError, match="not a version tag"):
        dist.meta("refs/tags/release-1", root=tmp_path)
    with pytest.raises(dist.DistError, match="no release"):
        dist.meta("refs/heads/feature", root=tmp_path)


def test_the_zip_is_the_same_every_time(tmp_path: Path) -> None:
    """Two builds give the same bytes: the integration's files, the
    version in the manifest, the licence, and no .distro/."""
    for out in ("a", "b"):
        dist.build("0.1.0-dev.3+gabc1234", "abc1234", tmp_path / out)
    one, two = ((tmp_path / out / dist.ZIP_NAME).read_bytes() for out in ("a", "b"))
    assert one == two
    sums = (tmp_path / "a" / "SHA256SUMS").read_text()
    assert sums == f"{hashlib.sha256(one).hexdigest()}  massimo.zip\n"
    with zipfile.ZipFile(tmp_path / "a" / dist.ZIP_NAME) as zf:
        names = zf.namelist()
        assert json.loads(zf.read("manifest.json"))["version"] == "0.1.0-dev.3+gabc1234"
    assert "__init__.py" in names and "LICENSE" in names and "brand/icon.png" in names
    assert not [n for n in names if n.startswith(".distro") or "__pycache__" in n]
    tree = tmp_path / "a" / "tree"
    assert (tree / ".distro" / "VERSION").read_text() == "0.1.0-dev.3+gabc1234\n"
    dist.write_zip(tree, tmp_path / "again.zip")
    assert (tmp_path / "again.zip").read_bytes() == one


@pytest.mark.skipif(shutil.which("ssh-keygen") is None, reason="ssh-keygen is not installed")
def test_a_distro_commit_is_signed(tmp_path: Path) -> None:
    """A distro commit carries the tree on top of the branch, signed with
    the channel's key, which git checks against the allowed signers."""
    key = tmp_path / "key"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "test", "-f", str(key)], check=True)
    repo = tmp_path / "repo"
    _git(tmp_path, "init", "-q", str(repo))
    dist.build("0.1.0", "abc1234", tmp_path / "out")
    email = "rolling@ha.massimo.metaworx.ch"
    first = dist.commit(tmp_path / "out" / "tree", "", key, "Massimo for HA", email, "0.1.0", root=repo)
    second = dist.commit(tmp_path / "out" / "tree", first, key, "Massimo for HA", email, "again", root=repo)
    assert _git(repo, "rev-parse", f"{second}^") == first
    assert "manifest.json" in _git(repo, "ls-tree", "--name-only", second)
    assert ".distro" in _git(repo, "ls-tree", "--name-only", second)
    signers = tmp_path / "allowed_signers"
    signers.write_text(f'{email} namespaces="git,file" {(tmp_path / "key.pub").read_text()}')
    _git(repo, "-c", f"gpg.ssh.allowedSignersFile={signers}", "verify-commit", second)
    other = tmp_path / "other"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "test", "-f", str(other)], check=True)
    signers.write_text(f'{email} namespaces="git,file" {(tmp_path / "other.pub").read_text()}')
    with pytest.raises(subprocess.CalledProcessError):
        _git(repo, "-c", f"gpg.ssh.allowedSignersFile={signers}", "verify-commit", second)
