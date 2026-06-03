import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Spinner } from '@/components/ui/spinner';
import i18n from '../../i18n';
import { ElectionResult, InterpretResult, interpretElection } from '../../services/electionApi';
import LiveBadge from './LiveBadge';
import MethodGroupDonut from './MethodGroupDonut';

// ── Colour helpers ────────────────────────────────────────────────────────────

const CANDIDATE_COLORS = [
  '#005CAB', '#C8590A', '#007A33', '#7B2D8B', '#9C3A00', '#005f73',
];

function agreementVariant(agreement: number): 'success' | 'warning' | 'danger' {
  if (agreement > 0.80) return 'success';
  if (agreement >= 0.50) return 'warning';
  return 'danger';
}

function agreementLabel(agreement: number, t: (k: string) => string): string {
  if (agreement > 0.80) return t('insight.consensusLabel');
  if (agreement >= 0.50) return t('insight.moderateLabel');
  return t('insight.strongLabel');
}

// ── Main component ────────────────────────────────────────────────────────────

interface Props {
  result: ElectionResult | null;
}

const ElectionInsightPanel: React.FC<Props> = ({ result }) => {
  const { t }    = useTranslation();
  const lang     = (i18n.language?.startsWith('en') ? 'en' : 'fr') as 'fr' | 'en';

  const [insight,  setInsight]  = useState<InterpretResult | null>(null);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState<string | null>(null);
  const runIdRef = useRef(0);

  useEffect(() => {
    if (!result) { setInsight(null); return; }

    const myRun = ++runIdRef.current;
    setLoading(true);
    setError(null);

    interpretElection(result, lang)
      .then((ins) => {
        if (runIdRef.current === myRun) { setInsight(ins); setLoading(false); }
      })
      .catch(() => {
        if (runIdRef.current === myRun) { setError(t('insight.error')); setLoading(false); }
      });
  }, [result, lang, t]);

  if (!result) return null;
  if (loading && !insight) return (
    <div className="flex items-center gap-2 py-2 text-[0.8rem] text-muted-foreground">
      <Spinner size="sm" />
      {t('insight.loading')}
    </div>
  );
  if (error) return <Alert variant="warning" className="mt-2 py-2">{error}</Alert>;
  if (!insight) return null;

  const variant    = agreementVariant(result.inter_method_agreement);
  const variantBg  = variant === 'success' ? 'rgba(0,122,51,0.08)'
                   : variant === 'warning' ? 'rgba(200,89,10,0.08)'
                   : 'rgba(183,28,28,0.08)';

  return (
    <Card className="mt-4" style={{ border: `1.5px solid var(--bs-${variant})` }}>
      <CardHeader
        className="flex flex-row items-center justify-between p-6 py-2"
        style={{ background: variantBg }}
      >
        <strong className="text-[0.88rem]">
          🔍 {t('insight.title')}
        </strong>
        <div className="flex items-center gap-2">
          <Badge variant={variant} className="text-[0.72rem]">
            {agreementLabel(result.inter_method_agreement, t)}
          </Badge>
          <LiveBadge loading={loading && !!insight} />
        </div>
      </CardHeader>

      <CardContent className="p-4">
        {/* A) Headline + method groups ───────────────────────────────── */}
        <p className="mb-4 text-[0.9rem] font-semibold">
          {insight.headline}
        </p>

        {/* Method groups — donut chart + optional divergence text */}
        <div className="mb-4 flex flex-wrap items-start gap-4">
          <MethodGroupDonut
            methodGroups={insight.method_groups}
            totalMethods={Object.keys(result.methods).length}
          />
          {insight.method_groups.length > 1 && (
            <div className="min-w-[120px] flex-1 text-[0.8rem] text-muted-foreground">
              {insight.divergence_reason}
            </div>
          )}
        </div>

        {/* B) Condorcet analysis ─────────────────────────────────────── */}
        <div className="mb-4 flex items-start gap-2 rounded bg-muted p-2 text-[0.82rem]">
          <span className="text-base leading-snug">
            {result.condorcet_exists ? '✓' : '✗'}
          </span>
          <span>{insight.condorcet_analysis}</span>
        </div>

        {/* C) Best / worst method ────────────────────────────────────── */}
        {(insight.best_by_regret || insight.worst_by_regret) && (
          <div className="mb-4 flex flex-wrap gap-2 text-[0.8rem]">
            {insight.best_by_regret && (
              <Badge variant="success" className="px-2 py-1 text-[0.75rem] font-medium">
                ✓ {t('insight.bestMethod')}: {insight.best_by_regret}
              </Badge>
            )}
            {insight.worst_by_regret && insight.worst_by_regret !== insight.best_by_regret && (
              <Badge variant="danger" className="px-2 py-1 text-[0.75rem] font-medium">
                ✗ {t('insight.worstMethod')}: {insight.worst_by_regret}
              </Badge>
            )}
          </div>
        )}

        {/* Blank analysis */}
        {insight.blank_analysis && (
          <Alert variant="warning" className="mb-4 py-2 text-[0.8rem]">
            □ {insight.blank_analysis}
          </Alert>
        )}

        {/* D) Pedagogical note ───────────────────────────────────────── */}
        <p className="mb-4 border-l-[3px] border-border pl-2.5 text-[0.78rem] italic text-muted-foreground">
          {insight.pedagogical_note}
        </p>

        {/* E) Key facts ──────────────────────────────────────────────── */}
        {insight.key_facts.length > 0 && (
          <ul className="mb-0 list-disc pl-5 text-[0.78rem]">
            {insight.key_facts.map((fact, i) => (
              <li key={i} className="text-muted-foreground">{fact}</li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
};

export default ElectionInsightPanel;
