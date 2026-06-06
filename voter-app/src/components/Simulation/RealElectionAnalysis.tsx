import React, { useMemo } from 'react';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Check } from '@/components/ui/form-controls';
import { Spinner } from '@/components/ui/spinner';
import { Table } from '@/components/ui/table';
import { Trans, useTranslation } from 'react-i18next';
import MethodTooltip from '../shared/MethodTooltip';
import { RealElectionResult } from '../../types';

const CANDIDATE_PALETTE = ['#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f', '#edc948'];

interface Props {
  result: RealElectionResult;
  blankVoteEnabled: boolean;
  blankLoading: boolean;
  onToggleBlankVote: (enabled: boolean) => void;
}

// ── Blank vote comparison table ────────────────────────────────────────────

const BlankComparisonTable: React.FC<{
  methods: Record<string, string | null>;
  methodsWithBlank: Record<string, string | null>;
  pluralityWinner: string;
}> = ({ methods, methodsWithBlank, pluralityWinner }) => {
  const { t } = useTranslation();
  const methodNames = Object.keys(methods);
  const crisisCount = methodNames.filter((m) => methodsWithBlank[m] === 'Blank').length;
  const changedCount = methodNames.filter((m) => methods[m] !== methodsWithBlank[m]).length;

  return (
    <div className="mt-3">
      {/* Summary badges */}
      <div className="flex gap-2 mb-3 flex-wrap items-center">
        {crisisCount > 0 && (
          <Badge variant="danger" style={{ fontSize: '0.82rem' }}>
            {t('simulation.realCrisis', { count: crisisCount, plural: crisisCount > 1 ? 's' : '' })}
          </Badge>
        )}
        {changedCount > 0 && (
          <Badge variant="warning" style={{ fontSize: '0.82rem' }}>
            {t('simulation.realChanged', { count: changedCount, total: methodNames.length })}
          </Badge>
        )}
        {changedCount === 0 && (
          <Badge variant="success" style={{ fontSize: '0.82rem' }}>
            {t('simulation.realNoChange')}
          </Badge>
        )}
      </div>

      {/* Comparison table */}
      <div style={{ overflowX: 'auto' }}>
        <Table className="[&_th]:p-1 [&_td]:p-1 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_th]:border [&_td]:border">
          <thead className="table-light">
            <tr>
              <th style={{ minWidth: 150 }}>{t('common.method')}</th>
              <th className="text-center" style={{ minWidth: 130 }}>
                {t('simulation.realWithoutBlank')}
                <br />
                <small className="font-normal text-muted-foreground">
                  {t('simulation.realOfficialResult')}
                </small>
              </th>
              <th className="text-center" style={{ minWidth: 150 }}>
                {t('simulation.realWithBlank')}
                <br />
                <small className="font-normal text-muted-foreground">
                  {t('simulation.realSimulation')}
                </small>
              </th>
              <th className="text-center" style={{ minWidth: 100 }}>
                {t('simulation.changed')}
              </th>
            </tr>
          </thead>
          <tbody>
            {methodNames.map((method) => {
              const w1 = methods[method] ?? null;
              const w2 = methodsWithBlank[method] ?? null;
              const changed = w1 !== w2;
              const isCrisis = w2 === 'Blank';
              return (
                <tr
                  key={method}
                  style={
                    isCrisis
                      ? { backgroundColor: '#fce8e8' }
                      : changed
                        ? { backgroundColor: '#fff8e1' }
                        : undefined
                  }
                >
                  <td className="ps-2 font-semibold">
                    <MethodTooltip method={method} />
                  </td>
                  <td className="text-center">
                    {w1 ? (
                      <Badge variant={w1 === pluralityWinner ? 'primary' : 'secondary'}>{w1}</Badge>
                    ) : (
                      <span className="text-muted-foreground text-sm">—</span>
                    )}
                  </td>
                  <td className="text-center">
                    {isCrisis ? (
                      <Badge variant="danger">{t('simulation.blankBadge')}</Badge>
                    ) : w2 ? (
                      <Badge variant={changed ? 'warning' : 'secondary'}>{w2}</Badge>
                    ) : (
                      <span className="text-muted-foreground text-sm">—</span>
                    )}
                  </td>
                  <td className="text-center font-bold" style={{ fontSize: '1rem' }}>
                    {isCrisis ? (
                      <span style={{ color: '#dc3545' }}>🚨</span>
                    ) : changed ? (
                      <span style={{ color: '#dc3545' }}>✗</span>
                    ) : (
                      <span style={{ color: '#198754' }}>✓</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      </div>
      <small className="text-muted-foreground">{t('simulation.realLegend')}</small>
    </div>
  );
};

// ── Main component ─────────────────────────────────────────────────────────

const RealElectionAnalysis: React.FC<Props> = ({
  result,
  blankVoteEnabled,
  blankLoading,
  onToggleBlankVote,
}) => {
  const { t } = useTranslation();
  const { election, plurality_winner, first_round_results, divergences, summary } = result;

  const nDifferent = summary.methods_with_different_winner;
  const nTotal = summary.total_methods_with_winner;
  const blankPct = election.estimated_blank_pct ?? 0;

  const METHOD_LABELS: Record<string, string> = useMemo(
    () => ({
      plurality: t('methods.plurality.label'),
      two_round: t('methods.two_round.label'),
      borda: t('methods.borda.label'),
      approval: t('methods.approval.label'),
      irv: t('methods.irv.label'),
      coombs: t('methods.coombs.label'),
      bucklin: t('methods.bucklin.label'),
      minimax: t('methods.minimax.label'),
      schulze: t('methods.schulze.label'),
      condorcet: t('methods.condorcet.label'),
      kemeny_young: t('methods.kemeny_young.label'),
      positional_score: t('methods.positional_score.label'),
      simple_score: t('methods.simple_score.label'),
      star_voting: t('methods.star_voting.label'),
      median_voting: t('methods.median_voting.label'),
      mean_median_hybrid: t('methods.mean_median_hybrid.label'),
      variance_based: t('methods.variance_based.label'),
    }),
    [t]
  );

  const sorted = [...divergences].sort((a, b) => {
    if (a.differs_from_plurality !== b.differs_from_plurality)
      return a.differs_from_plurality ? -1 : 1;
    return (METHOD_LABELS[a.method] ?? a.method).localeCompare(METHOD_LABELS[b.method] ?? b.method);
  });

  const maxPct = Math.max(...Object.values(first_round_results));

  return (
    <div>
      {/* ── Election header ── */}
      <Card className="mb-4 border-0 bg-slate-100">
        <CardBody>
          <h5 className="mb-1">
            {election.name}
            <Badge variant="secondary" className="ms-2" style={{ fontSize: '0.75rem' }}>
              {election.country} · {election.year}
            </Badge>
          </h5>
          <p className="text-muted-foreground text-sm mb-2">{election.description}</p>
          <p className="text-muted-foreground" style={{ fontSize: '0.75rem' }}>
            Source : {election.source}
          </p>
        </CardBody>
      </Card>

      {/* ── First-round results ── */}
      <Card className="mb-4">
        <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
          <strong>{t('simulation.firstRoundResults')}</strong>
          <span className="text-muted-foreground ms-2" style={{ fontSize: '0.85rem' }}>
            {t('simulation.firstRoundDesc')}
          </span>
        </CardHeader>
        <CardBody>
          <div className="flex flex-col gap-1">
            {Object.entries(first_round_results)
              .sort((a, b) => b[1] - a[1])
              .map(([candidate, pct]) => {
                const party = election.candidates.find((c) => c.name === candidate)?.party ?? '';
                const isPlurality = candidate === plurality_winner;
                return (
                  <div key={candidate} className="flex items-center gap-2">
                    <span
                      style={{
                        minWidth: 150,
                        fontWeight: isPlurality ? 700 : 400,
                        fontSize: '0.85rem',
                      }}
                    >
                      {candidate}
                      {isPlurality && (
                        <Badge variant="primary" className="ms-1" style={{ fontSize: '0.65rem' }}>
                          {t('simulation.firstPlace')}
                        </Badge>
                      )}
                    </span>
                    <div
                      style={{
                        flex: 1,
                        height: 14,
                        backgroundColor: '#e9ecef',
                        borderRadius: 3,
                        overflow: 'hidden',
                      }}
                    >
                      <div
                        style={{
                          height: '100%',
                          width: `${(pct / maxPct) * 100}%`,
                          backgroundColor: isPlurality ? '#0d6efd' : '#6ea8fe',
                          borderRadius: 3,
                        }}
                      />
                    </div>
                    <span style={{ minWidth: 45, fontSize: '0.82rem', textAlign: 'right' }}>
                      {pct.toFixed(1)}%
                    </span>
                    <span
                      className="text-muted-foreground"
                      style={{ minWidth: 200, fontSize: '0.75rem' }}
                    >
                      {party}
                    </span>
                  </div>
                );
              })}
          </div>
        </CardBody>
      </Card>

      {/* ── Summary banner ── */}
      {nDifferent > 0 ? (
        <Alert variant="warning" className="py-2 mb-4">
          <Trans
            i18nKey="simulation.realSummaryDiff"
            values={{
              count: nDifferent,
              plural: nDifferent > 1 ? 's' : '',
              total: nTotal,
              plurality_winner,
            }}
          />
          {nDifferent > nTotal / 2 ? t('simulation.realSummaryMajorityDiverges') : ''}
        </Alert>
      ) : (
        <Alert variant="success" className="py-2 mb-4">
          <Trans
            i18nKey="simulation.realSummaryAllAgree"
            values={{ pluralityWinner: plurality_winner }}
          />
        </Alert>
      )}

      {/* ── Methods comparison table ── */}
      <Card className="mb-4">
        <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
          <strong>{t('simulation.comparisonMethods')}</strong>
          <span className="text-muted-foreground ms-2" style={{ fontSize: '0.85rem' }}>
            {t('simulation.comparisonMethodsDesc')}
          </span>
        </CardHeader>
        <CardBody className="p-0">
          <Table className="[&_th]:p-1 [&_td]:p-1 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_th]:border [&_td]:border mb-0">
            <thead className="table-light">
              <tr>
                <th style={{ minWidth: 160 }}>{t('simulation.methodLabel')}</th>
                <th className="text-center" style={{ minWidth: 130 }}>
                  {t('simulation.winnerElected')}
                </th>
                <th className="text-center" style={{ minWidth: 90 }}>
                  {t('simulation.vsPlurality')}
                </th>
              </tr>
            </thead>
            <tbody>
              {sorted.map(({ method, winner, differs_from_plurality }) => (
                <tr
                  key={method}
                  style={differs_from_plurality ? { backgroundColor: '#fff3cd' } : undefined}
                >
                  <td className="ps-2 font-semibold">
                    <MethodTooltip method={method} />
                  </td>
                  <td className="text-center">
                    {winner ? (
                      <Badge
                        variant={
                          winner === plurality_winner
                            ? 'primary'
                            : differs_from_plurality
                              ? 'warning'
                              : 'secondary'
                        }
                      >
                        {winner}
                      </Badge>
                    ) : (
                      <span className="text-muted-foreground text-sm">
                        {t('simulation.noWinner')}
                      </span>
                    )}
                  </td>
                  <td className="text-center font-bold" style={{ fontSize: '1.1rem' }}>
                    {winner === null ? (
                      <span className="text-muted-foreground">—</span>
                    ) : differs_from_plurality ? (
                      <span style={{ color: '#dc3545' }}>✗</span>
                    ) : (
                      <span style={{ color: '#198754' }}>✓</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </CardBody>
      </Card>

      {/* ── Vote blanc simulation ── */}
      <Card className={blankVoteEnabled ? 'border-warning' : ''}>
        <CardHeader className="block space-y-0 border-b border-border px-4 py-2 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <strong>{t('simulation.simulateBlank')}</strong>
            {blankPct > 0 && (
              <span className="text-muted-foreground text-sm">
                {t('simulation.historicalRate', { pct: Math.round(blankPct * 100 * 10) / 10 })}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {blankLoading && <Spinner size="sm" className="text-[#cc9a00]" />}
            <Check
              type="switch"
              id="blank-vote-toggle"
              checked={blankVoteEnabled}
              onChange={(e) => onToggleBlankVote(e.target.checked)}
              label={blankVoteEnabled ? t('simulation.enabled') : t('simulation.disabled')}
              disabled={blankLoading}
            />
          </div>
        </CardHeader>
        <CardBody>
          {blankVoteEnabled && result.methods_with_blank ? (
            <BlankComparisonTable
              methods={result.methods}
              methodsWithBlank={result.methods_with_blank}
              pluralityWinner={plurality_winner}
            />
          ) : blankLoading ? (
            <div className="text-center py-3 text-muted-foreground">
              <Spinner size="sm" className="me-2" />
              {t('simulation.blankSimulationRunning')}
            </div>
          ) : (
            <p className="text-muted-foreground mb-0 text-sm">
              {t('simulation.blankToggleInfo', {
                pct: Math.round(blankPct * 100 * 10) / 10 || '?',
              })}
            </p>
          )}
        </CardBody>
      </Card>

      <p className="text-muted-foreground text-sm mt-3 mb-0">{t('simulation.realFooter')}</p>
    </div>
  );
};

export default RealElectionAnalysis;
