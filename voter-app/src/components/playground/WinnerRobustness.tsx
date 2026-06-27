import React from 'react';
import { useTranslation } from 'react-i18next';
import { winnerDistribution, type WinnerDistribution } from '../../lib/playgroundRobustness';
import type { NamedPt, Pt, Rule } from '../../lib/playgroundVoting';

// Robustness strip under the verdict: re-draws the electorate on N seeds and
// shows how often the rule's winner actually holds. A solid bar = a robust
// result; a split bar = the headline winner is an artefact of one draw.
const DRAWS = 140;

interface Props {
  sampleAtSeed: (seed: number) => Pt[];
  candidates: NamedPt[];
  rule: Rule;
  baseSeed: number;
  /** Candidate colours, aligned to `candidates` (same palette as the map). */
  colors: string[];
  /** The current deterministic winner — flagged fragile if it isn't the modal. */
  winner: string | null;
}

const WinnerRobustness: React.FC<Props> = ({
  sampleAtSeed,
  candidates,
  rule,
  baseSeed,
  colors,
  winner,
}) => {
  const { t } = useTranslation('playground');
  const [dist, setDist] = React.useState<WinnerDistribution | null>(null);

  // Heavy (DRAWS resamples × tally) — debounce so dragging/seed changes don't thrash.
  React.useEffect(() => {
    let alive = true;
    const id = setTimeout(() => {
      const d = winnerDistribution(sampleAtSeed, candidates, rule, DRAWS, baseSeed);
      if (alive) setDist(d);
    }, 180);
    return () => {
      alive = false;
      clearTimeout(id);
    };
  }, [sampleAtSeed, candidates, rule, baseSeed]);

  if (!dist || dist.total === 0 || !dist.modal) return null;

  const colorOf = (name: string): string => {
    const i = candidates.findIndex((c) => c.name === name);
    return i >= 0 ? colors[i % colors.length] : '#94a3b8';
  };
  const pct = Math.round(dist.modalShare * 100);
  const fragile = winner != null && dist.modal !== winner;

  return (
    <div data-testid="winner-robustness" className="mt-1 flex flex-col gap-1">
      <div
        className="flex h-1.5 w-full overflow-hidden rounded-full bg-muted"
        role="img"
        aria-label={t('robustness.aria', { name: dist.modal, pct, n: dist.total })}
      >
        {dist.shares.map((s) => (
          <div
            key={s.name}
            style={{ width: `${s.share * 100}%`, backgroundColor: colorOf(s.name) }}
            title={`${s.name} · ${Math.round(s.share * 100)}%`}
          />
        ))}
      </div>
      <p className="font-mono text-[0.68rem] text-muted-foreground">
        {t('robustness.summary', { name: dist.modal, pct, n: dist.total })}
        {fragile && <span className="ml-1 text-[#9a4513]">{t('robustness.fragile')}</span>}
      </p>
    </div>
  );
};

export default WinnerRobustness;
