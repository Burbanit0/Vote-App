import { describe, it, expect } from 'vitest';
import { GLOSSARY, seeInActionHref, type SeeInAction } from './glossary';
import { STORIES } from './stories';
import { ALL_EXPERIMENTS } from '../components/lab/labCatalog';

// Integrity gate: a "voir en action" link that points nowhere is worse than no
// link. Every ref is validated against the REAL story / lab-experiment ids, so
// the glossary can't quietly drift out of sync with the demos it promises.

const STORY_IDS = new Set(STORIES.map((s) => s.id));
const LAB_IDS = new Set(ALL_EXPERIMENTS.map((e) => e.id));
const ROUTES = new Set(['/', '/decouvrir', '/a-vous-de-jouer', '/playground', '/laboratoire']);

const refValid = (s: SeeInAction): boolean => {
  switch (s.kind) {
    case 'story':
      return STORY_IDS.has(s.ref);
    case 'lab':
      return LAB_IDS.has(s.ref);
    case 'route':
      return ROUTES.has(s.ref);
  }
};

describe('glossary integrity', () => {
  it('ships a substantial set of terms', () => {
    expect(Object.keys(GLOSSARY).length).toBeGreaterThanOrEqual(20);
  });

  it('every entry has non-empty fr + en copy', () => {
    for (const [id, e] of Object.entries(GLOSSARY)) {
      for (const loc of [e.fr, e.en]) {
        expect(loc.term, id).toBeTruthy();
        expect(loc.short, id).toBeTruthy();
        expect(loc.plain, id).toBeTruthy();
      }
    }
  });

  it('every "voir en action" link points at a real story / lab exp / route', () => {
    for (const [id, e] of Object.entries(GLOSSARY)) {
      if (e.seeInAction)
        expect(refValid(e.seeInAction), `${id} → ${e.seeInAction.kind}:${e.seeInAction.ref}`).toBe(
          true
        );
    }
  });

  it('builds the right hrefs', () => {
    expect(seeInActionHref({ kind: 'story', ref: 'spoiler' })).toBe('/playground?story=spoiler');
    expect(seeInActionHref({ kind: 'lab', ref: 'res-real-election' })).toBe(
      '/laboratoire?exp=res-real-election'
    );
    expect(seeInActionHref({ kind: 'route', ref: '/a-vous-de-jouer' })).toBe('/a-vous-de-jouer');
  });
});
