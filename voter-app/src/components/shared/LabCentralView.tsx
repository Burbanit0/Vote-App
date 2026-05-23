/**
 * LabCentralView — persistent central visualization for Election Lab.
 *
 * Always visible above the tab navigation so the user can see at a glance:
 *   - WHERE the candidates and voters sit (ideology map)
 *   - WHO wins under each voting method (compact matrix)
 *   - KEY metrics summarising the simulation
 *
 * Reflects the current simulation result. When the user toggles perturbations
 * in the sidebar config (campaign, blank vote, information model), the result
 * is recomputed and this view updates in lockstep.
 */
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Badge, Button, Card, Col, Row } from 'react-bootstrap';
import { ElectionResult } from '../../services/electionApi';
import IdeologyMapChart from '../Simulation/IdeologyMapChart';
import MetricTooltip from './MetricTooltip';

// ── Color palette per party (matches ElectionLabPage) ───────────────────────

const PARTY_COLORS: Record<string, string> = {
  Green: '#007A33', Liberal: '#005CAB',
  Conservative: '#C8590A', Independent: '#6c757d',
};

function candColor(result: ElectionResult, name: string | null): string {
  if (!name) return '#adb5bd';
  const c = result.candidates.find((c) => c.name === name);
  return PARTY_COLORS[c?.party ?? ''] ?? '#6c757d';
}

// ── Compact methods matrix ───────────────────────────────────────────────────

interface MatrixProps {
  result: ElectionResult;
  t: (k: string) => string;
}

const MethodsMatrix: React.FC<MatrixProps> = ({ result, t }) => {
  const methods = Object.entries(result.methods).sort(([a], [b]) => a.localeCompare(b));
  const cw = result.condorcet_winner;

  // Count winners frequency for sorting (most-frequent first)
  const winnerCounts: Record<string, number> = {};
  methods.forEach(([, m]) => {
    if (m.winner) winnerCounts[m.winner] = (winnerCounts[m.winner] ?? 0) + 1;
  });

  return (
    <div data-testid="lab-methods-matrix">
      <div className="d-flex flex-wrap gap-1" style={{ fontSize: '0.72rem' }}>
        {methods.map(([method, md]) => {
          const isCW = cw && md.winner === cw;
          const color = candColor(result, md.winner);
          return (
            <div
              key={method}
              className="d-flex align-items-center gap-1 px-2 py-1 rounded"
              style={{
                background: '#f8f9fa',
                border: `1px solid ${color}33`,
                minWidth: 110,
              }}
              data-testid={`matrix-row-${method}`}
            >
              <span style={{ fontSize: '0.65rem', color: '#6c757d', minWidth: 60 }}>
                {method}
              </span>
              {md.winner ? (
                <span
                  className="badge"
                  style={{ background: color, color: '#fff', fontSize: '0.65rem' }}
                >
                  {md.winner}
                </span>
              ) : (
                <span className="text-muted">—</span>
              )}
              {isCW && <span style={{ color: '#198754', fontSize: '0.7rem' }}>✓</span>}
            </div>
          );
        })}
      </div>
      {/* Compact summary */}
      <div className="mt-2 d-flex flex-wrap gap-2" style={{ fontSize: '0.7rem' }}>
        <Badge bg="primary" className="d-inline-flex align-items-center gap-1">
          {t('electionLab.methodAgreement')}: {Math.round(result.inter_method_agreement * 100)}%
          <MetricTooltip metric="method_agreement" placement="bottom" />
        </Badge>
        {cw ? (
          <Badge bg="success">
            Condorcet: {cw} ✓
          </Badge>
        ) : (
          <Badge bg="warning" text="dark">
            {t('lab.noCondorcet')}
          </Badge>
        )}
        {Object.keys(winnerCounts).length > 1 && (
          <Badge bg="danger">
            ⚠ {Object.keys(winnerCounts).length} {t('lab.differentWinners')}
          </Badge>
        )}
      </div>
    </div>
  );
};

// ── Active modules summary (which perturbations are on) ──────────────────────

interface ModulesProps {
  config: ElectionResult['config'];
  t: (k: string) => string;
}

const ActiveModulesBar: React.FC<ModulesProps> = ({ config, t }) => {
  const active: { key: string; label: string; color: string }[] = [];
  if (config.campaign?.enabled) {
    active.push({ key: 'camp', label: t('electionLab.sectionCampaign'), color: '#0d6efd' });
  }
  if (config.blank_vote?.enabled) {
    active.push({ key: 'blank', label: t('electionLab.sectionBlank'), color: '#ffc107' });
  }
  if (config.blank_vote?.contagion?.enabled) {
    active.push({ key: 'contag', label: t('electionLab.contagion'), color: '#dc3545' });
  }
  if (config.information_model?.enabled) {
    active.push({ key: 'info', label: t('electionLab.sectionInfo'), color: '#0dcaf0' });
  }

  if (active.length === 0) {
    return (
      <div className="text-muted" style={{ fontSize: '0.7rem' }} data-testid="active-modules-none">
        {t('lab.noActivePerturbations')}
      </div>
    );
  }

  return (
    <div className="d-flex gap-1 flex-wrap" data-testid="active-modules-bar">
      {active.map((m) => (
        <span
          key={m.key}
          className="badge"
          style={{ background: m.color, color: '#fff', fontSize: '0.65rem' }}
        >
          {m.label} ON
        </span>
      ))}
    </div>
  );
};

// ── Main LabCentralView ──────────────────────────────────────────────────────

interface Props {
  result: ElectionResult | null;
  loading: boolean;
}

const LabCentralView: React.FC<Props> = ({ result, loading }) => {
  const { t } = useTranslation();
  const [collapsed, setCollapsed] = useState(false);

  // Nothing to show before first simulation
  if (!result) {
    return (
      <Card className="mb-3" data-testid="lab-central-empty" style={{ background: '#f8f9fa' }}>
        <Card.Body className="text-center py-3">
          <div className="text-muted" style={{ fontSize: '0.85rem' }}>
            {loading ? t('lab.loadingCentral') : t('lab.runToSee')}
          </div>
        </Card.Body>
      </Card>
    );
  }

  const candidateNames = result.candidates.map((c) => c.name);

  return (
    <Card
      className="mb-3"
      data-testid="lab-central-view"
      style={{
        borderLeft: '4px solid #0d6efd',
        opacity: loading ? 0.55 : 1,
        transition: 'opacity 0.25s',
      }}
    >
      <Card.Header
        className="d-flex align-items-center justify-content-between py-2"
        style={{ background: '#f8f9fa', fontSize: '0.85rem' }}
      >
        <span className="fw-semibold">
          🔬 {t('lab.centralViewTitle')}
        </span>
        <div className="d-flex align-items-center gap-2">
          <ActiveModulesBar config={result.config} t={t} />
          <Button
            size="sm"
            variant="link"
            className="text-muted p-0"
            style={{ fontSize: '0.72rem' }}
            onClick={() => setCollapsed((c) => !c)}
            data-testid="central-collapse-toggle"
          >
            {collapsed ? '▼ ' + t('lab.expand') : '▲ ' + t('lab.collapse')}
          </Button>
        </div>
      </Card.Header>
      {!collapsed && (
        <Card.Body className="p-3" data-testid="central-body">
          <Row className="g-3">
            {/* ── Ideology map (compact) ── */}
            <Col xs={12} lg={6}>
              <div className="fw-semibold mb-1" style={{ fontSize: '0.78rem' }}>
                🗺 {t('lab.ideologyMapTitle')}
              </div>
              <div style={{
                maxHeight: 340, overflow: 'hidden', border: '1px solid #dee2e6',
                borderRadius: 4, padding: 4,
              }} data-testid="central-ideology-map">
                <IdeologyMapChart
                  defaultCandidates={candidateNames}
                  defaultNumVoters={result.config.num_voters}
                  defaultIdeology={result.config.ideology}
                  defaultSeed={result.config.seed}
                />
              </div>
            </Col>

            {/* ── Methods matrix (compact) ── */}
            <Col xs={12} lg={6}>
              <div className="fw-semibold mb-1" style={{ fontSize: '0.78rem' }}>
                📊 {t('lab.methodsMatrixTitle')}
              </div>
              <MethodsMatrix result={result} t={t} />
            </Col>
          </Row>
        </Card.Body>
      )}
    </Card>
  );
};

export default LabCentralView;
