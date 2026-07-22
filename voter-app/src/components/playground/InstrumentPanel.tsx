import React from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import { Instrument } from '@/components/ui/instrument';
import { usePlaygroundCtx } from './PlaygroundController';
import LeaderCanvas from './LeaderCanvas';
import NonSpatialProfileMap from './NonSpatialProfileMap';
import ParliamentCanvas from './ParliamentCanvas';
import { isSpatialSource } from '../../stores/useElectionStore';
import FlipReveal from './FlipReveal';
import Collapsible from './Collapsible';
import DemocracyMap from './DemocracyMap';
import IssuesPanel from './IssuesPanel';
import StructuralPanel from './StructuralPanel';
import { COMMUNITY_PALETTE } from '../../lib/playgroundElectorate';
import { wilsonFromRate } from '../../lib/ci';

// InstrumentPanel — the live screen. The spatial map sits inside the signature
// instrument frame (corner ticks + a mono label/readout strip); the headline
// paradox rate is the instrument's live readout. The flip centerpiece swaps the
// map for the active question with its inline robustness/structure readings.
interface InstrumentPanelProps {
  /** The Lab embeds this panel without the moment rail, so it always wants the
   * full rule UI — only the Playground's Électorat moment hides it. */
  forceShowRuleUi?: boolean;
}

const InstrumentPanel: React.FC<InstrumentPanelProps> = ({ forceShowRuleUi = false }) => {
  const { t } = useTranslation('playground');
  const {
    config,
    playground,
    mode,
    prefSource,
    result,
    loading,
    assemblyResult,
    assemblyLoading,
    dims,
    leaderRule,
    setLeaderRule,
    lens,
    setLens,
    activeMoment,
    behavior,
    strategicOutcome,
    youPos,
    setYouPos,
    showYou,
    composed,
    electorate,
    voters,
    voterColors,
    leaderCandidates,
    votingVoters,
    sampleAtSeed,
    baseSeed,
    moveCandidate,
    assembly,
    shakeOn,
    setShakeOn,
    shake,
    democracyEntries,
  } = usePlaygroundCtx();

  const paradox = (
    <span data-testid="cycle-rate" title={t('instrument.paradoxTitle')}>
      {loading || !result
        ? t('instrument.paradoxLoading')
        : t('instrument.paradox', { pct: Math.round(result.cycle_rate * 100) })}
    </span>
  );

  // Telemetry (top strip): the instrument's live OUTPUTS — Condorcet winner and
  // the paradox rate. Configuration (bottom strip): the standing INPUTS.
  const point = mode === 'leader' ? t('common.candidates') : t('common.parties');
  const telemetry = (
    <span className="flex items-center gap-2">
      {result?.condorcet_winner && (
        <>
          <span className="text-muted-foreground">
            {t('instrument.condorcet', { name: result.condorcet_winner })}
          </span>
          <span aria-hidden className="text-border">
            ·
          </span>
        </>
      )}
      {paradox}
    </span>
  );
  const status = (
    <>
      <span className="text-primary">
        {mode === 'leader' ? t('mode.leader') : t('mode.assembly')}
      </span>
      <span aria-hidden className="text-border">
        ·
      </span>
      <span>
        {config.candidates.length} {point}
      </span>
      <span aria-hidden className="text-border">
        ·
      </span>
      <span>
        {config.num_voters} {t('common.voters')}
      </span>
      {mode === 'leader' && (
        <>
          <span aria-hidden className="text-border">
            ·
          </span>
          <span className="normal-case">{t(`rules.${leaderRule}`)}</span>
        </>
      )}
      <span aria-hidden className="text-border">
        ·
      </span>
      <span className="tabular-nums">seed {config.seed}</span>
    </>
  );

  return (
    <Instrument
      variant="scope"
      label={mode === 'leader' ? t('instrument.labelLeader') : t('instrument.labelAssembly')}
      readout={telemetry}
      status={status}
    >
      <div className="flex flex-col gap-3">
        <FlipReveal modeKey={mode} caption={t('instrument.flipCaption')}>
          {mode === 'leader' ? (
            <div className="flex flex-col gap-3">
              {isSpatialSource(prefSource) ? (
                <LeaderCanvas
                  candidates={leaderCandidates}
                  voters={votingVoters}
                  rule={leaderRule}
                  dims={dims}
                  sampleAtSeed={sampleAtSeed}
                  baseSeed={baseSeed}
                  voterColors={voterColors}
                  youMarker={showYou ? youPos : null}
                  lens={lens}
                  onLensChange={setLens}
                  onMoveYou={(x, y) => setYouPos((p) => ({ ...p, x, y }))}
                  onRuleChange={setLeaderRule}
                  onMoveCandidate={moveCandidate}
                  showRuleUi={forceShowRuleUi || activeMoment !== 'electorate'}
                  behavior={behavior}
                  strategicOutcome={strategicOutcome}
                  manipTactic={playground.stratTactic}
                  manipShare={playground.stratShare}
                />
              ) : (
                <NonSpatialProfileMap />
              )}

              {isSpatialSource(prefSource) && composed && (
                <div
                  data-testid="electorate-legend"
                  className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[0.7rem] text-muted-foreground"
                >
                  {electorate.communities.map((c, i) => (
                    <span key={c.id} className="inline-flex items-center gap-1">
                      <span
                        className="inline-block h-2.5 w-2.5 rounded-full"
                        style={{ background: COMMUNITY_PALETTE[i % COMMUNITY_PALETTE.length] }}
                      />
                      {c.label}
                    </span>
                  ))}
                </div>
              )}

              {/* Shake the assumptions: re-roll the electorate → win-rate bands.
                  Spatial only — it re-rolls the ideological cloud. */}
              {isSpatialSource(prefSource) && (
                <div className="flex flex-col gap-1.5">
                  <Button
                    data-testid="shake-toggle"
                    variant={shakeOn ? 'primary' : 'outline'}
                    size="sm"
                    className="self-start"
                    onClick={() => setShakeOn((s) => !s)}
                    title={t('instrument.shakeTitle')}
                  >
                    {t('instrument.shake')}
                  </Button>
                  {shakeOn && (
                    <span className="text-xs text-muted-foreground">
                      {t('instrument.shakeHint')}
                    </span>
                  )}
                  {shakeOn && shake && (
                    <div data-testid="shake-bands" className="flex flex-col gap-1">
                      <p className="text-sm">
                        {shake.top ? (
                          <>
                            <strong>{shake.top}</strong> {t('instrument.shakeHoldsMid')}{' '}
                            <strong>{Math.round((shake.rates[shake.top] ?? 0) * 100)} %</strong>{' '}
                            {t('instrument.shakeHoldsEnd', { count: shake.replications })}{' '}
                            {(() => {
                              const iv = wilsonFromRate(
                                shake.rates[shake.top] ?? 0,
                                shake.replications
                              );
                              return (
                                <span className="text-muted-foreground">
                                  {t('instrument.shakeCI', {
                                    lo: Math.round(iv.lo * 100),
                                    hi: Math.round(iv.hi * 100),
                                  })}
                                </span>
                              );
                            })()}
                          </>
                        ) : (
                          '—'
                        )}
                      </p>
                      {config.candidates.map((c) => {
                        const rate = shake.rates[c.name] ?? 0;
                        const iv = wilsonFromRate(rate, shake.replications);
                        return (
                          <div key={c.name} className="flex items-center gap-2 text-xs">
                            <span className="w-24 truncate text-muted-foreground">{c.name}</span>
                            {/* Bar = point estimate; the faint overlay spans the 95% CI. */}
                            <div className="relative h-2.5 flex-1 overflow-hidden rounded bg-muted/50">
                              <div
                                className="absolute inset-y-0 bg-primary/20"
                                style={{
                                  left: `${iv.lo * 100}%`,
                                  width: `${(iv.hi - iv.lo) * 100}%`,
                                }}
                                title={t('instrument.shakeCITitle', {
                                  lo: Math.round(iv.lo * 100),
                                  hi: Math.round(iv.hi * 100),
                                })}
                              />
                              <div
                                className="absolute inset-y-0 left-0 rounded bg-primary/70"
                                style={{ width: `${rate * 100}%`, transition: 'width 400ms ease' }}
                              />
                            </div>
                            <span className="w-16 text-right font-mono tabular-nums text-muted-foreground">
                              {Math.round(rate * 100)}±{Math.round(iv.half * 100)}%
                            </span>
                          </div>
                        );
                      })}
                      <p className="text-[0.65rem] text-muted-foreground">
                        {t('instrument.shakeCIFooter', { n: shake.replications })}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              <ParliamentCanvas
                parties={config.candidates}
                voters={voters}
                result={assemblyResult}
                loading={assemblyLoading}
                nominalSeats={assembly.seats}
                onMoveParty={moveCandidate}
              />
              <Collapsible
                title={t('instrument.democracyTitle')}
                subtitle={t('instrument.democracySub')}
                testid="module-democracy"
              >
                {democracyEntries.length > 0 ? (
                  <DemocracyMap entries={democracyEntries} current={assembly.structure} />
                ) : (
                  <p className="text-xs text-muted-foreground">
                    {t('instrument.democracyComputing')}
                  </p>
                )}
              </Collapsible>
              <Collapsible title={t('instrument.issuesTitle')} testid="module-issues">
                <IssuesPanel config={config} playground={playground} />
              </Collapsible>
              <Collapsible title={t('instrument.structuralTitle')} testid="module-structural">
                <StructuralPanel
                  config={config}
                  partyNames={config.candidates.map((c) => c.name)}
                  playground={playground}
                />
              </Collapsible>
            </div>
          )}
        </FlipReveal>
      </div>
    </Instrument>
  );
};

export default InstrumentPanel;
