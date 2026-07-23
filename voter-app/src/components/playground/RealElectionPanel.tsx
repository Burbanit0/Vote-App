import React from 'react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';
import { backtest, type RealElection } from '../../lib/realElections';
import { track } from '../../lib/analytics';
import fixture from '../../lib/__fixtures__/realElections.json';

// RealElectionPanel — the thesis on a REAL ballot box, not a spatial model. The
// strongest possible statement of "the method changes the winner": no
// assumptions, just counted votes. Two ballot boxes ship:
//  · Burlington 2009 — plurality / IRV / Condorcet each crown a DIFFERENT person;
//  · Alaska 2022 special — IRV elects Peltola while Begich beats both rivals
//    head-to-head, the modern textbook Condorcet failure.
// Every number is asserted against the published record in realElections.test.ts.

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

const ELECTIONS = (fixture as { elections: RealElection[] }).elections;

const RealElectionPanel: React.FC = () => {
  const { t, i18n } = useTranslation('playground');
  const fr = i18n.language.startsWith('fr');
  const [id, setId] = React.useState(ELECTIONS[0].id);
  const election = ELECTIONS.find((e) => e.id === id) ?? ELECTIONS[0];
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
      {/* Ballot-box picker — only worth showing once there is more than one. */}
      {ELECTIONS.length > 1 && (
        <div
          role="radiogroup"
          aria-label={t('realElection.pick')}
          data-testid="real-election-pick"
          className="flex flex-wrap gap-1"
        >
          {ELECTIONS.map((e) => (
            <button
              key={e.id}
              type="button"
              role="radio"
              aria-checked={e.id === election.id}
              data-testid={`real-election-${e.id}`}
              onClick={() => {
                track('real_election_selected', { election: e.id });
                setId(e.id);
              }}
              className={cn(
                'rounded-md border px-2 py-0.5 text-[0.7rem] transition-colors',
                e.id === election.id
                  ? 'border-primary/50 bg-accent/50 font-medium'
                  : 'border-border text-muted-foreground hover:bg-accent/30'
              )}
            >
              {fr ? e.title : e.titleEn}
            </button>
          ))}
        </div>
      )}

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
