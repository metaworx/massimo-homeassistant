#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Builds the site, https://ha.massimo.metaworx.ch (CONTRIBUTING.md, "The
# site"), without a key and without state: the pages of site/ at the root,
# the README as readme.html, keys/ as /keys/, and per channel whose branch
# distro/<channel> exists, distro/<channel>.zip made again from the branch,
# with the signature the branch carries for it. A zip that does not match
# its signature, or a branch whose commit is not signed by its key, fails
# the build: nothing is deployed. site.yml runs it; it runs locally too.
# After Massimo's packaging/site/build.sh (D52-A).
set -euo pipefail

usage() {
	cat >&2 <<'EOF'
usage: build.sh --out <dir> [--remote <name>]
  --out <dir>      the site; it must not exist yet
  --remote <name>  where the distro/<channel> branches are (default origin)
Exit 0 built, 1 failed, 2 usage.
EOF
	exit 2
}

root=$(cd "$(dirname "$0")/.." && pwd)
out=""
remote=origin
while [ $# -gt 0 ]; do
	case "$1" in
	--out) out=${2:-}; shift 2 || usage ;;
	--remote) remote=${2:-}; shift 2 || usage ;;
	*) usage ;;
	esac
done
[ -n "$out" ] || usage
[ ! -e "$out" ] || { echo "build.sh: $out exists" >&2; exit 1; }

signers="$root/keys/allowed_signers"
mkdir -p "$out/keys" "$out/distro"
cp "$root"/site/{site.css,privacy.html} "$out/"
cp "$root"/keys/* "$out/keys/"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# The channels: a table of what each branch holds, for the home page.
rows=""
for channel in stable beta alpha devel; do
	ref="refs/remotes/$remote/distro/$channel"
	git -C "$root" rev-parse --verify --quiet "$ref" >/dev/null || continue
	case "$channel" in
	devel) principal=rolling@ha.massimo.metaworx.ch ;;
	*) principal=release@ha.massimo.metaworx.ch ;;
	esac
	git -C "$root" -c gpg.ssh.allowedSignersFile="$signers" verify-commit "$ref" 2>"$tmp/verify" ||
		{ cat "$tmp/verify" >&2; echo "build.sh: distro/$channel is not signed by a key of keys/allowed_signers" >&2; exit 1; }
	grep -qF "signature for $principal " "$tmp/verify" ||
		{ cat "$tmp/verify" >&2; echo "build.sh: distro/$channel is not signed by $principal" >&2; exit 1; }
	tree="$tmp/$channel"
	mkdir "$tree"
	git -C "$root" archive "$ref" | tar -x -C "$tree"
	python3 "$root/tools/dist.py" zip "$tree" "$out/distro/$channel.zip"
	cp "$tree/.distro/massimo.zip.sig" "$out/distro/$channel.zip.sig"
	ssh-keygen -Y verify -f "$signers" -I "$principal" -n file -s "$out/distro/$channel.zip.sig" \
		<"$out/distro/$channel.zip" >/dev/null ||
		{ echo "build.sh: distro/$channel.zip does not match its signature" >&2; exit 1; }
	version=$(cat "$tree/.distro/VERSION")
	source=$(cat "$tree/.distro/SOURCE")
	rows+="<tr><td><code>$channel</code></td><td>$version</td>"
	rows+="<td><a href=\"https://github.com/metaworx/massimo-homeassistant/commit/$source\">${source:0:7}</a></td>"
	rows+="<td><a href=\"/distro/$channel.zip\">$channel.zip</a> · <a href=\"/distro/$channel.zip.sig\">signature</a></td></tr>"$'\n'
done
if [ -n "$rows" ]; then
	channels="<table>"$'\n'"<tr><th>Channel</th><th>Version</th><th>From</th><th>Download</th></tr>"$'\n'"$rows</table>"
else
	channels="<p>No channel has a version yet.</p>"
fi
printf '%s' "$channels" >"$tmp/channels.html"

# The README as a page; its links to other files of the repository go to
# GitHub.
commit=$(git -C "$root" rev-parse --short=7 HEAD)
python3 "$root/GUIDELINES/shared/tools/md_html.py" --anchors github --source README.md \
	--url "=https://github.com/metaworx/massimo-homeassistant/blob/main/" "$root/README.md" >"$tmp/readme.html"

python3 - "$root/site" "$tmp" "$out" "$commit" <<'EOF'
import sys
from pathlib import Path

site, tmp, out = (Path(a) for a in sys.argv[1:4])
commit = sys.argv[4]
home = (site / "index.html").read_text().replace("{{CHANNELS}}", (tmp / "channels.html").read_text())
(out / "index.html").write_text(home)
page = (site / "doc.html.in").read_text()
for key, value in {
    "{{TITLE}}": "README",
    "{{SOURCE_NAME}}": "README.md",
    "{{COMMIT}}": commit,
    "{{SOURCE}}": "https://github.com/metaworx/massimo-homeassistant/blob/main/README.md",
    "{{BODY}}": (tmp / "readme.html").read_text(),
}.items():
    page = page.replace(key, value)
(out / "readme.html").write_text(page)
EOF
echo "build.sh: the site is in $out"
