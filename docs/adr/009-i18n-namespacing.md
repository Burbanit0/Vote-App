# ADR 009 — i18next with lazy-loaded language bundles

**Status:** Accepted (Phase 6, 2026-06)

## Context

The app ships FR + EN. Both translation bundles were eagerly imported, so every user
downloaded both languages even though only one is active at a time.

## Decision

Keep i18next as the i18n layer, but **code-split the language bundles** and lazy-load
the inactive one. French is the default; English loads on demand via `loadLanguage`.

## Consequences

- Smaller initial payload — the second language is fetched only if selected.
- Tests run under jsdom where `navigator.language` is `en-US`, so the suite resolves
  English: setup awaits `i18nReady` then `loadLanguage('en')` so strings are present.
- Components query by role/text, and tests assert English copy — keep that contract
  when adding translated UI.
