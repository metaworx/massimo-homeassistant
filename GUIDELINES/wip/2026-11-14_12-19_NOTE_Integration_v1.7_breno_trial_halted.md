# NOTE Integration v1.7: breno trial halted

Block 10, the trial on breno, as far as it went on 2026-11-14,
and why the owner stopped it.

## Done

- `distro/devel`, 0.0.0-dev.43+gbf491e7 (the merge of the release fix),
  cloned as `pi` into `/srv/homeassistant/config/custom_components/massimo`;
  the folder made with `sudo install -d -o pi -g pi`, so that `pi` pulls
  without sudo.
  Its commit checked against `keys/allowed_signers`, kept in the clone's
  `.git/allowed_signers` and set as its `gpg.ssh.allowedSignersFile`:
  good signature for `rolling@ha.massimo.metaworx.ch`.
- `homeassistant` restarted: Home Assistant 2026.11.0 loads `massimo`
  without an error. No config entry was made.
  maxcube fails to connect, as since 2026-11-12; nothing else was touched.

## Why it stopped

Home Assistant's zeroconf found a Massimo on the LAN - not the Pi's,
which serves HTTP on `127.0.0.1:8099` alone, but one on the Windows side
of the owner's workstation, `192.168.178.101:8099` - and offered it.
The owner stopped the trial there: which Massimo, and which user,
Home Assistant signs in to is what Massimo's AP IntegrationUsers is
settling, with the sessions "HA Integration 1" and "HA Bridgehead".
The trial resumes once that is decided.

## Found on 2026.11 (D33-A)

Home Assistant 2026.11 warns that `climate.py`'s `RoomClimate` provides
`_attr_temperature_unit`, `current_temperature` and `target_temperature`,
which stop working in 2027.11: they are to be the `native_*` names.
The tests do not see it, the Home Assistant they pin giving no warning.
To be fixed before the first release (Block 11).

## Left in place

The clone on the Pi, loaded but unused, and the discovered flow in
Home Assistant's "Discovered" list, which the owner may ignore.
