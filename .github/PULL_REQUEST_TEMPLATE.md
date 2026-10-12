## Request

<!-- The original request, verbatim (a link to the issue, or a quote). Not a summary written afterwards. -->

## Description

<!-- What changed, and why -->

## Acceptance criteria

<!-- One checkable criterion per line, taken from the request. Tick only what the evidence below shows. -->

- [ ] C1 —
- [ ] C2 —

## Evidence

<!--
The commands run and their real output (the useful last lines), screenshots for UI.
The block `/verify` prints can be pasted as is.
-->

**Not verified:** <!-- required: what was not checked, and why; "nothing" only when true -->

## Type of change

- [ ] `feat` — new feature
- [ ] `fix` — bug fix
- [ ] `refactor` — no behaviour change
- [ ] `docs` — documentation only
- [ ] `ci` — CI/CD, pipeline
- [ ] `security` — security fix
- [ ] `perf` — performance

## Checklist

### Code
- [ ] Follows the existing style (no console.log, no unused imports, etc.)
- [ ] No secret or credential committed (see detect-secrets)
- [ ] Variable and function names are clear and in English

### Tests
- [ ] Existing tests pass (`npm test` / `pytest`)
- [ ] Tests were added for new behaviour (where applicable)
- [ ] Coverage does not drop

### Security
- [ ] `npm run audit:gate` (in `voter-app/`) passes
- [ ] User input is validated on the backend
- [ ] No vulnerable dependency added

### Frontend (if applicable)
- [ ] Checked in light and dark mode
- [ ] Checked in Expert and Beginner mode
- [ ] Checked with plain-language rule names on
- [ ] Checked on mobile (responsive tables)
- [ ] No regression on HomePage, PlaygroundPage, LaboratoirePage

### Backend (if applicable)
- [ ] New compute-heavy endpoints are rate limited (`check_v2_rate_limit` or equivalent)
- [ ] New routes are tested
- [ ] CORS respected (no `*` added)

## Screenshots (UI changes)

<!-- Before / after, where relevant -->

## Notes for the reviewer

<!-- Useful context: architectural decisions, trade-offs, points to look at -->
