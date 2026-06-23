import React from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router';
import { useElection } from '../../stores/useElectionStore';
import { ElectionResult } from '../../services/electionApi';
import { HISTORICAL_SCENARIOS } from '../../data/historicalScenarios';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';

const CORE_METHODS = ['plurality', 'irv', 'borda', 'schulze', 'approval'] as const;

const PHENOMENON_VARIANT: Record<string, string> = {
  'Paradoxe de Condorcet': 'danger',
  'Effet spoiler': 'warning',
  'Fragmentation & coalition': 'info',
  "Cycle d'Arrow (intransitivité)": 'secondary',
  'Consensus parfait (Condorcet)': 'success',
  'Fragmentation & vote blanc': 'warning',
  'Crise constitutionnelle': 'danger',
};

interface Props {
  result: ElectionResult | null;
}

const HistoricalReferencePanel: React.FC<Props> = ({ result }) => {
  const { t } = useTranslation();
  const { scenarioMeta } = useElection();
  const navigate = useNavigate();

  if (!scenarioMeta) return null;

  const data = HISTORICAL_SCENARIOS[scenarioMeta.id];
  if (!data) return null;

  const variant = PHENOMENON_VARIANT[data.phenomenon] ?? 'secondary';

  return (
    <Card
      className="mt-4 border-2"
      style={{ borderColor: `var(--bs-${variant})` }}
      data-style="tailwind"
    >
      <CardHeader
        className="flex flex-row flex-wrap items-center gap-2 p-6 py-2"
        style={{ background: `var(--bs-${variant}-bg-subtle, #f8f9fa)` }}
      >
        <span className="text-[1.2rem]">{data.flag}</span>
        <strong className="text-[0.9rem]">{data.name}</strong>
        {data.year > 0 && (
          <Badge variant="secondary" className="text-[0.65rem]">
            {data.year}
          </Badge>
        )}
        <Badge variant={variant as never} className="text-[0.65rem]">
          {t('scenarios.phenomenon')}: {data.phenomenon}
        </Badge>
        <div className="ml-auto flex items-center gap-2">
          <Button
            size="sm"
            variant="outline-primary"
            className="px-2 py-0.5 text-[0.7rem]"
            onClick={() => navigate('/playground')}
            data-testid="open-replay-btn"
          >
            📺 {t('replay.openReplay')}
          </Button>
          {data.reference && (
            <a
              href={data.reference}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[0.72rem] text-muted-foreground"
            >
              Wikipedia ↗
            </a>
          )}
        </div>
      </CardHeader>

      <CardContent className="p-4">
        {/* Description pédagogique */}
        <p className="mb-4 text-[0.83rem] leading-relaxed text-muted-foreground">
          {data.description}
        </p>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-12">
          {/* A) Résultat réel */}
          <div className="md:col-span-5">
            <div className="h-full rounded bg-muted p-4 text-[0.82rem]">
              <div className="mb-2 text-[0.85rem] font-semibold">
                🏛️ {t('scenarios.realResult')}
              </div>
              <div className="mb-1 text-muted-foreground">
                {t('scenarios.method')} : <strong>{data.real_result.method}</strong>
              </div>
              <div className="mb-2">
                {t('scenarios.winner')} :{' '}
                <Badge variant="primary" className="text-[0.78rem]">
                  {data.real_result.winner}
                </Badge>
              </div>
              <div className="text-[0.78rem] leading-snug text-muted-foreground">
                {data.real_result.context}
              </div>

              {/* Vote shares if available */}
              {data.vote_shares && (
                <div className="mt-4">
                  <div className="mb-1 text-[0.75rem] uppercase tracking-wider text-muted-foreground">
                    {t('scenarios.voteShares')}
                  </div>
                  {Object.entries(data.vote_shares)
                    .sort(([, a], [, b]) => b - a)
                    .slice(0, 5)
                    .map(([name, pct]) => (
                      <div key={name} className="mb-1 flex items-center gap-2">
                        <span className="min-w-[100px] text-[0.75rem]">{name}</span>
                        <div
                          className="rounded bg-primary/60"
                          style={{ width: `${Math.round(pct * 2)}px`, height: 8, minWidth: 4 }}
                        />
                        <span className="text-[0.75rem] text-muted-foreground">
                          {pct.toFixed(1)}%
                        </span>
                      </div>
                    ))}
                </div>
              )}
            </div>
          </div>

          {/* B) Comparaison simulation vs réel */}
          {result && (
            <div className="md:col-span-7">
              <div className="mb-2 text-[0.85rem] font-semibold">
                ⚖️ {t('scenarios.simulatedComparison')}
              </div>
              <table className="w-full border-collapse text-[0.78rem]">
                <thead className="bg-muted">
                  <tr className="border border-border [&>th]:border [&>th]:border-border [&>th]:p-1.5">
                    <th>{t('common.method')}</th>
                    <th className="text-center">{t('scenarios.simulatedWinner')}</th>
                    <th className="text-center">{t('scenarios.vsReal')}</th>
                  </tr>
                </thead>
                <tbody>
                  {CORE_METHODS.map((method) => {
                    const md = result.methods[method];
                    const simWin = md?.winner ?? '—';
                    const sameAs = simWin === data.real_result.winner;
                    return (
                      <tr key={method} className="[&>td]:border [&>td]:border-border [&>td]:p-1.5">
                        <td className="font-semibold">{method}</td>
                        <td className="text-center">
                          <span
                            className="inline-flex items-center rounded-md px-2 py-0.5 text-[0.72rem] font-semibold text-white"
                            style={{ background: sameAs ? '#007A33' : 'var(--bs-secondary)' }}
                          >
                            {simWin}
                          </span>
                        </td>
                        <td className="text-center">
                          {data.real_result.winner === '—' ? (
                            <span className="text-muted-foreground">—</span>
                          ) : sameAs ? (
                            <span style={{ color: '#007A33' }}>✓</span>
                          ) : (
                            <span style={{ color: '#B71C1C' }}>✗</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>

              {/* Condorcet info */}
              {result.condorcet_winner ? (
                <div className="text-[0.78rem]" style={{ color: '#007A33' }}>
                  ✓ {t('scenarios.condorcetExists', { winner: result.condorcet_winner })}
                </div>
              ) : (
                <div className="text-[0.78rem]" style={{ color: '#B71C1C' }}>
                  ✗ {t('scenarios.condorcetNone')}
                </div>
              )}
            </div>
          )}
        </div>

        {/* C) Message pédagogique contextuel */}
        {result && (
          <Alert variant={variant as never} className="mb-0 mt-4 py-2 text-[0.8rem]">
            {t(`scenarios.pedagogical_${scenarioMeta.id}`, {
              defaultValue: data.description,
            })}
          </Alert>
        )}
      </CardContent>
    </Card>
  );
};

export default HistoricalReferencePanel;
