# NOTE SetupPolish v1.0: title display name

A decision on D7, made 2026-11-16 after the plan's run was merged.

- **Whose key** a title names, and the *Signed in as* sensor's `user`
  attribute, is the key's user by its `display_name` from `GET
  /api/v1/me`, its login `name` only where it has none.
- **Why:** since Massimo's migration 0024 an integration's users are named
  `<integration uuid>:<subject>`, a name that says nothing to a person;
  Massimo's session on Home Assistant (AP StoreRaise v1.2, Block 4) asked
  for it. `display_name` is in `/me` on Massimo's `main` already, so no
  newer Massimo is required.
- **The owner's word:** D1-A with `EXEC`, title and attribute alike.
