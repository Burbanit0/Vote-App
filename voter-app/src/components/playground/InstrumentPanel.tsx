import React from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import { Instrument } from '@/components/ui/instrument';
import { usePlaygroundCtx } from './PlaygroundController';
import LeaderCanvas from './LeaderCanvas';
import ParliamentCanvas from './ParliamentCanvas';
import FlipReveal from './FlipReveal';
import Collapsible from './Collapsible';
import DemocracyMap from './DemocracyMap';
import IssuesPanel from './IssuesPanel';
import StructuralPanel from './StructuralPanel';
import { COMMUNITY_PALETTE } from '../../lib/playgroundElectorate';

// InstrumentPanel — the live screen. The spatial map sits inside the signature
// instrument frame (corner ticks + a mono label/readout strip); the headline
// paradox rate is the instrument's live readout. The flip centerpiece swaps the
// map for the active question with its inline robustness/structure readings.
const InstrumentPanel: React.FC = () => {
  const { t } = useTranslation('playground');
  const {
    config,
    playground,
    mode,
    result,
    loading,
    assemblyResult,
    assemblyLoading,
    dims,
    leaderRule,
    setLeaderRule,
    lens,
    setLens,
    youPos,
    setYouPos,
    showYou,
    composed,
    electorate,
    voters,
    voterColors,
    leaderCandidates,
    votingVoters,
    moveCandidate,
    assembly,
    shakeOn,
    setShakeOn,
    shake,
    democracyEntries,
  } = usePlaygroundCtx();

  return (
    <Instrument
      label={mode === 'leader' ? t('instrument.labelLeader') : t('instrument.labelAssembly')}
      readout={
        <span data-testid="cycle-rate" title={t('instrument.paradoxTitle')}>
          {loading || !result
            ? t('instrument.paradoxLoading')
            : t('instrument.paradox', { pct: Math.round(result.cycle_rate * 100) })}
        </span>
      }
    >
      <div className="flex flex-col gap-3">
        {result && (
          <p className="font-mono text-[0.68rem] tracking-tight text-muted-foreground">
            {result.condorcet_winner
              ? t('instrument.condorcet', { name: result.condorcet_winner })
              : t('instrument.condorcetNone')}
          </p>
        )}

        <FlipReveal modeKey={mode} caption="Mêmes électeurs, caractère opposé.">
          {mode === 'leader' ? (
            <div className="flex flex-col gap-3">
              <LeaderCanvas
                candidates={leaderCandidates}
                voters={votingVoters}
                rule={leaderRule}
                dims={dims}
                voterColors={voterColors}
                youMarker={showYou ? youPos : null}
                lens={lens}
                onLensChange={setLens}
                onMoveYou={(x, y) => setYouPos((p) => ({ ...p, x, y }))}
                onRuleChange={setLeaderRule}
                onMoveCandidate={moveCandidate}
              />

              {composed && (
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

              {/* Shake the assumptions: re-roll the electorate → win-rate bands. */}
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
                  <span className="text-xs text-muted-foreground">{t('instrument.shakeHint')}</span>
                )}
                {shakeOn && shake && (
                  <div data-testid="shake-bands" className="flex flex-col gap-1">
                    <p className="text-sm">
                      {shake.top ? (
                        <>
                          <strong>{shake.top}</strong> {t('instrument.shakeHoldsMid')}{' '}
                          <strong>{Math.round((shake.rates[shake.top] ?? 0) * 100)} %</strong>{' '}
                          {t('instrument.shakeHoldsEnd', { count: shake.replications })}
                        </>
                      ) : (
                        '—'
                      )}
                    </p>
                    {config.candidates.map((c) => (
                      <div key={c.name} className="flex items-center gap-2 text-xs">
                        <span className="w-24 truncate text-muted-foreground">{c.name}</span>
                        <div className="h-2.5 flex-1 overflow-hidden rounded bg-muted/50">
                          <div
                            className="h-full animate-pulse rounded bg-primary/70"
                            style={{
                              width: `${(shake.rates[c.name] ?? 0) * 100}%`,
                              transition: 'width 400ms ease',
                            }}
                          />
                        </div>
                        <span className="w-10 text-right font-mono tabular-nums text-muted-foreground">
                          {Math.round((shake.rates[c.name] ?? 0) * 100)} %
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
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
