# LogoSphere for Android — the rest of the web's features

Date: 2026-11-20 · Status: in implementation

The first version of the app (docs/plans/2026-11-18-android-client-design.md)
covered the everyday member loop and left the rest to the web: the Me tab
linked there. This pass closes that gap, so nothing on the site needs the
browser any more.

## What the web had and the app didn't

Found by comparing every API call the web client makes with the app's
(`frontend/src` against `android/core/.../LogoSphereApi.kt`).

| # | Feature (web source) | API |
|---|---|---|
| 1 | Edit your profile: name, surname, location, photo (`Settings.js`, `ProfilePage.js`) | `GET /api/user/profile`, `POST /api/updateuser` (multipart `profile_picture`) |
| 2 | Your Meaning Graph: write, edit and remove value cards; endorse on reflection; mark reviewed (`ProfilePage.js`, `ValueCardState.js`) | `POST/PATCH/DELETE /api/value_cards…`, `…/endorse`, `…/review` |
| 3 | Copy someone's value card onto your graph, or a group's you manage (`ValueCardChip.js`) | `POST /api/value_cards/clone` |
| 4 | Start a sphere, alliance or project (`EntityForm.js`) | `POST /api/{spheres,alliances,projects}` (multipart), then `PATCH` for the join policy |
| 5 | Manage a group: name, description, policies, a sphere's public/sandbox flags, banner (`EntityManagement.js`) | `PATCH /api/<kind>s/<id>`, `POST /api/spheres/<id>/governance`, `POST …/image` |
| 6 | Members: approve or decline requests, promote, demote, remove (`MembersList.js`) | `POST /api/<kind>s/<id>/members/<uid>/role` |
| 7 | A group's Meaning Graph: write, edit, remove, endorse, review (`EntityValueGraph.js`) | `/api/entity_value_cards/<id>…` |
| 8 | Governance: policies, delegating your vote, proposals, voting, counting early, withdrawing (`GovernancePanel.js`) | `/api/<kind>s/<id>/governance`, `…/proposals…`, `…/delegation` |
| 9 | Post an opening as a group you manage (`EntityPage.js` → `NewServiceForm.js`) | `POST /api/openings` with `acting_as_id` |
| 10 | Edit an opening (a new version once an exchange links to it); set its picture (`OpeningPage.js`) | `PATCH /api/openings/<id>`, `POST …/image` |
| 11 | Edit an exchange's title, description and banner; receipt photos, up to three (`ExchangePage.js`) | `POST /api/exchange/<id>/edit`, `…/receipt_photos` |
| 12 | Platform administration: overview, users, spheres, alliances, projects, openings (`AdminPage.js`) | `/api/admin/…` |
| 13 | About, How it works, Contribute, Donate, Privacy, Terms (`pages/*.js`) | — |

Left out on purpose: the public sphere page for signed-out visitors (the app
always has a member signed in) and the Settings page's "coming soon" card
(nothing there saves).

## How it fits the app

- **`:core`** gains the calls above, their response models (governance and
  admin in files of their own), a multipart `Upload`, and the rules screens
  ask: who may set roles (`Membership.canSetRoles`), each kind's role labels
  and actions (`Roles`), each kind's policies and how to word them
  (`Policies`). All unit-tested; the new responses decode from fixtures written
  from the Flask code.
- **`:app`** gains screens for the profile editor, the value-card editor (one
  form for a person's and a group's cards), a group's management (settings,
  meaning graph, members), new groups, governance (a tab on every group), the
  admin console and the information pages. Existing screens gain edit and
  picture actions.
- **Pictures** come from the system photo picker. Small files go up as they
  are; big ones are scaled to 2048 px on the phone (keeping EXIF rotation)
  before upload, and the server makes its own sizes as before. After an upload
  the app forgets its cached copy of that picture so the new one shows at once.
- **Destructive actions** ask first, as the rest of the app does: a dialog
  where the web uses a two-step button.

## Testing

`:core` unit tests (rules, decoding, request shapes against MockWebServer),
`assembleDebug`, then the debug build on the phone against production, signed
in as the phone's owner. Changes made while testing are undone afterwards, as
in the earlier passes.
