// storyClaims.ts — the facts the guided stories' copy states, as data (PLAN_BEYOND_CI W1.3).
//
// A beat that names a winner or prints a percentage makes a claim about the engine. Each
// one is listed here and checked by stories.test.ts against the story's own electorate,
// so an engine, seed or coordinate change that falsifies the copy fails a test instead
// of shipping. Change a beat's copy, change its claim here.
//
// Percentages are as the copy prints them, and the test checks that the beat's EN and FR
// text does print them (and names the winner), so the table and the copy cannot drift
// apart. The copy rounds (38.5% is printed 38%), so the engine may differ by half a point. Claims stories.test.ts already asserts elsewhere (most winners, the
// strict Condorcet winners) are not repeated. The parliament stories' seat figures come
// from the backend and are recorded in stories.ts's comments instead.

type At = { story: string; step: string };
export type StoryClaim =
  | (At & { kind: 'winner'; expected: string })
  | (At & { kind: 'firstPref'; candidate: string; pct: number })
  | (At & { kind: 'approval'; candidate: string; pct: number })
  | (At & { kind: 'blankShare'; pct: number })
  | (At & { kind: 'winnerShareOfExprimes'; pct: number });

export const STORY_CLAIMS: StoryClaim[] = [
  // "One electorate, several presidents": each beat names its winner.
  { story: 'five', step: 'plurality', kind: 'winner', expected: 'Chirac' },
  { story: 'five', step: 'irv', kind: 'winner', expected: 'Jospin' },
  { story: 'five', step: 'borda', kind: 'winner', expected: 'Bayrou' },
  { story: 'five', step: 'condorcet', kind: 'winner', expected: 'Bayrou' },
  { story: 'five', step: 'approval', kind: 'winner', expected: 'Bayrou' },
  // Clones: "B gathers 56% of the electorate".
  { story: 'clones', step: 'duel', kind: 'firstPref', candidate: 'B', pct: 56 },
  // Blank vote: 67/33, then 62% blank, 96% of the expressed, 36% of all voters, 62% blank.
  { story: 'blank', step: 'clean', kind: 'firstPref', candidate: 'Camille', pct: 67 },
  { story: 'blank', step: 'clean', kind: 'firstPref', candidate: 'Farid', pct: 33 },
  { story: 'blank', step: 'todayLaw', kind: 'blankShare', pct: 62 },
  { story: 'blank', step: 'todayLaw', kind: 'winnerShareOfExprimes', pct: 96 },
  { story: 'blank', step: 'ifCounted', kind: 'winnerShareOfExprimes', pct: 36 },
  { story: 'blank', step: 'competitive', kind: 'blankShare', pct: 62 },
  // Monotonicity: first choices 38/32/29, then Nora at 49.
  { story: 'monotonie', step: 'avant', kind: 'firstPref', candidate: 'Nora', pct: 38 },
  { story: 'monotonie', step: 'avant', kind: 'firstPref', candidate: 'Karim', pct: 32 },
  { story: 'monotonie', step: 'avant', kind: 'firstPref', candidate: 'Yanis', pct: 29 },
  { story: 'monotonie', step: 'apres', kind: 'firstPref', candidate: 'Nora', pct: 49 },
  // Reversal: 39/33/28, then Malik at 61 with every ballot reversed.
  { story: 'renversement', step: 'avant', kind: 'firstPref', candidate: 'Malik', pct: 39 },
  { story: 'renversement', step: 'avant', kind: 'firstPref', candidate: 'Inès', pct: 33 },
  { story: 'renversement', step: 'avant', kind: 'firstPref', candidate: 'Sami', pct: 28 },
  { story: 'renversement', step: 'inverse', kind: 'firstPref', candidate: 'Malik', pct: 61 },
  // Support: approval 61/39, then Hugo at 72.
  { story: 'soutien', step: 'avant', kind: 'approval', candidate: 'Léa', pct: 61 },
  { story: 'soutien', step: 'avant', kind: 'approval', candidate: 'Hugo', pct: 39 },
  { story: 'soutien', step: 'apres', kind: 'approval', candidate: 'Hugo', pct: 72 },
  { story: 'soutien', step: 'apres', kind: 'approval', candidate: 'Léa', pct: 61 },
];
