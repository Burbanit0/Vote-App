import React, { useState } from 'react';
import { ruleWinnerFromRanks } from '../../lib/playgroundVoting';

// NoShowParadox — a constructed, interactive demonstration of the participation
// (no-show) paradox: voting can hurt you. On this fixed profile the two-round
// runoff (and IRV) elect B; once some C-supporters ABSTAIN, A enters the runoff
// and wins — and C-supporters prefer A to B. Their participation backfired.
//
// Why constructed (not measured on the live electorate): no-show paradoxes are
// rare and need specific profiles, so they almost never surface on a continuous
// spatial cloud. A canonical example makes the paradox reliably visible — the
// same "Paradoxe construit" pattern used by IssuesPanel/StructuralPanel.

const A = 0;
const B = 1;
const C = 2;
const NAMES = ['A', 'B', 'C'];

// Each group is a bloc of identical ballots (ranking = candidate indices, best→worst).
const GROUPS: { ranking: number[]; count: number }[] = [
  { ranking: [C, A, B], count: 10 }, // C-supporters: prefer A to B
  { ranking: [A, B, C], count: 9 },
  { ranking: [B, A, C], count: 8 },
  { ranking: [B, C, A], count: 7 },
];
const MAX_ABSTAIN = 10; // the C-supporter bloc size

function buildRanks(abstain: number): number[][] {
  const ranks: number[][] = [];
  for (const g of GROUPS) {
    const kept = g.ranking[0] === C ? Math.max(0, g.count - abstain) : g.count;
    for (let i = 0; i < kept; i++) ranks.push(g.ranking);
  }
  return ranks;
}

/** Two-round winner index for the demo profile with `abstain` C-supporters absent. */
export function noShowWinner(abstain: number): number {
  return ruleWinnerFromRanks(buildRanks(abstain), 3, 'two_round');
}

/** First-preference counts (for the mini bar display). */
function firstPrefs(abstain: number): number[] {
  const counts = [0, 0, 0];
  for (const r of buildRanks(abstain)) counts[r[0]] += 1;
  return counts;
}

const COLORS = ['#2563eb', '#dc2626', '#16a34a'];

const NoShowParadox: React.FC = () => {
  const [abstain, setAbstain] = useState(0);
  const winner = noShowWinner(abstain);
  const baseWinner = noShowWinner(0);
  const flipped = winner !== baseWinner;
  const counts = firstPrefs(abstain);
  const total = counts.reduce((s, c) => s + c, 0) || 1;
  // C-supporters rank C>A>B; where does the current winner sit for them? (0 best)
  const cRankOfWinner = [C, A, B].indexOf(winner);
  const cRankOfBase = [C, A, B].indexOf(baseWinner);

  return (
    <div
      data-testid="noshow-demo"
      className="mt-2 rounded-md border border-border p-2 text-[0.7rem]"
    >
      <div className="mb-1 font-medium">
        🚷 Paradoxe du non-votant (exemple — scrutin à deux tours)
      </div>
      <p className="mb-2 text-muted-foreground">
        34 électeurs, 3 candidats. Les partisans de C les classent C ▸ A ▸ B. Faites-en abstenir
        quelques-uns : observez le vainqueur.
      </p>

      <label className="mb-1 flex items-center gap-2">
        <span className="whitespace-nowrap">Partisans de C qui s’abstiennent : {abstain}</span>
        <input
          data-testid="noshow-abstain"
          type="range"
          className="flex-1"
          min={0}
          max={MAX_ABSTAIN}
          step={1}
          value={abstain}
          onChange={(e) => setAbstain(Number(e.target.value))}
        />
      </label>

      {/* First-preference bars */}
      <div className="mb-2 flex flex-col gap-0.5">
        {NAMES.map((n, i) => (
          <div key={n} className="flex items-center gap-2">
            <span className="w-3" style={{ color: COLORS[i] }}>
              {n}
            </span>
            <div className="h-2 flex-1 overflow-hidden rounded bg-muted">
              <div
                className="h-full rounded"
                style={{
                  width: `${(counts[i] / total) * 100}%`,
                  background: COLORS[i],
                  transition: 'width 300ms ease',
                }}
              />
            </div>
            <span className="w-5 text-right tabular-nums text-muted-foreground">{counts[i]}</span>
          </div>
        ))}
      </div>

      <div data-testid="noshow-verdict">
        Vainqueur : <strong style={{ color: COLORS[winner] }}>{NAMES[winner]}</strong>
        {flipped ? (
          <span className="text-[#16a34a]">
            {' '}
            — Paradoxe ! En s’abstenant, les partisans de C font élire {NAMES[winner]} (leur{' '}
            {cRankOfWinner + 1}
            <sup>e</sup> choix), qu’ils préfèrent à {NAMES[baseWinner]} (leur {cRankOfBase + 1}
            <sup>e</sup>/dernier). Leur participation leur nuisait.
          </span>
        ) : (
          <span className="text-muted-foreground">
            {' '}
            — avec tous les votants, c’est le 3<sup>e</sup> choix des partisans de C qui l’emporte.
          </span>
        )}
      </div>
    </div>
  );
};

export default NoShowParadox;
