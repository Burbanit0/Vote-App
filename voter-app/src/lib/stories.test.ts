import { describe, it, expect } from 'vitest';
import { STORIES, storyById, type StoryStep } from './stories';
import { sampleVoters, fieldWinnerName, type NamedPt, type Dims } from './playgroundVoting';
import { composeElectorate } from './playgroundElectorate';
import type { PlaygroundState } from '../stores/useElectionStore';
import pgEn from '../i18n/locales/playground.en';
import pgFr from '../i18n/locales/playground.fr';

// Resolve the electorate + candidates as they stand *at* a given step, by folding
// the story's step patches up to and including it (steps patch only what changes).
// Mirrors PlaygroundController: simple ideology → sampleVoters; composed mixture →
// composeElectorate. This is the harness AND the guarantee that every beat's
// claimed winner survives a coordinate/seed drift.
function stateAt(storyId: string, stepId: string) {
  const story = storyById(storyId)!;
  let candidates: NamedPt[] = [];
  let num_voters = 300;
  let seed = 42;
  let ideology = 'random';
  let dims: Dims = 2;
  let valence = false;
  let rule = 'plurality';
  let electorate: PlaygroundState['electorate'] | null = null;
  for (const s of story.steps) {
    if (s.config?.candidates) candidates = s.config.candidates as NamedPt[];
    if (s.config?.num_voters != null) num_voters = s.config.num_voters;
    if (s.config?.seed != null) seed = s.config.seed;
    if (s.config?.ideology != null) ideology = s.config.ideology;
    if (s.playground?.space) {
      dims = s.playground.space.dims;
      valence = s.playground.space.valenceEnabled;
    }
    if (s.playground?.electorate) electorate = s.playground.electorate;
    if (s.rule) rule = s.rule;
    if (s.id === stepId) break;
  }
  const voters =
    electorate?.mode === 'composed'
      ? composeElectorate(
          electorate.communities,
          electorate.correlation,
          num_voters,
          seed,
          dims,
          electorate.noise
        ).voters
      : sampleVoters(num_voters, seed, ideology, dims);
  const cands: NamedPt[] = candidates.map((c) => ({
    ...c,
    y: dims >= 2 ? c.y : 0,
    z: dims >= 3 ? (c.z ?? 0) : 0,
    valence: valence ? (c.valence ?? 0) : 0,
  }));
  return { voters, cands, rule };
}

const winnerAt = (storyId: string, stepId: string): string | null => {
  const { voters, cands, rule } = stateAt(storyId, stepId);
  return fieldWinnerName(voters, cands, rule as never);
};

// Winner under an arbitrary rule at a step (candidates fixed at that step).
const winnerWithRule = (storyId: string, stepId: string, rule: string): string | null => {
  const { voters, cands } = stateAt(storyId, stepId);
  return fieldWinnerName(voters, cands, rule as never);
};

describe('stories — registry integrity', () => {
  it('every step beatKey and every title/tagline exists in FR and EN', () => {
    const keys: string[] = [];
    for (const st of STORIES) {
      keys.push(st.titleKey, st.taglineKey);
      for (const step of st.steps) keys.push(step.beatKey);
    }
    const resolve = (bundle: Record<string, unknown>, dotted: string): unknown =>
      dotted.split('.').reduce<unknown>((o, k) => (o as Record<string, unknown>)?.[k], bundle);
    for (const k of keys) {
      expect(resolve(pgFr, k), `FR missing ${k}`).toBeTypeOf('string');
      expect(resolve(pgEn, k), `EN missing ${k}`).toBeTypeOf('string');
    }
  });

  it('story ids are unique and steps are non-empty', () => {
    const ids = STORIES.map((s) => s.id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const s of STORIES) expect(s.steps.length).toBeGreaterThan(0);
  });

  it('the first step of every story sets mode, rule, a moment and a space', () => {
    for (const s of STORIES) {
      const first: StoryStep = s.steps[0];
      expect(first.mode, s.id).toBeTruthy();
      expect(first.rule, s.id).toBeTruthy();
      expect(first.moment, s.id).toBeTruthy();
      expect(first.playground?.space, s.id).toBeTruthy();
    }
  });
});

describe('stories — load-bearing outcomes hold on the seeded electorate', () => {
  it('spoiler: 2-way plurality elects Gore; the entrant flips it to Bush; IRV & Condorcet restore Gore', () => {
    expect(winnerAt('spoiler', 'duel')).toBe('Gore');
    expect(winnerAt('spoiler', 'enter')).toBe('Bush'); // Nader spoils
    expect(winnerAt('spoiler', 'irv')).toBe('Gore'); // spoiler neutralised
    expect(winnerAt('spoiler', 'condorcet')).toBe('Gore');
  });

  it('squeeze: the centrist is the Condorcet winner but IRV eliminates them first', () => {
    expect(winnerAt('squeeze', 'condorcet')).toBe('Centre');
    expect(winnerAt('squeeze', 'irv')).not.toBe('Centre');
  });

  it('paradox: same electorate, three different winners under plurality / IRV / approval', () => {
    expect(winnerAt('paradox', 'plurality')).toBe('Alice');
    expect(winnerAt('paradox', 'irv')).toBe('Carol');
    expect(winnerAt('paradox', 'approval')).toBe('Bob');
    // three distinct crowns from one electorate — the paradox made concrete
    const winners = new Set([
      winnerAt('paradox', 'plurality'),
      winnerAt('paradox', 'irv'),
      winnerAt('paradox', 'approval'),
    ]);
    expect(winners.size).toBe(3);
  });

  it('utile: plurality is spoiler-prone here (differs from a Condorcet-consistent rule)', () => {
    expect(winnerWithRule('utile', 'sincere', 'plurality')).not.toBe(
      winnerWithRule('utile', 'sincere', 'condorcet')
    );
  });

  it('valence: position elects the incumbent; quality (valence on) elects the reformer', () => {
    expect(winnerAt('valence', 'position')).toBe('Sortant');
    expect(winnerAt('valence', 'quality')).toBe('Réformateur');
  });

  it('five: the same electorate yields at least three different winners across rules', () => {
    const rules = ['plurality', 'irv', 'borda', 'condorcet', 'approval'];
    const winners = new Set(rules.map((r) => winnerWithRule('five', 'plurality', r)));
    expect(winners.size).toBeGreaterThanOrEqual(3);
  });
});
