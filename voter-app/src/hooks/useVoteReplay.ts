import { useEffect, useMemo, useState } from 'react';
import { buildTrace, sampleVoters } from '../lib/voteTrace';
import type { Rule, Pt, NamedPt } from '../lib/playgroundVoting';

// useVoteReplay — the animation engine behind every "how a method counts" view
// (the replay modal and the side-by-side face-à-face). It samples a watchable
// subset of the electorate, builds the engine-authoritative trace for a rule, and
// walks the frames on a family-appropriate beat. Extracted so the modal and the
// duel share ONE animation clock and can't drift apart.

// Faster animation ⇒ more ballots (each beat is quicker, so a bigger electorate
// still stays watchable). One shared sample per speed, re-drawn on reshuffle.
export const SPEEDS = [
  { key: 'calm', n: 15, div: 1 },
  { key: 'normal', n: 30, div: 2 },
  { key: 'fast', n: 60, div: 4 },
] as const;

// Base beat: counting drops one ballot per beat (fast); rounds/duels need reading.
export const STEP_MS: Record<string, number> = {
  count: 380,
  lottery: 900,
  elim: 950,
  pairwise: 850,
  twophase: 1100,
};

export interface VoteReplayOptions {
  speedIdx?: number;
  seed?: number;
  /** Paused/hidden hosts (a closed modal) freeze the clock. */
  show?: boolean;
  autoplay?: boolean;
  /** Bump to restart from frame 0 without changing rule/seed/speed. */
  restartKey?: number;
}

export function useVoteReplay(
  voters: Pt[],
  candidates: NamedPt[],
  rule: Rule,
  { speedIdx = 0, seed = 1, show = true, autoplay = true, restartKey = 0 }: VoteReplayOptions = {}
) {
  const [frame, setFrame] = useState(0);
  const [playing, setPlaying] = useState(autoplay);
  const speed = SPEEDS[speedIdx] ?? SPEEDS[0];

  const sample = useMemo(() => sampleVoters(voters, speed.n, seed), [voters, speed.n, seed]);
  const trace = useMemo(
    () => (candidates.length >= 2 ? buildTrace(sample, candidates, rule) : null),
    [sample, candidates, rule]
  );

  const nFrames = trace?.frames.length ?? 0;
  const atEnd = frame >= nFrames - 1;

  // Restart the animation on any change of what's being shown.
  useEffect(() => {
    setFrame(0);
    setPlaying(autoplay);
  }, [rule, seed, speedIdx, show, restartKey, autoplay]);

  // Auto-advance while playing.
  useEffect(() => {
    if (!show || !playing || !trace || atEnd) return;
    const ms = (STEP_MS[trace.family] ?? 800) / speed.div;
    const id = window.setTimeout(() => setFrame((f) => f + 1), ms);
    return () => window.clearTimeout(id);
  }, [show, playing, trace, frame, atEnd, speed.div]);

  return { trace, frame, setFrame, playing, setPlaying, nFrames, atEnd };
}
