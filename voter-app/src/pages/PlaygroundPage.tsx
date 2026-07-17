import React from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { useMetaTags } from '../hooks/useMetaTags';
import {
  PlaygroundProvider,
  usePlaygroundCtx,
} from '../components/playground/PlaygroundController';
import MomentRail, { MOMENTS } from '../components/playground/MomentRail';
import InstrumentPanel from '../components/playground/InstrumentPanel';
import GuidedFooter from '../components/playground/GuidedFooter';
import StoryPlayer from '../components/playground/StoryPlayer';
import ElectorateMoment from '../components/playground/moments/ElectorateMoment';
import MethodMoment from '../components/playground/moments/MethodMoment';
import StrategyMoment from '../components/playground/moments/StrategyMoment';
import CampaignMoment from '../components/playground/moments/CampaignMoment';
import BilanMoment from '../components/playground/moments/BilanMoment';

// Single-instrument shell — a measurement instrument for democracy. A persistent
// Dirigeant/Assemblée switch (the duality) sits orthogonally above a console of
// five "moments" (Électorat → Méthode → Stratégie → Campagne → Bilan), simple to
// complex, one active at a time. The active moment swaps the LEFT control panel
// and drives the instrument's lens; the central screen stays live throughout. A
// guided fil (the footer) walks the moments in order. All state lives in the
// PlaygroundProvider, so this file is pure layout.

const MOMENT_PANELS = {
  electorate: ElectorateMoment,
  method: MethodMoment,
  strategy: StrategyMoment,
  bilan: BilanMoment,
} as const;

// Segmented hardware-style switch for the leader/assembly duality.
const ModeSwitch: React.FC = () => {
  const { mode, setMode } = usePlaygroundCtx();
  const { t } = useTranslation('playground');
  return (
    <div
      data-testid="mode-toggle"
      role="radiogroup"
      aria-label={t('mode.leader')}
      className="inline-flex shrink-0 items-center rounded-full border border-border bg-muted/50 p-0.5 text-sm shadow-inner"
    >
      {(
        [
          ['leader', '👑', t('mode.leader')],
          ['parliament', '🏛', t('mode.assembly')],
        ] as const
      ).map(([id, icon, label]) => (
        <button
          key={id}
          type="button"
          role="radio"
          aria-checked={mode === id}
          data-testid={`mode-toggle-${id}`}
          onClick={() => setMode(id)}
          className={cn(
            'rounded-full px-3.5 py-1.5 font-medium transition-all',
            mode === id
              ? 'bg-primary text-primary-foreground shadow-sm'
              : 'text-muted-foreground hover:text-foreground'
          )}
        >
          <span className="mr-1" aria-hidden>
            {icon}
          </span>
          {label}
        </button>
      ))}
    </div>
  );
};

const PlaygroundShell: React.FC = () => {
  const { activeMoment, setActiveMoment } = usePlaygroundCtx();
  const { t } = useTranslation('playground');
  const meta = MOMENTS.find((m) => m.id === activeMoment) ?? MOMENTS[0];
  const Panel = activeMoment !== 'campaign' ? MOMENT_PANELS[activeMoment] : null;

  return (
    <div data-testid="playground-page" className="w-full px-4 py-4">
      {/* ── Masthead ── */}
      <header className="mb-3 flex flex-wrap items-end justify-between gap-3 border-b border-border pb-3">
        <div>
          <p className="font-mono text-[0.66rem] uppercase tracking-[0.22em] text-primary">
            {t('masthead.kicker')}
          </p>
          <h1 className="mt-0.5 font-display text-2xl font-bold tracking-tight sm:text-3xl">
            {t('masthead.title')}
          </h1>
          <p className="mt-1 max-w-xl text-sm text-muted-foreground">{t('masthead.subtitle')}</p>
        </div>
        <ModeSwitch />
      </header>

      {/* ── Histoires: guided narratives over the same instrument ── */}
      <StoryPlayer />

      {/* ── Moment console ── */}
      <MomentRail active={activeMoment} onSelect={setActiveMoment} />

      <div className="mt-4">
        {activeMoment === 'campaign' ? (
          <CampaignMoment />
        ) : (
          <div
            className={cn(
              'grid grid-cols-1 gap-5',
              // Bilan is a conclusion: give the synthesis/comparison the wide column
              // and shrink the map to a companion. Other moments keep the map large.
              activeMoment === 'bilan' ? 'lg:grid-cols-[1fr_20rem]' : 'lg:grid-cols-[21rem_1fr]'
            )}
          >
            <Card className="h-fit overflow-hidden" data-testid={`moment-${activeMoment}-panel`}>
              <div className="flex items-center gap-2.5 border-b border-border/60 px-4 py-3">
                <span className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10 font-mono text-sm font-semibold text-primary">
                  {meta.n}
                </span>
                <div className="min-w-0">
                  <p className="font-display text-base font-semibold leading-tight">
                    {t(`moments.${activeMoment}.label`)}
                  </p>
                  <p className="truncate text-[0.7rem] text-muted-foreground">
                    {t(`moments.${activeMoment}.hint`)}
                  </p>
                </div>
              </div>
              <CardContent className="flex flex-col gap-4 p-4">{Panel && <Panel />}</CardContent>
            </Card>

            <InstrumentPanel />
          </div>
        )}
      </div>

      <GuidedFooter />
    </div>
  );
};

const PlaygroundPage: React.FC = () => {
  useMetaTags({
    title: 'Playground — un instrument, du simple au complexe',
    description:
      'Un même électorat, un seul instrument. Choisissez la question (dirigeant ou assemblée), puis avancez moment par moment : électorat, méthode, stratégie, campagne, bilan — et observez les effets en direct.',
  });

  return (
    <PlaygroundProvider>
      <PlaygroundShell />
    </PlaygroundProvider>
  );
};

export default PlaygroundPage;
