import React from 'react';
import { useTranslation } from 'react-i18next';
import { usePlaygroundCtx } from '../PlaygroundController';
import Scorecard from '../Scorecard';
import MethodInfo from '../MethodInfo';
import ValuesPanel from '../ValuesPanel';
import Collapsible from '../Collapsible';
import RealElectionPanel from '../RealElectionPanel';
import { useVotingLabels } from '../../../hooks/useVotingLabels';
import { dialWeights, LEADER_AXES_KEYS } from '../../../lib/scorecard';
import { PARLIAMENT_AXES_KEYS } from '../../../lib/playgroundMeta';

// Moment ⑤ Bilan — the verdict. What does the current method/structure score, and
// what is it worth according to YOUR values? The synthesis the journey builds up to.
const BilanMoment: React.FC = () => {
  const { t } = useTranslation('playground');
  const { ruleLabels, structureLabels } = useVotingLabels();
  const {
    mode,
    leaderRule,
    assembly,
    result,
    parlSc,
    currentAxes,
    axisMeta,
    lensItems,
    lensMode,
    setLensMode,
    dial,
    setDial,
    effectiveWeights,
    setLeaderWeights,
    setParlWeights,
  } = usePlaygroundCtx();

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-1 text-sm font-medium">
        <span className="text-muted-foreground">{t('bilan.evaluatedFor')}</span>
        <span>
          {mode === 'leader' ? ruleLabels[leaderRule] : structureLabels[assembly.structure]}
        </span>
        {mode === 'leader' ? (
          <MethodInfo
            method={leaderRule}
            context={{ condorcetExists: result?.condorcet_winner != null }}
            placement="bottom"
          />
        ) : (
          <MethodInfo method={assembly.structure} placement="bottom" />
        )}
      </div>

      <Scorecard
        axes={currentAxes}
        bandNote={t('bilan.bandNote', {
          count: mode === 'leader' ? 20 : (parlSc?.replications ?? 24),
        })}
      />

      <hr className="border-border" />

      {/* FA-2 — the identity dial (one value, correlated weights) */}
      <div data-testid="lijphart-dial-block" className="flex flex-col gap-1">
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold uppercase tracking-wide text-muted-foreground">
            {t('bilan.sensibility')}
          </span>
          <button
            type="button"
            data-testid="lens-granular-toggle"
            className="text-[0.7rem] text-primary underline-offset-2 hover:underline"
            onClick={() => {
              if (lensMode === 'dial') {
                const seeded = dialWeights(dial, mode);
                if (mode === 'leader') setLeaderWeights(seeded);
                else setParlWeights(seeded);
                setLensMode('granular');
              } else {
                setLensMode('dial');
              }
            }}
          >
            {lensMode === 'dial' ? t('bilan.fineTune') : t('bilan.simpleDial')}
          </button>
        </div>
        {lensMode === 'dial' && (
          <>
            <input
              data-testid="lijphart-dial"
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={dial}
              onChange={(e) => setDial(Number(e.target.value))}
              title="Un seul cadran qui règle des pondérations corrélées (convention déclarée) — le réglage fin reste disponible."
            />
            <div className="flex justify-between text-[0.68rem] text-muted-foreground">
              <span>{t('bilan.majoritarian')}</span>
              <span>{t('bilan.consensualist')}</span>
            </div>
          </>
        )}
      </div>

      <ValuesPanel
        items={lensItems}
        axisKeys={mode === 'leader' ? [...LEADER_AXES_KEYS] : PARLIAMENT_AXES_KEYS}
        axisLabels={Object.fromEntries(axisMeta.map((a) => [a.key, a.label]))}
        itemLabels={mode === 'leader' ? ruleLabels : structureLabels}
        weights={effectiveWeights}
        granular={lensMode === 'granular'}
        onWeightChange={(k, v) => {
          setLensMode('granular');
          if (mode === 'leader') setLeaderWeights((w) => ({ ...w, [k]: v }));
          else setParlWeights((w) => ({ ...w, [k]: v }));
        }}
      />

      <Collapsible
        title={t('realElection.title')}
        subtitle={t('realElection.sub')}
        testid="module-real-election"
      >
        <RealElectionPanel />
      </Collapsible>
    </div>
  );
};

export default BilanMoment;
