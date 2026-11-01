import React from 'react';
import { useTranslation } from 'react-i18next';
import { Crown, Landmark } from 'lucide-react';
import { CardContent } from '@/components/ui/card';
import { Segmented } from '@/components/ui/segmented';
import { FoldedCorner, RiseWords } from '@/components/ui/slip';
import { cn } from '@/lib/utils';
import { useMetaTags } from '../hooks/useMetaTags';
import {
  PlaygroundProvider,
  useStoreCtx,
  useJourneyCtx,
} from '../components/playground/PlaygroundController';
import MomentRail, { MOMENTS } from '../components/playground/MomentRail';
import InstrumentPanel from '../components/playground/InstrumentPanel';
import GuidedFooter from '../components/playground/GuidedFooter';
import WinnerStrip from '../components/playground/WinnerStrip';
import StoryPlayer from '../components/playground/StoryPlayer';
import { track } from '../lib/analytics';
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

// The leader/assembly duality: the segmented switch the homepage's rule picker uses.
const ModeSwitch: React.FC = () => {
  const { mode, setMode } = useStoreCtx();
  const { t } = useTranslation('playground');
  return (
    <div data-testid="mode-toggle" className="w-full max-w-xs shrink-0">
      <Segmented
        label={t('mode.leader')}
        value={mode}
        onChange={(id) => {
          track('mode_toggled', { mode: id });
          setMode(id);
        }}
        options={[
          { value: 'leader', label: t('mode.leader'), icon: Crown, testid: 'mode-toggle-leader' },
          {
            value: 'parliament',
            label: t('mode.assembly'),
            icon: Landmark,
            testid: 'mode-toggle-parliament',
          },
        ]}
      />
    </div>
  );
};

const PlaygroundShell: React.FC = () => {
  const { activeMoment, setActiveMoment } = useJourneyCtx();
  const { t } = useTranslation('playground');
  const meta = MOMENTS.find((m) => m.id === activeMoment) ?? MOMENTS[0];
  const Panel = activeMoment !== 'campaign' ? MOMENT_PANELS[activeMoment] : null;

  return (
    <div
      data-testid="playground-page"
      data-touch
      className="mx-auto w-full max-w-[1600px] px-4 pt-8 pb-12 sm:px-6"
    >
      {/* ── Masthead ── */}
      <header className="mb-6 flex flex-wrap items-end justify-between gap-x-10 gap-y-4">
        <div className="flex max-w-3xl flex-col gap-3">
          <p className="home-up text-[15px] font-bold text-primary">{t('masthead.kicker')}</p>
          <h1 className="font-display text-[clamp(40px,4.6vw,68px)] leading-[0.9] font-extrabold">
            <RiseWords text={t('masthead.title')} delay={80} />
          </h1>
          <p
            className="home-up text-base text-muted-foreground"
            style={{ animationDelay: '200ms' }}
          >
            {t('masthead.subtitle')}
          </p>
        </div>
        <ModeSwitch />
      </header>

      {/* ── Histoires: guided narratives over the same instrument ── */}
      <StoryPlayer />

      {/* ── Moment console ── */}
      <MomentRail active={activeMoment} onSelect={setActiveMoment} />
      <WinnerStrip />

      <div className="mt-4">
        {activeMoment === 'campaign' ? (
          <CampaignMoment />
        ) : (
          <div
            className={cn(
              'grid grid-cols-1 gap-5',
              // Bilan is a conclusion: the synthesis leads (wide column), but the
              // map still needs room to read — 20rem cramped its telemetry, lens
              // tabs and Voronoi. Other moments keep the map as the wide column.
              activeMoment === 'bilan'
                ? 'lg:grid-cols-[minmax(0,1fr)_30rem]'
                : 'lg:grid-cols-[21rem_1fr]'
            )}
          >
            {/* The moment's controls, on a slip with its corner folded over (drawn, not cut,
                so their popovers are never clipped); a new moment is laid down by the sweep. */}
            <div
              key={activeMoment}
              className="bench-wipe relative h-fit border border-border bg-card"
              data-testid={`moment-${activeMoment}-panel`}
            >
              <FoldedCorner size={24} />
              <div className="flex items-center gap-3 border-b border-border py-3.5 pr-9 pl-4">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary font-mono text-sm font-semibold text-primary-foreground">
                  {meta.n}
                </span>
                <div className="min-w-0">
                  <p className="font-display text-[24px] leading-none font-extrabold">
                    {t(`moments.${activeMoment}.label`)}
                  </p>
                  <p className="mt-1 truncate text-sm text-muted-foreground">
                    {t(`moments.${activeMoment}.hint`)}
                  </p>
                </div>
              </div>
              <CardContent className="flex flex-col gap-4 p-4">{Panel && <Panel />}</CardContent>
            </div>
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
