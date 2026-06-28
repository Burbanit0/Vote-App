import React from 'react';
import { useTranslation } from 'react-i18next';
import { backtest, type RealElection } from '../../lib/realElections';
import fixture from '../../lib/__fixtures__/realElections.json';

// RealElectionPanel — the thesis on a REAL ballot box, not a spatial model. On the
// genuine 2009 Burlington ballots, plurality / IRV / Condorcet each crown a
// different candidate. The strongest possible statement of "the method changes the
// winner": no assumptions, just counted votes.

const METHOD_LABEL: Record<string, { fr: string; en: string }> = {
  plurality: { fr: 'Pluralité (1 tour)', en: 'Plurality (1 round)' },
  two_round: { fr: 'Deux tours', en: 'Two-round runoff' },
  irv: { fr: 'Vote alternatif (IRV)', en: 'Instant-runoff (IRV)' },
  condorcet: { fr: 'Condorcet (Copeland)', en: 'Condorcet (Copeland)' },
  minimax: { fr: 'Condorcet (minimax)', en: 'Condorcet (minimax)' },
};

// Stable colour per distinct winner so the same name reads the same down the list.
const WINNER_TINT = [
  'text-sky-700 dark:text-sky-300',
  'text-amber-700 dark:text-amber-300',
  'text-violet-700 dark:text-violet-300',
  'text-rose-700 dark:text-rose-300',
];

const RealElectionPanel: React.FC = () => {
  const { t, i18n } = useTranslation('playground');
  const fr = i18n.language.startsWith('fr');
  const election = (fixture as { elections: RealElection[] }).elections[0];
  const bt = React.useMemo(() => backtest(election), [election]);

  // Assign each distinct winner a tint, in first-appearance order.
  const tintOf = React.useMemo(() => {
    const map: Record<string, string> = {};
    let i = 0;
    for (const r of bt.results)
      if (!(r.winner in map)) map[r.winner] = WINNER_TINT[i++ % WINNER_TINT.length];
    return map;
  }, [bt]);

  return (
    <div data-testid="real-election-panel" className="flex flex-col gap-2">
      <div className="flex flex-col gap-0.5">
        <p className="text-sm font-medium">{fr ? election.title : election.titleEn}</p>
        <p className="text-[0.65rem] text-muted-foreground">{election.source}</p>
      </div>

      <p data-testid="real-election-headline" className="text-sm">
        {t('realElection.headlinePre')}{' '}
        <strong className="text-amber-600 dark:text-amber-400">{bt.distinctWinners}</strong>{' '}
        {t('realElection.headlineEnd')}
      </p>

      <div className="flex flex-col gap-1">
        {bt.results.map((r) => (
          <div
            key={r.method}
            className="flex items-baseline justify-between gap-2 rounded border border-border px-2 py-1 text-xs"
          >
            <span className="shrink-0 text-muted-foreground">
              {fr ? METHOD_LABEL[r.method].fr : METHOD_LABEL[r.method].en}
            </span>
            <span className="flex flex-col items-end">
              <strong className={tintOf[r.winner]}>{r.winner}</strong>
              <span className="text-[0.65rem] text-muted-foreground/80">{r.detail}</span>
            </span>
          </div>
        ))}
      </div>

      <p className="text-[0.65rem] text-muted-foreground">{t('realElection.note')}</p>
    </div>
  );
};

export default RealElectionPanel;
