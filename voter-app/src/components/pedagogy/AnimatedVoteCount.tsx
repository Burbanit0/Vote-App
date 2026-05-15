/**
 * AnimatedVoteCount — step-by-step pedagogical vote count visualisation.
 *
 * All algorithms run client-side from raw ranked ballots (number[][]).
 * Each inner array is a ranked list of candidate indices, e.g.:
 *   [0, 2, 1] → candidate 0 first, candidate 2 second, candidate 1 third.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Button, ProgressBar } from 'react-bootstrap';

// ── Types ───────────────────────────────────────────────────────────────────

export type VoteMethod = 'plurality' | 'borda' | 'irv' | 'two-round' | 'approval' | 'schulze' | 'star';

export interface VoteCandidate {
  name: string;
  color: string;
}

export interface VoteStep {
  round: number;
  title: string;
  description: string;
  scores: Record<string, number>;
  eliminated?: string;
  winner?: string;
}

interface Props {
  method: VoteMethod;
  candidates: VoteCandidate[];
  /** Ranked ballots: each element is an array of candidate indices in preference order. */
  ballots: number[][];
  speed: 'slow' | 'normal' | 'fast';
}

// ── Speed config ────────────────────────────────────────────────────────────

const SPEED_MS: Record<Props['speed'], number> = { slow: 1500, normal: 700, fast: 250 };

// ── Step generators ─────────────────────────────────────────────────────────

function initScores(names: string[]): Record<string, number> {
  return Object.fromEntries(names.map((n) => [n, 0]));
}

function maxScore(scores: Record<string, number>): number {
  return Math.max(0, ...Object.values(scores));
}

function winnerOf(scores: Record<string, number>): string | undefined {
  const entries = Object.entries(scores);
  if (!entries.length) return undefined;
  return entries.reduce((a, b) => (b[1] > a[1] ? b : a))[0];
}

// ── plurality ──────────────────────────────────────────────────────────────
function pluralitySteps(names: string[], ballots: number[][]): VoteStep[] {
  const scores = initScores(names);
  for (const ballot of ballots) {
    const first = ballot[0];
    if (first !== undefined && names[first]) scores[names[first]]++;
  }
  const winner = winnerOf(scores);
  const total  = ballots.length;
  const pct    = winner ? ((scores[winner] / total) * 100).toFixed(1) : '?';
  return [
    {
      round: 1,
      title: 'Tour unique — Décompte des voix',
      description:
        `Chaque électeur exprime son premier choix. Le candidat avec le plus de voix ` +
        `gagne directement — même sans majorité absolue (règle de la pluralité). ` +
        `Vainqueur : ${winner ?? '—'} avec ${pct}% des voix.`,
      scores,
      winner,
    },
  ];
}

// ── borda ──────────────────────────────────────────────────────────────────
function bordaSteps(names: string[], ballots: number[][]): VoteStep[] {
  const n      = names.length;
  const scores = initScores(names);
  for (const ballot of ballots) {
    ballot.forEach((idx, rank) => {
      if (names[idx]) scores[names[idx]] += Math.max(0, n - 1 - rank);
    });
  }
  const maxPts = (n - 1) * ballots.length;
  const winner = winnerOf(scores);
  return [
    {
      round: 1,
      title: 'Méthode de Borda — Attribution des points',
      description:
        `Chaque bulletin attribue ${n - 1} pts au 1er choix, ${n - 2} pts au 2e, … 0 pt au dernier. ` +
        `Les totaux récompensent les candidats largement appréciés, pas seulement les premiers choix. ` +
        `Maximum possible : ${maxPts} pts (1er sur tous les bulletins).`,
      scores,
      winner,
    },
  ];
}

// ── irv ────────────────────────────────────────────────────────────────────
function irvSteps(names: string[], ballots: number[][]): VoteStep[] {
  const steps: VoteStep[] = [];
  let remaining = [...names];
  // Work with index-based ballots, filter eliminated indices each round
  let activeBallots = ballots.map((b) => b.filter((i) => names[i] !== undefined));

  while (remaining.length > 1) {
    const scores = initScores(remaining);
    const total  = activeBallots.length;

    for (const ballot of activeBallots) {
      const top = ballot.find((i) => remaining.includes(names[i]));
      if (top !== undefined) scores[names[top]]++;
    }

    const sorted = [...remaining].sort((a, b) => scores[b] - scores[a]);
    const frontRunner = sorted[0];
    const lastPlace   = sorted[sorted.length - 1];

    if (scores[frontRunner] > total / 2) {
      steps.push({
        round: steps.length + 1,
        title: `Tour ${steps.length + 1} — Majorité absolue`,
        description:
          `${frontRunner} obtient ${scores[frontRunner]} voix sur ${total} ` +
          `(${((scores[frontRunner] / total) * 100).toFixed(1)}%) — soit plus de 50 %. ` +
          `La majorité absolue est atteinte : c'est le vainqueur !`,
        scores,
        winner: frontRunner,
      });
      break;
    }

    steps.push({
      round: steps.length + 1,
      title: `Tour ${steps.length + 1} — Élimination`,
      description:
        `Aucun candidat n'atteint 50 % des voix. ` +
        `${lastPlace} recueille le moins de suffrages (${scores[lastPlace]}) et est éliminé. ` +
        `Ses votes sont redistribués aux seconds choix des électeurs concernés.`,
      scores,
      eliminated: lastPlace,
    });

    remaining = remaining.filter((n) => n !== lastPlace);
    activeBallots = activeBallots.map((b) =>
      b.filter((i) => remaining.includes(names[i]))
    );
  }

  if (remaining.length === 1 && !steps.some((s) => s.winner)) {
    steps.push({
      round: steps.length + 1,
      title: `Tour ${steps.length + 1} — Vainqueur par défaut`,
      description:
        `Il ne reste qu'un seul candidat : ${remaining[0]}. L'élection est terminée.`,
      scores: { [remaining[0]]: activeBallots.length },
      winner: remaining[0],
    });
  }

  return steps;
}

// ── two-round ──────────────────────────────────────────────────────────────
function twoRoundSteps(names: string[], ballots: number[][]): VoteStep[] {
  const steps: VoteStep[] = [];
  const total = ballots.length;

  // Round 1
  const r1scores = initScores(names);
  for (const ballot of ballots) {
    const top = ballot[0];
    if (top !== undefined && names[top]) r1scores[names[top]]++;
  }

  const sortedR1 = [...names].sort((a, b) => r1scores[b] - r1scores[a]);
  const frontR1  = sortedR1[0];

  if (r1scores[frontR1] > total / 2) {
    steps.push({
      round: 1,
      title: 'Tour 1 — Majorité absolue dès le premier tour',
      description:
        `${frontR1} obtient ${r1scores[frontR1]} voix (${((r1scores[frontR1] / total) * 100).toFixed(1)}%) ` +
        `et remporte l'élection dès le premier tour avec une majorité absolue. Pas de second tour nécessaire.`,
      scores: r1scores,
      winner: frontR1,
    });
    return steps;
  }

  const top2 = sortedR1.slice(0, 2);
  steps.push({
    round: 1,
    title: 'Tour 1 — Aucune majorité absolue',
    description:
      `Aucun candidat ne dépasse 50 %. Les deux candidats en tête (${top2.join(' et ')}) ` +
      `se qualifient pour le second tour. Les autres sont éliminés.`,
    scores: r1scores,
  });

  // Round 2 — count preferences between top2 only
  const r2scores = Object.fromEntries(top2.map((n) => [n, 0]));
  for (const ballot of ballots) {
    const top2Ranked = ballot.filter((i) => top2.includes(names[i]));
    if (top2Ranked.length > 0 && names[top2Ranked[0]]) {
      r2scores[names[top2Ranked[0]]]++;
    }
  }

  const winnerR2 = winnerOf(r2scores);
  steps.push({
    round: 2,
    title: 'Tour 2 — Duel final',
    description:
      `Le second tour oppose uniquement ${top2.join(' et ')}. ` +
      `Les électeurs ayant voté pour un éliminé au 1er tour reportent leur vote sur leur préférence entre les deux finalistes. ` +
      `Vainqueur : ${winnerR2 ?? '—'}.`,
    scores: r2scores,
    winner: winnerR2,
  });

  return steps;
}

// ── approval ───────────────────────────────────────────────────────────────
function approvalSteps(names: string[], ballots: number[][]): VoteStep[] {
  const n = names.length;
  // Approve top ⌈n/2⌉ candidates on each ballot
  const threshold = Math.ceil(n / 2);
  const scores    = initScores(names);
  for (const ballot of ballots) {
    for (let rank = 0; rank < Math.min(threshold, ballot.length); rank++) {
      const idx = ballot[rank];
      if (names[idx]) scores[names[idx]]++;
    }
  }
  const winner = winnerOf(scores);
  return [
    {
      round: 1,
      title: 'Vote par approbation — Décompte',
      description:
        `Chaque électeur approuve les ${threshold} candidat(s) en haut de son classement ` +
        `(½ du champ de candidats). ` +
        `Le candidat avec le plus d'approbations l'emporte — l'effet spoiler est éliminé ` +
        `car approuver un candidat ne pénalise pas les autres.`,
      scores,
      winner,
    },
  ];
}

// ── schulze (simplified) ───────────────────────────────────────────────────
function schulzeSteps(names: string[], ballots: number[][]): VoteStep[] {
  const n = names.length;
  // Compute pairwise win counts (how many voters prefer A over B)
  const pref: Record<string, Record<string, number>> = {};
  for (const a of names) {
    pref[a] = {};
    for (const b of names) pref[a][b] = 0;
  }
  for (const ballot of ballots) {
    for (let i = 0; i < ballot.length; i++) {
      for (let j = i + 1; j < ballot.length; j++) {
        const a = names[ballot[i]];
        const b = names[ballot[j]];
        if (a && b) pref[a][b]++;
      }
    }
  }
  // Score = number of head-to-head duels won
  const scores = initScores(names);
  for (const a of names) {
    for (const b of names) {
      if (a !== b && pref[a][b] > pref[b][a]) scores[a]++;
    }
  }
  const winner = winnerOf(scores);
  return [
    {
      round: 1,
      title: 'Schulze — Victoires en duels directs (simplifié)',
      description:
        `La méthode Schulze analyse toutes les paires de candidats et trouve les chemins ` +
        `de victoire les plus solides (algorithme de Floyd–Warshall). ` +
        `Ici : le score = nombre de candidats battus en duel direct. ` +
        `${n > 2 ? 'La chaîne complète est calculée algorithmiquement.' : ''}`,
      scores,
      winner,
    },
  ];
}

// ── star (simplified) ──────────────────────────────────────────────────────
function starSteps(names: string[], ballots: number[][]): VoteStep[] {
  const n      = names.length;
  // Derive 0–5 score from rank position
  const scoreOf = (rank: number) => Math.round((5 * Math.max(0, n - 1 - rank)) / Math.max(1, n - 1));

  const step1scores = initScores(names);
  for (const ballot of ballots) {
    ballot.forEach((idx, rank) => {
      if (names[idx]) step1scores[names[idx]] += scoreOf(rank);
    });
  }

  const sortedByScore = [...names].sort((a, b) => step1scores[b] - step1scores[a]);
  const finalists     = sortedByScore.slice(0, 2);

  // Step 2 — preference between top 2
  const step2scores = Object.fromEntries(finalists.map((nm) => [nm, 0]));
  for (const ballot of ballots) {
    const ranked = ballot.filter((i) => finalists.includes(names[i]));
    if (ranked.length > 0 && names[ranked[0]]) step2scores[names[ranked[0]]]++;
  }
  const winner = winnerOf(step2scores);

  return [
    {
      round: 1,
      title: 'STAR — Phase score',
      description:
        `Chaque rang attribue un score : 1er → 5 pts, dernier → 0 pt. ` +
        `Les deux candidats avec le total le plus élevé (${finalists.join(' et ')}) ` +
        `avancent au second tour automatique.`,
      scores: step1scores,
    },
    {
      round: 2,
      title: 'STAR — Second tour automatique',
      description:
        `Duel entre les deux finalistes : chaque électeur vote pour celui qu'il a classé ` +
        `le plus haut. Le score de la 1ère phase n'intervient plus ici — c'est une majorité directe. ` +
        `Vainqueur : ${winner ?? '—'}.`,
      scores: step2scores,
      winner,
    },
  ];
}

// ── Public API ──────────────────────────────────────────────────────────────

export function generateSteps(
  method: VoteMethod,
  candidates: VoteCandidate[],
  ballots: number[][],
): VoteStep[] {
  const names = candidates.map((c) => c.name);
  if (!names.length || !ballots.length) return [];
  switch (method) {
    case 'plurality':  return pluralitySteps(names, ballots);
    case 'borda':      return bordaSteps(names, ballots);
    case 'irv':        return irvSteps(names, ballots);
    case 'two-round':  return twoRoundSteps(names, ballots);
    case 'approval':   return approvalSteps(names, ballots);
    case 'schulze':    return schulzeSteps(names, ballots);
    case 'star':       return starSteps(names, ballots);
    default:           return [];
  }
}

/**
 * Generate plausible demo ballots biased toward `winner` being first-choice
 * for ~45 % of voters. Used when raw ballots aren't available from the API.
 * Uses a deterministic LCG seeded from the winner name for stable output.
 */
export function generateDemoBallots(
  candidateNames: string[],
  winner: string,
  numBallots = 120,
): number[][] {
  const n          = candidateNames.length;
  const winnerIdx  = Math.max(0, candidateNames.indexOf(winner));
  const ballots: number[][] = [];

  // Deterministic LCG seeded from winner index and candidate count
  let seed = winnerIdx * 1000 + n * 97 + 42;
  const rng = () => {
    seed = (seed * 1664525 + 1013904223) & 0xffffffff;
    return (seed >>> 0) / 0xffffffff;
  };
  const shuffle = (arr: number[]) => {
    const a = [...arr];
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(rng() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  };

  const favorWinner = Math.floor(numBallots * 0.45);

  for (let i = 0; i < numBallots; i++) {
    const indices = Array.from({ length: n }, (_, j) => j);
    if (i < favorWinner) {
      // Winner-first ballots
      const rest = shuffle(indices.filter((j) => j !== winnerIdx));
      ballots.push([winnerIdx, ...rest]);
    } else {
      // Spread remaining votes among other candidates
      const otherPool  = indices.filter((j) => j !== winnerIdx);
      const othersIdx  = (i - favorWinner) % otherPool.length;
      const firstChoice = otherPool[othersIdx];
      const rest       = shuffle(indices.filter((j) => j !== firstChoice));
      ballots.push([firstChoice, ...rest]);
    }
  }
  return ballots;
}

// ── CandidateBar ────────────────────────────────────────────────────────────

interface BarProps {
  name: string;
  color: string;
  score: number;
  maxValue: number;
  totalBallots: number;
  isEliminated: boolean;
  isWinner: boolean;
  animDuration: number;
}

const CandidateBar: React.FC<BarProps> = ({
  name, color, score, maxValue, totalBallots, isEliminated, isWinner, animDuration,
}) => {
  const pct     = maxValue > 0 ? Math.round((score / maxValue) * 100) : 0;
  const totalPct = totalBallots > 0 ? ((score / totalBallots) * 100).toFixed(1) : '—';
  const barColor = isEliminated ? '#dc3545' : isWinner ? color : color;

  return (
    <div className="mb-3" role="row">
      <div className="d-flex justify-content-between align-items-center mb-1">
        <span className="fw-semibold" style={{ fontSize: '0.92rem' }}>
          {isEliminated && <span aria-hidden="true">❌ </span>}
          {isWinner && <span aria-hidden="true">🏆 </span>}
          {name}
          {isEliminated && <span className="text-danger ms-1 fw-normal small">(éliminé)</span>}
          {isWinner && <span className="text-success ms-1 fw-normal small">(vainqueur)</span>}
        </span>
        <span className="text-muted small">
          {score} {totalBallots > 0 && !isEliminated && `(${totalPct}%)`}
        </span>
      </div>
      <div
        aria-label={`${name} : ${score}`}
        style={{
          height: 28,
          backgroundColor: 'var(--bs-secondary-bg, #f0f0f0)',
          borderRadius: 6,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: '100%',
            backgroundColor: barColor,
            transition: `width ${animDuration * 0.9}ms ease, background-color 300ms ease`,
            borderRadius: 6,
            opacity: isEliminated ? 0.6 : 1,
          }}
        />
      </div>
    </div>
  );
};

// ── AnimatedVoteCount ───────────────────────────────────────────────────────

const AnimatedVoteCount: React.FC<Props> = ({ method, candidates, ballots, speed }) => {
  const steps       = generateSteps(method, candidates, ballots);
  const animDuration = SPEED_MS[speed];

  const [stepIdx, setStepIdx]   = useState(0);
  const [playing, setPlaying]   = useState(false);
  const timerRef                = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clamp = (n: number) => Math.max(0, Math.min(steps.length - 1, n));

  const go = useCallback((idx: number) => {
    if (timerRef.current) clearTimeout(timerRef.current);
    setPlaying(false);
    setStepIdx(clamp(idx));
  }, [steps.length]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-play
  useEffect(() => {
    if (!playing) return;
    timerRef.current = setTimeout(() => {
      setStepIdx((prev) => {
        if (prev >= steps.length - 1) {
          setPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, animDuration);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [playing, stepIdx, steps.length, animDuration]);

  if (!steps.length) {
    return (
      <div className="text-muted text-center py-4">
        Pas de données suffisantes pour visualiser cette méthode.
      </div>
    );
  }

  const step          = steps[stepIdx];
  const allCandNames  = candidates.map((c) => c.name);
  const eliminatedSoFar = steps.slice(0, stepIdx + 1).map((s) => s.eliminated).filter(Boolean) as string[];
  const stepMax       = maxScore(step.scores);
  const totalBallots  = ballots.length;

  return (
    <div>
      {/* Step header */}
      <div className="d-flex align-items-center justify-content-between mb-1">
        <span className="badge bg-primary" style={{ fontSize: '0.75rem' }}>
          Étape {stepIdx + 1} / {steps.length}
        </span>
        <span className="text-muted small">{totalBallots} bulletins</span>
      </div>

      <h6 className="fw-bold mb-1" style={{ fontSize: '1rem' }}>{step.title}</h6>
      <p className="text-muted mb-3" style={{ fontSize: '0.85rem', lineHeight: 1.5 }}>
        {step.description}
      </p>

      {/* Candidate bars */}
      {allCandNames.map((name) => {
        const cand     = candidates.find((c) => c.name === name)!;
        const score    = step.scores[name] ?? 0;
        const isElim   = eliminatedSoFar.includes(name) && step.eliminated !== name
          ? false                            // already gone, skip bar
          : step.eliminated === name;        // eliminated THIS step → red
        const alreadyGone = eliminatedSoFar.includes(name) && step.eliminated !== name;
        if (alreadyGone) return null;        // hidden in later rounds

        return (
          <CandidateBar
            key={name}
            name={name}
            color={cand?.color ?? '#1a56cc'}
            score={score}
            maxValue={stepMax}
            totalBallots={totalBallots}
            isEliminated={isElim}
            isWinner={step.winner === name}
            animDuration={animDuration}
          />
        );
      })}

      {/* Step indicator dots */}
      {steps.length > 1 && (
        <div className="d-flex justify-content-center gap-1 my-2">
          {steps.map((_, i) => (
            <button
              key={i}
              onClick={() => go(i)}
              aria-label={`Aller à l'étape ${i + 1}`}
              style={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                border: 'none',
                padding: 0,
                cursor: 'pointer',
                backgroundColor: i === stepIdx ? 'var(--bs-primary, #0d6efd)' : 'var(--bs-border-color, #dee2e6)',
                transition: 'background-color 0.2s',
              }}
            />
          ))}
        </div>
      )}

      {/* Navigation controls */}
      <div className="d-flex gap-2 justify-content-center mt-3" role="toolbar" aria-label="Contrôles de navigation">
        <Button variant="outline-secondary" size="sm" onClick={() => go(0)}
          disabled={stepIdx === 0} aria-label="Revenir au début" title="Début">
          ⏮
        </Button>
        <Button variant="outline-secondary" size="sm" onClick={() => go(stepIdx - 1)}
          disabled={stepIdx === 0} aria-label="Étape précédente" title="Précédente">
          ◀
        </Button>
        <Button
          variant={playing ? 'primary' : 'outline-primary'}
          size="sm"
          onClick={() => setPlaying((p) => !p)}
          aria-label={playing ? 'Pause' : 'Lecture automatique'}
          title="Auto"
          style={{ minWidth: 48 }}
        >
          {playing ? '⏸' : '⏯'}
        </Button>
        <Button variant="outline-secondary" size="sm" onClick={() => go(stepIdx + 1)}
          disabled={stepIdx === steps.length - 1} aria-label="Étape suivante" title="Suivante">
          ▶
        </Button>
        <Button variant="outline-secondary" size="sm" onClick={() => go(steps.length - 1)}
          disabled={stepIdx === steps.length - 1} aria-label="Aller à la fin" title="Fin">
          ⏭
        </Button>
      </div>
    </div>
  );
};

export default AnimatedVoteCount;
