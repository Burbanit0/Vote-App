import React, { useEffect, useRef, useState } from 'react';
import { Alert, Badge, Card, Spinner } from 'react-bootstrap';
import { useTranslation } from 'react-i18next';
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
    <div className="d-flex align-items-center gap-2 py-2 text-muted" style={{ fontSize: '0.8rem' }}>
      <Spinner size="sm" />
      {t('insight.loading')}
    </div>
  );
  if (error) return <Alert variant="warning" className="py-2 mt-2">{error}</Alert>;
  if (!insight) return null;

  const variant    = agreementVariant(result.inter_method_agreement);
  const variantBg  = variant === 'success' ? 'rgba(0,122,51,0.08)'
                   : variant === 'warning' ? 'rgba(200,89,10,0.08)'
                   : 'rgba(183,28,28,0.08)';

  return (
    <Card className="mt-3" style={{ border: `1.5px solid var(--bs-${variant})` }}>
      <Card.Header
        className="d-flex align-items-center justify-content-between py-2"
        style={{ background: variantBg }}
      >
        <strong style={{ fontSize: '0.88rem' }}>
          🔍 {t('insight.title')}
        </strong>
        <div className="d-flex align-items-center gap-2">
          <Badge bg={variant} style={{ fontSize: '0.72rem' }}>
            {agreementLabel(result.inter_method_agreement, t)}
          </Badge>
          <LiveBadge loading={loading && !!insight} />
        </div>
      </Card.Header>

      <Card.Body className="p-3">
        {/* A) Headline + method groups ───────────────────────────────── */}
        <p className="fw-semibold mb-3" style={{ fontSize: '0.9rem' }}>
          {insight.headline}
        </p>

        {/* Method groups — donut chart + optional divergence text */}
        <div className="d-flex align-items-start gap-3 mb-3 flex-wrap">
          <MethodGroupDonut
            methodGroups={insight.method_groups}
            totalMethods={Object.keys(result.methods).length}
          />
          {insight.method_groups.length > 1 && (
            <div style={{ flex: 1, minWidth: 120, fontSize: '0.8rem' }} className="text-muted">
              {insight.divergence_reason}
            </div>
          )}
        </div>

        {/* B) Condorcet analysis ─────────────────────────────────────── */}
        <div
          className="d-flex align-items-start gap-2 mb-3 p-2 rounded"
          style={{ background: 'var(--bs-secondary-bg, #f8f9fa)', fontSize: '0.82rem' }}
        >
          <span style={{ fontSize: '1rem', lineHeight: 1.4 }}>
            {result.condorcet_exists ? '✓' : '✗'}
          </span>
          <span>{insight.condorcet_analysis}</span>
        </div>

        {/* C) Best / worst method ────────────────────────────────────── */}
        {(insight.best_by_regret || insight.worst_by_regret) && (
          <div className="d-flex gap-2 mb-3 flex-wrap" style={{ fontSize: '0.8rem' }}>
            {insight.best_by_regret && (
              <Badge
                bg="success"
                style={{ fontSize: '0.75rem', padding: '4px 8px', fontWeight: 500 }}
              >
                ✓ {t('insight.bestMethod')}: {insight.best_by_regret}
              </Badge>
            )}
            {insight.worst_by_regret && insight.worst_by_regret !== insight.best_by_regret && (
              <Badge
                bg="danger"
                style={{ fontSize: '0.75rem', padding: '4px 8px', fontWeight: 500 }}
              >
                ✗ {t('insight.worstMethod')}: {insight.worst_by_regret}
              </Badge>
            )}
          </div>
        )}

        {/* Blank analysis */}
        {insight.blank_analysis && (
          <Alert variant="warning" className="py-2 mb-3" style={{ fontSize: '0.8rem' }}>
            □ {insight.blank_analysis}
          </Alert>
        )}

        {/* D) Pedagogical note ───────────────────────────────────────── */}
        <p
          className="text-muted mb-3"
          style={{ fontSize: '0.78rem', fontStyle: 'italic', borderLeft: '3px solid var(--bs-border-color)', paddingLeft: 10 }}
        >
          {insight.pedagogical_note}
        </p>

        {/* E) Key facts ──────────────────────────────────────────────── */}
        {insight.key_facts.length > 0 && (
          <ul className="mb-0" style={{ fontSize: '0.78rem', paddingLeft: 20 }}>
            {insight.key_facts.map((fact, i) => (
              <li key={i} className="text-muted">{fact}</li>
            ))}
          </ul>
        )}
      </Card.Body>
    </Card>
  );
};

export default ElectionInsightPanel;
