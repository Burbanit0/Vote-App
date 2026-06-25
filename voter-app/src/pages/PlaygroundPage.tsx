import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useMetaTags } from '../hooks/useMetaTags';
import {
  PlaygroundProvider,
  usePlaygroundCtx,
} from '../components/playground/PlaygroundController';
import MomentRail, { MOMENTS } from '../components/playground/MomentRail';
import InstrumentPanel from '../components/playground/InstrumentPanel';
import Frontieres from '../components/playground/Frontieres';
import GuidedFooter from '../components/playground/GuidedFooter';
import ElectorateMoment from '../components/playground/moments/ElectorateMoment';
import MethodMoment from '../components/playground/moments/MethodMoment';
import StrategyMoment from '../components/playground/moments/StrategyMoment';
import CampaignMoment from '../components/playground/moments/CampaignMoment';
import BilanMoment from '../components/playground/moments/BilanMoment';

// Single-instrument shell. One page, one live instrument. A persistent
// Dirigeant/Assemblée toggle (the duality) sits orthogonally above a rail of five
// "moments" (Électorat → Méthode → Stratégie → Campagne → Bilan), simple to
// complex, one active at a time. The active moment swaps the LEFT control panel
// and drives the instrument's lens; the central map stays live throughout. A
// guided fil (the footer) walks the moments in order. All state lives in the
// PlaygroundProvider, so this file is pure layout.

const MOMENT_PANELS = {
  electorate: ElectorateMoment,
  method: MethodMoment,
  strategy: StrategyMoment,
  bilan: BilanMoment,
} as const;

const PlaygroundShell: React.FC = () => {
  const { mode, setMode, activeMoment, setActiveMoment } = usePlaygroundCtx();
  const meta = MOMENTS.find((m) => m.id === activeMoment) ?? MOMENTS[0];
  const Panel = activeMoment !== 'campaign' ? MOMENT_PANELS[activeMoment] : null;

  return (
    <div data-testid="playground-page" className="container mx-auto px-3 py-4">
      <header className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">🎛 Instrument de vote</h1>
          <p className="text-sm text-muted-foreground">
            Un seul appareil, du simple au complexe — choisissez la question, puis avancez moment
            par moment.
          </p>
        </div>
        <div
          data-testid="mode-toggle"
          role="radiogroup"
          aria-label="Question"
          className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-border bg-card p-1"
        >
          <Button
            data-testid="mode-toggle-leader"
            variant={mode === 'leader' ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setMode('leader')}
          >
            👑 Dirigeant
          </Button>
          <Button
            data-testid="mode-toggle-parliament"
            variant={mode === 'parliament' ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setMode('parliament')}
          >
            🏛 Assemblée
          </Button>
        </div>
      </header>

      <MomentRail active={activeMoment} onSelect={setActiveMoment} />
      <p className="mb-4 mt-1.5 px-1 text-sm text-muted-foreground">{meta.hint}</p>

      {activeMoment === 'campaign' ? (
        <CampaignMoment />
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[22rem_1fr]">
          <Card className="h-fit" data-testid={`moment-${activeMoment}-panel`}>
            <CardHeader className="p-4 pb-2">
              <CardTitle className="text-base">
                {meta.icon} {meta.label}
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4 p-4 pt-2">{Panel && <Panel />}</CardContent>
          </Card>

          <InstrumentPanel />
        </div>
      )}

      <Frontieres />
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
