# Vote Lab — Manual Test Protocol

A full walkthrough to exercise the app after the Phase 6–7 refactor (Bootstrap →
Tailwind/shadcn, react-bootstrap removed, secondary-pages cleanup). Work top to
bottom; for each case mark **PASS / FAIL** and jot anything odd in the notes line.

> **Why this matters now:** the automated suite checks behaviour/roles/text, **not
> pixels**. The biggest risk from the migration is **visual / layout / dark-mode**
> regressions and interactive primitives (modals, dropdowns, accordions, tabs,
> forms). Look critically at spacing, alignment, borders, colours, and contrast.

---

## 0. Setup — how to run

**Option A — Docker (closest to prod, recommended):**
```bash
docker-compose up --build
# Frontend  → http://localhost:3000   (or whatever the compose maps)
# Backend   → http://localhost:4434/api/v2/health  (expect {"status":"ok"})
# API docs  → http://localhost:4434/api/v2/docs
```

**Option B — Local dev (two terminals):**
```bash
# Terminal 1 — backend
cd flask_voter_app
uvicorn api.main:app --reload --port 4434

# Terminal 2 — frontend
cd voter-app
npm start            # → http://localhost:3000
```

**Before you start:** open the browser **DevTools Console + Network** tabs and keep
them visible the whole session. **Any red console error or failed network request is
a bug** — note the case you were on when it appeared.

---

## 1. Coverage matrix

Do a **full pass once** in your main browser, then **spot-check** the starred (★)
cases in the other dimensions:

| Dimension | Values to try |
|---|---|
| Browser | Chrome/Edge (primary), Firefox, Safari |
| Viewport | Desktop ≥1200px · Tablet ~768px · **Mobile ~375px** (DevTools device mode) |
| Theme | **Light + Dark** (toggle in the user/settings menu) |
| Language | **FR + EN** (toggle in the user/settings menu) |

---

## 2. Bug report template

For each bug, copy this block into your report:

```
BUG #
- Case ID:            (e.g. E-04)
- Where:              URL + which tab/panel/button
- Environment:        browser / viewport / theme / language
- Steps to reproduce: 1) … 2) … 3) …
- Expected:
- Actual:
- Console errors:     (paste any red errors)
- Screenshot:         (attach if visual)
- Severity:           blocker / major / minor / cosmetic
```

---

## 3. Test cases

Legend: `[ ]` = not run, write `PASS` / `FAIL` after running.

### A — Global shell & Navbar

- **A-01** `[ ]` Load `/`. Page renders, no console errors, Navbar visible with brand
  "🗳️ Vote Lab" + "Bêta" badge. _Notes:_
- **A-02** `[ ]` Navbar "🔬 Election Lab" link → `/election-lab` loads. _Notes:_
- **A-03** `[ ]` **Learn** dropdown opens, lists Quiz + International Regimes + Guided
  Tour; clicking an item navigates and closes the menu; clicking outside closes it. _Notes:_
- **A-04** `[ ]` **Explore** dropdown opens, lists What-If, Quadratic Funding, Tech
  Democracy, Theory, Gallery, API Docs; each navigates. _Notes:_
- **A-05 ★** `[ ]` **Gallery** link (`/galerie`) loads the Scenario Gallery page
  _(route wired in `feat/galerie-route-and-404`)_. _Notes:_
- **A-06** `[ ]` "?" tour button (round) is visible and clickable. _Notes:_
- **A-07 ★** `[ ]` **Mobile (375px):** hamburger ☰ appears; tapping it expands the nav;
  links work; tapping a link collapses it again. _Notes:_
- **A-08** `[ ]` Brand link returns to `/` from any page. _Notes:_

### B — Theme, language & settings (user/settings dropdown, top-right)

- **B-01** `[ ]` Open the ⚙/👤 settings dropdown — it opens and lists Preferences. _Notes:_
- **B-02 ★** `[ ]` Toggle **Dark mode**: whole app switches to dark; **no white-on-white
  or black-on-black** anywhere; cards/tables/inputs/badges all readable. _Notes:_
- **B-03** `[ ]` Reload after enabling dark mode → it persists. _Notes:_
- **B-04 ★** `[ ]` Toggle **language FR↔EN**: visible strings switch; no raw keys like
  `nav.quiz` showing; persists on reload. _Notes:_
- **B-05** `[ ]` Toggle **Expert mode** — extra controls/info appear where expected. _Notes:_
- **B-06** `[ ]` Toggle **Teacher mode** → password modal opens; first time asks to
  create a password (min 4, confirm must match); the modal's **× close button** works;
  submitting a valid password activates teacher mode. _Notes:_

### C — Authentication

- **C-01** `[ ]` `/register`: form renders; submitting with a weak/mismatched password
  shows an inline error (not a crash). _Notes:_
- **C-02** `[ ]` Register a new account → redirected/logged in; username shows in the
  settings menu. _Notes:_
- **C-03** `[ ]` Logout (settings menu) → returns to logged-out state. _Notes:_
- **C-04** `[ ]` `/login` with the account → success; with wrong password → clear error. _Notes:_
- **C-05** `[ ]` OAuth buttons (Google / GitHub) on `/login` are present and styled
  (full flow needs configured keys — at minimum they should not be broken). _Notes:_
- **C-06** `[ ]` While **logged out**, visit `/profile` and `/simulation` → redirected
  to login (protected). While **logged in**, both load. _Notes:_

### D — Home page

- **D-01** `[ ]` Hero renders; the **Quick Compare** widget shows two method selectors. _Notes:_
- **D-02** `[ ]` Change method A and method B in the widget → result updates, winner
  badge(s) shown. _Notes:_
- **D-03 ★** `[ ]` Layout is clean at desktop, tablet, and mobile widths. _Notes:_

### E — Election Lab (`/election-lab`) — the core hub

- **E-01** `[ ]` Page loads with a parameter panel + a central map area + a row/menu
  of tabs. _Notes:_
- **E-02** `[ ]` **Parameter panel:** change num_voters (range/slider), seed, ideology;
  toggle campaign / blank vote / information model → the results update accordingly. _Notes:_
- **E-03** `[ ]` **Central map:** toggle the layers (points / heatmap / Voronoi /
  median voter) → each renders without error. _Notes:_
- **E-04** `[ ]` **Drag a candidate** on the 2D map (mouse) → it moves and results
  recompute. _Notes:_
- **E-05 ★** `[ ]` Drag a candidate on **mobile (touch)** → works. _Notes:_
- **E-06** `[ ]` **Tabs — desktop:** click through every tab; each renders its panel
  with no console error and no blank panel. Pay attention to the groups **See /
  Perturb / Variant**. _Notes (list any broken tab):_
- **E-07** `[ ]` Tabs that contain **tables** (e.g. Coalition, Condorcet, Manipulability,
  Score) render readable, aligned tables with borders. _Notes:_
- **E-08** `[ ]` Tabs with **charts** (Monte Carlo, Jury, Polarization, etc.) render the
  charts; legends/axes look right. _Notes:_
- **E-09** `[ ]` **Monte Carlo** tab: run a streaming simulation → the live convergence
  chart animates and completes (WebSocket). _Notes:_
- **E-10 ★** `[ ]` **NEW tab "Party Dynamics"** (Variant group): renders the Duverger
  simulator; controls work. _Notes:_
- **E-11 ★** `[ ]` **NEW tab "Sortition / Tirage au sort"** (Variant group): renders;
  comparison (elected / pure / stratified) works. _Notes:_
- **E-12 ★** `[ ]` **Deep link:** open `/election-lab?tab=sortition` directly → the
  Sortition tab is pre-selected. _Notes:_
- **E-13 ★** `[ ]` **Mobile tab nav:** at 375px the tabs become a dropdown + ‹ › arrows;
  selecting/stepping changes the panel; horizontal **swipe** changes tabs. _Notes:_
- **E-14** `[ ]` Pin/unpin a perturbation (if present) and verify it persists on reload. _Notes:_

### F — Simulation Compare (`/simulation/compare`)

- **F-01** `[ ]` Page loads with its tab set (14 tabs). _Notes:_
- **F-02** `[ ]` Click through each tab; charts/tables/metrics render. _Notes:_
- **F-03** `[ ]` Any dropdown / overlay-tooltip in this page opens and closes cleanly. _Notes:_

### G — Scenario Builder (`/scenario-builder`)

- **G-01** `[ ]` Page loads; candidate editor + electorate config render. _Notes:_
- **G-02** `[ ]` Add / edit / remove a candidate; change electorate sliders → preview
  updates. _Notes:_
- **G-03** `[ ]` Any save/export modal opens, is styled, and closes via × and backdrop. _Notes:_

### H — Standalone pages (Navbar)

For each: page loads, no console errors, layout OK light+dark, interactive bits work.

- **H-01** `[ ]` `/quiz` — questions render; answering advances; score/result shows. _Notes:_
- **H-02** `[ ]` `/what-if` — interactive controls work; charts render. _Notes:_
- **H-03** `[ ]` `/regimes-internationaux` — content + any selectors render. _Notes:_
- **H-04** `[ ]` `/quadratic-funding` — simulator controls + viz render. _Notes:_
- **H-05** `[ ]` `/tech-democracy` — content renders. _Notes:_
- **H-06** `[ ]` `/theory` — content renders. _Notes:_
- **H-07** `[ ]` `/api-docs` — API documentation renders. _Notes:_
- **H-08** `[ ]` `/teacher/presentation` — slides/presentation mode renders (enable
  Teacher mode first if required). _Notes:_

### I — Gallery

- **I-01 ★** `[ ]` Navigate to the gallery from the Navbar **and** by typing `/galerie`.
  The Scenario Gallery page loads in both cases. _Notes:_
- **I-02** `[ ]` If it loads: scenarios list renders; opening one works; the share modal
  (if reachable) opens/closes. _Notes:_

### J — Absorbed routes (redirects)

- **J-01** `[ ]` Type `/sortition` → should **redirect** to the Lab's Sortition tab. _Notes:_
- **J-02** `[ ]` Type `/party-dynamics` → should **redirect** to the Lab's Party
  Dynamics tab. _Notes:_

### K — Removed / unknown routes (should show the 404 page, NOT a blank screen)

- **K-01** `[ ]` Type `/campaign` → clean **404 page** ("Page introuvable" + Home /
  Election Lab buttons). _Notes:_
- **K-02** `[ ]` Type `/blank-contagion` → 404 page. _Notes:_
- **K-03** `[ ]` Type `/constitutional-crisis` → 404 page. _Notes:_
- **K-04** `[ ]` Type any garbage path (e.g. `/zzz`) → 404 page; the Home and Election
  Lab buttons on it both navigate correctly. _Notes:_

### L — UI primitives stress (migration-sensitive)

- **L-01** `[ ]` **Modals/dialogs:** every modal opens centered, has a working ×,
  closes on backdrop click and Esc, and doesn't leave the page scroll-locked after close. _Notes:_
- **L-02** `[ ]` **Dropdowns:** open on click, close on outside-click and on item-select;
  menu isn't clipped/hidden behind other content. _Notes:_
- **L-03** `[ ]` **Accordions:** headers expand/collapse; chevron rotates; only intended
  panel(s) open. _Notes:_
- **L-04** `[ ]` **Tabs:** active tab is visually distinct; switching is instant. _Notes:_
- **L-05** `[ ]` **Forms:** range sliders drag smoothly; selects open and select; number
  inputs accept typing; checkboxes/switches toggle. _Notes:_
- **L-06** `[ ]` **Toasts:** any success/error toast appears, is readable, and
  auto-dismisses or can be closed. _Notes:_
- **L-07** `[ ]` **Badges / alerts:** colour-coded states (success green / danger red /
  warning amber / info) look correct in **both** themes. _Notes:_
- **L-08** `[ ]` **Tooltips / overlays:** hovering an info "?" shows a tooltip that is
  readable and positioned sensibly. _Notes:_

### M — Cross-cutting

- **M-01 ★** `[ ]` **Dark mode** across at least: Lab, a table tab, a chart tab, a modal,
  the Navbar dropdowns, a form — all readable. _Notes:_
- **M-02** `[ ]` Resize the window slowly from wide → narrow on the Lab and Home; layout
  reflows without overlap or horizontal scrollbars. _Notes:_
- **M-03** `[ ]` **Offline / PWA:** with the app loaded, go offline (DevTools → Network →
  Offline) and reload → the offline banner / cached shell appears (doesn't hard-crash). _Notes:_
- **M-04** `[ ]` Full session review: scroll back through the Console — list every red
  error / warning you saw and which case triggered it. _Notes:_

---

## 4. Quick reference — what changed (so you know where to look hardest)

- **All UI re-skinned** Bootstrap → Tailwind: every screen could have spacing/colour
  drift. Dark mode is the highest-risk area.
- **Primitives are hand-written:** modal, tabs, accordion, dropdown, toast, pagination,
  navbar, tooltip, grid, form controls — exercise each (Section L).
- **Pages moved/removed:** Sortition + Party Dynamics are now **Lab tabs** with
  redirects (J); Campaign, Blank-Contagion, Constitutional-Crisis were **removed** (K).
- **Fixed:** the `/galerie` route is now wired (A-05/I-01), and unknown/removed paths
  show a 404 page instead of a blank screen (K).

---

When done, send me the filled-in FAIL items + any bug blocks from Section 2. Group by
severity if you can. I'll triage and fix.
