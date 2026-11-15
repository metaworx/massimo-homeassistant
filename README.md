# Massimo for Home Assistant

A Home Assistant integration for [Massimo](https://github.com/metaworx/massimo),
the server that holds eQ-3 MAX!
Cubes: Massimo keeps the Cubes, their radio budget, pairing and week programmes,
and Home Assistant becomes one more client of its HTTP API,
beside Massimo's own web UI and apps.

> **Not released yet.**
> It sets up a Massimo server, follows its Cubes,
> shows their devices with their sensors and key locks,
> controls each room's heating, boost included, and edits its week programme,
> in a card or by actions.
> Until a release, Home Assistant's own MAX! integration can control the Cube through
> Massimo's LAN proxy,
> as Massimo's
> [docs/homeassistant.md](https://github.com/metaworx/massimo/blob/main/docs/homeassistant.md) describes.

## What it does so far

- **Setup** by address, or found by mDNS (`_massimo._tcp`),
  registered by a code that Massimo's owner approves, or with an API key.
  The server is known by its node id; an address found again on the
  network replaces one found before, never one you typed, except that a
  registered entry follows the address Massimo announces.
- **The server as a device**, the Cubes beneath it: Massimo's version, its
  address to visit, and diagnostic entities - *Connected*, *Last contact*
  (off by default) and *Signed in as* (registered, a person's key, or a
  server without users) - and diagnostics to download, without the key.
- **Users**: registered, each call names the Home Assistant user it is made
  for, and Massimo allows it what that user may do ("Users", below).
- **Live data**:
  it reads the server's Cubes and rooms once and then follows each Cube's event
  stream.
  After an interruption it resumes after the last event it read,
  where the server supports it (Massimo with event ids),
  and reads again what the server no longer holds.
- **Devices**: the Cube as a hub, and each thermostat, window contact and eco
  switch as a device of its own beneath it,
  in an area named as its room in Massimo
  (the area is only suggested, when the device first appears;
  the areas stay yours).
  Devices paired later appear without a restart,
  and devices removed in Massimo leave Home Assistant too.
- **Entities**:
  - each thermostat's measured temperature, and a radiator thermostat's valve;
  - each window contact's window;
  - every device's battery, and its link and transmit errors (diagnostic);
  - each thermostat's **key lock** as a switch: on locks its buttons,
    written through Massimo's queue, and shown once the thermostat reports it;
  - the Cube's connection, radio duty cycle, free memory slots,
    pending radiograms and queued commands (diagnostic).

  A device's entities are unavailable while its Cube is not connected,
  until it has reported, and while Massimo calls it stale
  (a thermostat silent for 24 hours).
- **Rooms**, from a Massimo with virtual wall thermostats
  (Massimo's feature `vwt`; an older one gets the devices alone, and a warning):
  each room with a thermostat is a device of its own, in its area,
  and stays the room's whatever thermostats come and go in it.
  - Its **`climate`** shows the room's temperature as Massimo computes it:
    its wall thermostat's, else the median of its radiator thermostats
    (the attribute `temperature_sources` says which).
    Modes: `auto` follows the week programme, `heat` holds a setpoint,
    `off` holds 4.5 °C, which the thermostats show as off.
    Presets: `eco` and `comfort` hold the room's eco and comfort
    temperatures, `away` shows vacation mode, `none` goes back to the week
    programme, and `boost` (from a Massimo with the feature `boost`) opens the
    valves for the thermostats' boost time, after which they go back to the
    mode they had.
    Every write goes through Massimo's queue to all thermostats of the room,
    and shows once they report it.
  - **Massimo: Set vacation** (`massimo.set_vacation`) holds a room at a
    temperature until an end, rounded up to the half hour,
    then goes back to its week programme.
  - **Room temperature from** (configuration): the median or the mean of the
    radiator thermostats, for a room without a wall thermostat.
- **Week programmes**, from a Massimo that tags them
  (Massimo's feature `program_etag`), as actions on a room's `climate`:
  - **Massimo: Get week programme** (`massimo.get_program`) answers the
    room's programme, its tag, whether a write to it is still on its way,
    and whether its thermostats agree;
  - **Massimo: Set week programme** (`massimo.set_program`) writes days of
    it, each 1 to 13 switch points such as `{"temp": 21, "until": "07:00"}`,
    the last until 24:00, and answers the new tag;
    given the tag it read, a write over a change made meanwhile
    (in Massimo's web UI, at a thermostat) is refused instead of
    overwriting it;
  - **Massimo: Copy week programme** (`massimo.copy_program`) copies a
    room's programme, or some of its days, to other rooms, or one day of a
    room onto its other days.

  The `climate`'s attributes `program_tag` and `program_changed` say which
  programme the room has and when the integration saw it change.
- **The card "Massimo week programme"** edits a room's week programme with
  Massimo's own editor, in Home Assistant's look: add it to a dashboard and
  choose the room. Nothing to install: the integration loads it.
  - It sends only the days you changed, with the tag it read the programme
    with; a programme changed meanwhile, in Massimo or at a thermostat,
    is not overwritten: the card keeps your edits and offers to load the
    current one.
  - It reads the programme again by itself when it changes elsewhere and
    you are not editing it.
  - The editor and its texts (English, German, French, Italian, Dutch,
    Polish) come from your Massimo server, under Massimo's own licence,
    AGPL-3.0: the integration passes them on to a browser signed in to
    Home Assistant, and carries none of them.
    A page holds one version of the editor: with two Massimo servers of
    different versions, the first one a card loads is used.
- **Re-authentication** when the key stops working, and **reconfiguration**:
  register again, or type another key.

## Setting up

1. Install it into Home Assistant's `custom_components/massimo` from the
   channel you choose, with git or as a signed zip, as
   <https://ha.massimo.metaworx.ch> shows:

   ```bash
   git clone -b distro/beta https://github.com/metaworx/massimo-homeassistant.git custom_components/massimo
   ```

   and restart Home Assistant.
   `distro/<channel>` is `stable`, `beta`, `alpha` or `devel`;
   every version below 1.0.0 is `beta`, or `alpha` where it carries
   `-alpha`, and `devel` is `main` once its tests have passed;
   until the first release, `devel` is the only one.
   (Through the Marketplace or HACS once released.)
2. Settings → Devices & services → Add integration → **Massimo**,
   or the server Home Assistant found on the network:
   the address at which a browser opens Massimo's web UI
   (filled in where Home Assistant found a server not set up yet),
   then one of
   - **Register**: first two names, the one Home Assistant goes by in
     Massimo's list of integrations (Home Assistant's own, by default) and
     this server's in Home Assistant ("Massimo" and its location or host);
     then Home Assistant asks Massimo to register it and shows a code.
     In Massimo, System settings → Integrations lists the request with its code;
     approve it there if the codes are the same, with the most it may do.
     Home Assistant collects its key and goes on by itself.
     A request waits ten minutes.
   - **Type an API key** of a Massimo user who may read, and this
     server's name in Home Assistant:
     the way to a Massimo without the feature `integration`,
     or one that takes no requests.
     A server without users needs none.

   The entry's title is the name, followed by whose key it signs in with
   where that is a person's, such as "Massimo Keller (key of anna)";
   a title you rename yourself stays.
   A server found on the network long ago is asked again when you open its
   card, so the choice offered is the one it allows now.

Home Assistant 2026.10 or newer.

## Users

Registered, Home Assistant is an integration of Massimo's,
and each call it makes for one of its users names that user
(Massimo's [docs/api-v1.md](https://github.com/metaworx/massimo/blob/main/docs/api-v1.md),
"Acting for an integration's users"):

- the user's id, name and level for the entity:
  `admin` for an administrator, otherwise `control` where the user may
  control the entity and `view` where only view;
- a call no user started, such as an automation's, as `system`;
- the reads and the event stream as the integration itself.

Massimo makes each user at its first call, lists them under the integration,
and lets you link one to a Massimo user; a call may do only what the
integration, the user it is linked to, and the level allow.
A refusal is said in Home Assistant with its reason.

Two repairs may appear under Settings → Repairs:

- **Register Home Assistant with Massimo**: the entry signs in with a key typed
  by hand to a Massimo that could register it.
  Reconfigure the entry and choose to register.
- **Accept this installation in Massimo**: Massimo accepted another
  installation of Home Assistant for this integration, as after a backup
  restored on another machine.
  Accept this one in Massimo, under System settings → Integrations;
  until then, the calls made for users and automations are refused.

## Development

The tests run against a real `massimo serve` and Massimo's fake Cube,
not against mocks.
[CONTRIBUTING.md](CONTRIBUTING.md) says how to set up, test, commit
and cut a release.

## Licence

Apache-2.0, as Home Assistant itself.
Massimo is AGPL-3.0; this integration talks to it over HTTP and is a work of its
own.
