import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { usePlaygroundCtx } from './PlaygroundController';
import LeaderCanvas from './LeaderCanvas';
import ParliamentCanvas from './ParliamentCanvas';
import FlipReveal from './FlipReveal';
import Collapsible from './Collapsible';
import DemocracyMap from './DemocracyMap';
import IssuesPanel from './IssuesPanel';
import StructuralPanel from './StructuralPanel';
import { COMMUNITY_PALETTE } from '../../lib/playgroundElectorate';

// InstrumentPanel — the live centre: the headline paradox reading on top, then the
// flip centerpiece (same electorate, the question flips) with the spatial map for
// the active mode and its inline robustness/structure readings.
const InstrumentPanel: React.FC = () => {
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
    <Card>
      <CardContent className="p-3">
        <div
          data-testid="cycle-rate"
          className="mb-3 rounded-md border border-border px-2.5 py-2"
          title="Part des électorats ré-échantillonnés sans vainqueur de Condorcet — un taux élevé signale que le résultat dépend fortement des hypothèses."
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground">
              Taux de paradoxe (cycles)
            </span>
            <span className="font-mono text-sm font-semibold tabular-nums">
              {loading || !result ? '…' : `${Math.round(result.cycle_rate * 100)} %`}
            </span>
          </div>
          {result && (
            <p className="mt-1 text-[0.7rem] text-muted-foreground/80">
              {result.condorcet_winner
                ? `Vainqueur de Condorcet : ${result.condorcet_winner}`
                : 'Aucun vainqueur de Condorcet (cycle).'}
            </p>
          )}
        </div>

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
                  title="Ré-échantillonne l'électorat 60 fois (mêmes hypothèses, nouveaux tirages) — sépare une propriété structurelle d'un réglage choisi."
                >
                  🎲 Secouer les hypothèses
                </Button>
                {shakeOn && (
                  <span className="text-xs text-muted-foreground">
                    Monte-Carlo complet dans les Explorations avancées (Analyse)
                  </span>
                )}
                {shakeOn && shake && (
                  <div data-testid="shake-bands" className="flex flex-col gap-1">
                    <p className="text-sm">
                      {shake.top ? (
                        <>
                          <strong>{shake.top}</strong> tient{' '}
                          <strong>{Math.round((shake.rates[shake.top] ?? 0) * 100)} %</strong> des{' '}
                          {shake.replications} ré-échantillonnages.
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
                title="🗺 Carte des démocraties (Lijphart)"
                subtitle="majoritaire ↔ consensus"
                testid="module-democracy"
              >
                {democracyEntries.length > 0 ? (
                  <DemocracyMap entries={democracyEntries} current={assembly.structure} />
                ) : (
                  <p className="text-xs text-muted-foreground">Calcul en cours…</p>
                )}
              </Collapsible>
              <Collapsible title="🗳 Enjeux & groupage (Ostrogorski)" testid="module-issues">
                <IssuesPanel config={config} playground={playground} />
              </Collapsible>
              <Collapsible title="⚖ Équités structurelles" testid="module-structural">
                <StructuralPanel
                  config={config}
                  partyNames={config.candidates.map((c) => c.name)}
                  playground={playground}
                />
              </Collapsible>
            </div>
          )}
        </FlipReveal>
      </CardContent>
    </Card>
  );
};

export default InstrumentPanel;
