import { describe, it, expect } from 'vitest';
import { CURIOSITY_QUESTIONS } from './curiosityQuestions';
import { STORIES } from './stories';
import pgFr from '../i18n/locales/playground.fr';
import pgEn from '../i18n/locales/playground.en';

// Integrity gate: every curiosity question must route to a real story and have
// its text in BOTH locales — a dead entry would strand a curious newcomer.

const STORY_IDS = new Set(STORIES.map((s) => s.id));

const q = (bundle: Record<string, unknown>, id: string): unknown =>
  ((bundle.curiosity as { q?: Record<string, unknown> })?.q ?? {})[id];

describe('curiosity questions', () => {
  it('offers a handful of questions with unique ids', () => {
    expect(CURIOSITY_QUESTIONS.length).toBeGreaterThanOrEqual(5);
    expect(new Set(CURIOSITY_QUESTIONS.map((c) => c.id)).size).toBe(CURIOSITY_QUESTIONS.length);
  });

  it('every question routes to a real story', () => {
    for (const c of CURIOSITY_QUESTIONS)
      expect(STORY_IDS.has(c.story), `${c.id} → ${c.story}`).toBe(true);
  });

  it('every question has text in FR and EN', () => {
    for (const c of CURIOSITY_QUESTIONS) {
      expect(q(pgFr, c.id), `FR curiosity.q.${c.id}`).toBeTypeOf('string');
      expect(q(pgEn, c.id), `EN curiosity.q.${c.id}`).toBeTypeOf('string');
    }
  });
});
