# Analytics — Umami (self-hosted, anonymous, cookie-less)

Usage measurement for Vote Lab. **Umami** was chosen because it is cookie-less
and stores no visitor identifier: under the CNIL audience-measurement exemption
this needs **no consent banner** — a pedagogy app should not open on a cookie
wall. It runs beside the app in its own compose stack (the app itself stays
deliberately DB-free); tearing this directory down never touches the app.

## Why frontend events (and not server logs)

The whole voting engine runs client-side — changing the rule, playing a story,
opening a Lab fiche, scrubbing the campaign never hits the backend. Server logs
therefore see almost nothing. The app emits a small vocabulary of anonymous
events through `voter-app/src/lib/analytics.ts`:

| Event | Props | Answers |
|---|---|---|
| `story_started` / `story_completed` | `story` | Which histoires get played, and finished? |
| `rule_changed` | `rule` | Which voting methods do people explore? |
| `moment_changed` | `moment` | How far along the 5-moment journey do they go? |
| `mode_toggled` | `mode` | Dirigeant vs Assemblée interest |
| `preset_applied` | `preset` | Which starting scenarios attract clicks? |
| `lab_fiche_opened` | `fiche` | Which of the 57 Lab experiments are used? |
| `lab_compare_opened` | `fiche`, `vs` | Which pairs do people compare? |
| `real_election_selected` | `election` | Burlington vs Alaska interest |
| `campaign_scenario_selected` | `scenario` | Which campaign dynamics are run? |

Plus pageviews, tracked automatically (Umami hooks SPA navigations itself).

Props are ids and enum values only — never free text, never anything
user-identifying. `Do-Not-Track` is respected. Dev builds, tests and forks of
this repo send nothing (the tracker only loads when both `VITE_UMAMI_*` vars
are present in a **production** build).

## Setup

1. Start the stack (Docker required):

   ```bash
   cd analytics
   cp .env.example .env        # then fill both values (openssl rand -hex 32)
   docker compose up -d
   ```

2. Open `http://localhost:3100` (production: put it behind your reverse proxy
   on a subdomain, e.g. `analytics.votelab.app`). Log in with the default
   `admin` / `umami` and **change the password immediately**.

3. *Settings → Websites → Add website*, enter the app's domain, then copy the
   generated **Website ID**.

4. Build the frontend with the two variables set (CI secret or `.env.local`):

   ```bash
   VITE_UMAMI_SRC=https://analytics.votelab.app/script.js
   VITE_UMAMI_WEBSITE_ID=<the website id>
   npm run build
   ```

That's all — events appear in the Umami dashboard under the site's *Events*
tab, with a breakdown per prop.

## Verifying locally

`npm run build && npm run preview` with the vars pointing at the local stack
(`http://localhost:3100/script.js`), click around, watch the dashboard's
realtime view. Dev mode (`npm start`) intentionally sends nothing.
