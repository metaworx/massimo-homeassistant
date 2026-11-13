# NOTE Integration v1.5: how Block 7 went

The `PLAN++` run of 2026-11-13, Block 7 (the card), and where it went
differently from v1.5.

## Where the work differs from the plan

1. **`massimo.get_program` names the device the programme was read from**
   (`source`, its name): the card shows it as Massimo's page does
   ("Programme as stored on …"). A field added to Block 5's answer.
2. **The check by hand ran in two frames of 1100 and 390 px** on one page,
   the browser window being maximised at 2560 px and not resizable from the
   tool; Home Assistant lays out each frame by its own width.
3. **The scratch Home Assistant** needed its components' requirements
   installed (`pyspeex-noise` among them) before the frontend loaded, and
   Lovelace in storage mode for the card editor; neither concerns the
   integration.

## The check by hand

On Home Assistant 2026.10.4 with `home-assistant-frontend` 20260930.5,
against Massimo's `main` and the fake Cube's fixture `rooms`, dark theme,
English:

- the card renders Massimo's editor: days, "Only Monday", the day bar,
  the switch points, the copy section, the resets and Send;
- an edit marks the days it changes, Send writes them ("… : ok");
- a change made in Massimo while nothing was edited is loaded by itself;
- a change made in Massimo while the card held an edit: Send is refused,
  the edit kept, "Load the current programme" offered and working;
- at 390 px, the phone layout, everything fits without scrolling sideways;
- the card picker lists "Massimo week programme"; its editor offers the
  Massimo rooms only, and a change of room reloads the preview.

Not checked by hand: the light theme, and a language other than English.
