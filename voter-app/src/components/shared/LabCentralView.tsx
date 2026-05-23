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
import React, { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Badge, Button, Card, Col, Row } from 'react-bootstrap';
import { ElectionResult } from '../../services/electionApi';
import { usePerturbations, PinnedPerturbation } from '../../context/PerturbationsContext';
import { useAnimationBroadcast } from '../../context/AnimationBroadcastContext';
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
  /** Pinned perturbations that have per-method winners — when at least one
   *  is provided, the matrix renders comparison columns showing how each
   *  perturbation alters the winner per method. */
  pinned: PinnedPerturbation[];
  t: (k: string) => string;
}

const MethodsMatrix: React.FC<MatrixProps> = React.memo(({ result, pinned, t }) => {
  // Sort methods alphabetically once per result change
  const methods = useMemo(
    () => Object.entries(result.methods).sort(([a], [b]) => a.localeCompare(b)),
    [result.methods]
  );
  const cw = result.condorcet_winner;

  // Only perturbations that actually published per-method winners
  const pertsWithMethods = useMemo(
    () => pinned.filter((p) => p.winnersByMethod),
    [pinned]
  );

  // Count winners frequency for sorting (most-frequent first)
  const winnerCounts = useMemo(() => {
    const c: Record<string, number> = {};
    methods.forEach(([, m]) => {
      if (m.winner) c[m.winner] = (c[m.winner] ?? 0) + 1;
    });
    return c;
  }, [methods]);

  // Table layout when ≥1 perturbation is pinned (column alignment makes
  // the diff legible across many methods); compact chip layout otherwise.
  const useTable = pertsWithMethods.length > 0;

  return (
    <div data-testid="lab-methods-matrix">
      {useTable ? (
        <div style={{ overflowX: 'auto' }} data-testid="lab-matrix-table">
          <table
            className="table table-sm align-middle mb-0"
            style={{ fontSize: '0.72rem', minWidth: 320 + pertsWithMethods.length * 90 }}
          >
            <thead>
              <tr style={{ background: '#f8f9fa' }}>
                <th style={{ width: 110, fontWeight: 600, color: '#6c757d' }}>
                  {t('lab.method')}
                </th>
                <th style={{ width: 130, fontWeight: 600, color: '#6c757d' }}
                  title={t('lab.baselineWinner')}>
                  {t('lab.baselineWinner')}
                </th>
                {pertsWithMethods.map((p) => (
                  <th
                    key={p.id}
                    style={{ minWidth: 80, fontWeight: 600, color: '#6c757d' }}
                    title={p.summary}
                    data-testid={`matrix-col-${p.type}`}
                  >
                    {p.icon} {p.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {methods.map(([method, md], rowIdx) => {
                const isCW = cw && md.winner === cw;
                const color = candColor(result, md.winner);
                const baseWinner = md.winner;
                return (
                  <tr
                    key={method}
                    style={{ background: rowIdx % 2 === 0 ? '#fff' : '#fafafa' }}
                    data-testid={`matrix-row-${method}`}
                  >
                    <td style={{ color: '#495057' }}>{method}</td>
                    <td>
                      {baseWinner ? (
                        <span
                          className="badge"
                          style={{ background: color, color: '#fff', fontSize: '0.65rem' }}
                        >
                          {baseWinner}
                        </span>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                      {isCW && <span style={{ color: '#198754', fontSize: '0.7rem', marginLeft: 4 }}>✓</span>}
                    </td>
                    {pertsWithMethods.map((p) => {
                      const pertWinner = p.winnersByMethod?.[method];
                      if (pertWinner === undefined) {
                        return (
                          <td key={p.id} style={{ color: '#adb5bd', fontSize: '0.7rem' }}>
                            —
                          </td>
                        );
                      }
                      const changed = pertWinner !== baseWinner;
                      return (
                        <td
                          key={p.id}
                          style={{
                            background: changed ? 'rgba(220,53,69,0.08)' : 'rgba(25,135,84,0.08)',
                          }}
                          data-testid={`matrix-pert-${method}-${p.type}`}
                        >
                          <span
                            className="badge"
                            style={{
                              background: changed ? '#dc3545' : '#198754',
                              color: '#fff', fontSize: '0.6rem',
                            }}
                            title={`${p.label}: ${pertWinner ?? '—'}`}
                          >
                            {pertWinner ?? '—'}
                          </span>
                          {changed && (
                            <span style={{ fontSize: '0.6rem', color: '#dc3545', marginLeft: 4 }}>
                              ≠
                            </span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="d-flex flex-wrap gap-1" style={{ fontSize: '0.72rem' }}>
          {methods.map(([method, md]) => {
            const isCW = cw && md.winner === cw;
            const color = candColor(result, md.winner);
            const baseWinner = md.winner;
            return (
              <div
                key={method}
                className="d-flex align-items-center gap-1 px-2 py-1 rounded flex-wrap"
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
                {baseWinner ? (
                  <span
                    className="badge"
                    style={{ background: color, color: '#fff', fontSize: '0.65rem' }}
                    title={t('lab.baselineWinner')}
                  >
                    {baseWinner}
                  </span>
                ) : (
                  <span className="text-muted">—</span>
                )}
                {isCW && <span style={{ color: '#198754', fontSize: '0.7rem' }}>✓</span>}
              </div>
            );
          })}
        </div>
      )}
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
});
MethodsMatrix.displayName = 'MethodsMatrix';

// ── Active modules summary (which perturbations are on) ──────────────────────

interface ModulesProps {
  config: ElectionResult['config'];
  t: (k: string) => string;
}

const ActiveModulesBar: React.FC<ModulesProps> = React.memo(({ config, t }) => {
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
});
ActiveModulesBar.displayName = 'ActiveModulesBar';

// ── Pinned perturbations panel ──────────────────────────────────────────────

interface PinnedProps {
  pinned: PinnedPerturbation[];
  onUnpin: (id: string) => void;
  onClear: () => void;
  t: (k: string) => string;
}

const PinnedPerturbationsPanel: React.FC<PinnedProps> = React.memo(({
  pinned, onUnpin, onClear, t,
}) => {
  if (pinned.length === 0) {
    return (
      <div
        className="text-muted text-center py-2"
        style={{ fontSize: '0.72rem', borderTop: '1px dashed #dee2e6', marginTop: 12 }}
        data-testid="pinned-empty"
      >
        {t('lab.pinHint')}
      </div>
    );
  }

  return (
    <div className="mt-3 pt-3" style={{ borderTop: '1px dashed #dee2e6' }}
      data-testid="pinned-section">
      <div className="d-flex align-items-center justify-content-between mb-2">
        <span className="fw-semibold" style={{ fontSize: '0.78rem' }}>
          📌 {t('lab.pinnedTitle')} ({pinned.length})
        </span>
        <Button
          variant="link"
          size="sm"
          className="text-muted p-0"
          style={{ fontSize: '0.7rem' }}
          onClick={onClear}
          data-testid="pinned-clear"
        >
          {t('lab.pinnedClearAll')}
        </Button>
      </div>
      <div className="d-flex gap-2 flex-wrap">
        {pinned.map((p) => {
          const changed = p.methodsChanged ?? 0;
          const borderColor = changed > 0 ? '#dc3545' : '#198754';
          return (
            <div
              key={p.id}
              className="border rounded p-2"
              style={{
                background: '#fff',
                borderLeft: `3px solid ${borderColor}`,
                minWidth: 220,
                maxWidth: 340,
                fontSize: '0.74rem',
              }}
              data-testid={`pinned-card-${p.type}`}
            >
              <div className="d-flex align-items-start gap-1">
                <span style={{ fontSize: '0.95rem' }}>{p.icon}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="fw-semibold" style={{ fontSize: '0.76rem' }}>
                    {p.label}
                  </div>
                  <div className="text-muted" style={{ fontSize: '0.7rem', lineHeight: 1.3 }}>
                    {p.summary}
                  </div>
                  {changed > 0 ? (
                    <Badge bg="danger" className="mt-1" style={{ fontSize: '0.6rem' }}>
                      ⚡ {changed} {t('lab.methodsChanged')}
                    </Badge>
                  ) : (
                    <Badge bg="success" className="mt-1" style={{ fontSize: '0.6rem' }}>
                      ✓ {t('lab.winnerStable')}
                    </Badge>
                  )}
                </div>
                <Button
                  size="sm"
                  variant="link"
                  className="text-muted p-0 lh-1"
                  style={{ fontSize: '0.9rem' }}
                  onClick={() => onUnpin(p.id)}
                  aria-label={t('lab.unpinAria')}
                  data-testid={`pinned-unpin-${p.type}`}
                >
                  ×
                </Button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
});
PinnedPerturbationsPanel.displayName = 'PinnedPerturbationsPanel';

// ── Main LabCentralView ──────────────────────────────────────────────────────

interface Props {
  result: ElectionResult | null;
  loading: boolean;
}

// Persist collapsed/focus state across page navigations and refreshes.
const COLLAPSED_LS_KEY = 'votelab_central_collapsed';
const FOCUS_LS_KEY     = 'votelab_central_focus_mode';

function readBool(key: string, fallback: boolean): boolean {
  if (typeof window === 'undefined') return fallback;
  try {
    const v = window.localStorage.getItem(key);
    return v === '1' ? true : v === '0' ? false : fallback;
  } catch {
    return fallback;
  }
}
function writeBool(key: string, value: boolean): void {
  if (typeof window === 'undefined') return;
  try { window.localStorage.setItem(key, value ? '1' : '0'); } catch { /* */ }
}

const LabCentralView: React.FC<Props> = ({ result, loading }) => {
  const { t } = useTranslation();
  const [collapsed, setCollapsed] = useState(() => readBool(COLLAPSED_LS_KEY, false));
  // Focus mode: matrix-only (no map) when user wants to dedicate space to the
  // active tab's drill-down. Persisted so it doesn't reset every navigation.
  const [focusMode, setFocusMode] = useState(() => readBool(FOCUS_LS_KEY, false));
  const { pinned, unpinPerturbation, clearPinned } = usePerturbations();
  const { frame } = useAnimationBroadcast();

  // Persist toggle state
  React.useEffect(() => { writeBool(COLLAPSED_LS_KEY, collapsed); }, [collapsed]);
  React.useEffect(() => { writeBool(FOCUS_LS_KEY,     focusMode); }, [focusMode]);

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

  // Memoised so child IdeologyMapChart doesn't see a new array each parent
  // render (matters because its useEffect deps key off this prop reference).
  const candidateNames = useMemo(
    () => result.candidates.map((c) => c.name),
    [result.candidates]
  );

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
          {/* ── Live animation badge ── */}
          {frame && (
            <Badge bg="info" className="d-inline-flex align-items-center gap-1"
              style={{ fontSize: '0.65rem' }}
              data-testid="animation-frame-badge"
              title={t('lab.animationLive')}>
              ▶ {frame.method.toUpperCase()} — {t('lab.round')} {frame.step}/{frame.totalSteps}
              {frame.eliminated && (
                <span style={{ marginLeft: 4, opacity: 0.85 }}>
                  ✗ {frame.eliminated}
                </span>
              )}
              {frame.currentWinner && (
                <span style={{ marginLeft: 4, fontWeight: 700 }}>
                  🏆 {frame.currentWinner}
                </span>
              )}
            </Badge>
          )}
          <ActiveModulesBar config={result.config} t={t} />
          <Button
            size="sm"
            variant={focusMode ? 'secondary' : 'link'}
            className={focusMode ? '' : 'text-muted p-0'}
            style={{ fontSize: '0.7rem', padding: focusMode ? '2px 8px' : undefined }}
            onClick={() => setFocusMode((f) => !f)}
            data-testid="central-focus-toggle"
            data-tour="lab-focus"
            title={t('lab.focusModeTitle')}
          >
            {focusMode ? '🎯 ' + t('lab.focusOn') : '🎯 ' + t('lab.focusOff')}
          </Button>
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
            {/* ── Ideology map (compact) — hidden in focus mode to give the
                active tab more vertical space ── */}
            {!focusMode && (
              <Col xs={12} lg={6}>
                <div className="fw-semibold mb-1" style={{ fontSize: '0.78rem' }}>
                  🗺 {t('lab.ideologyMapTitle')}
                </div>
                <div style={{
                  maxHeight: 340, overflow: 'auto', border: '1px solid #dee2e6',
                  borderRadius: 4, padding: 4,
                }} data-testid="central-ideology-map">
                  <IdeologyMapChart
                    embedded
                    defaultCandidates={candidateNames}
                    initialCandidatePositions={result.config.candidates}
                    defaultNumVoters={result.config.num_voters}
                    defaultIdeology={result.config.ideology}
                    defaultSeed={result.config.seed}
                  />
                </div>
              </Col>
            )}

            {/* ── Methods matrix (compact) — full width in focus mode ── */}
            <Col xs={12} lg={focusMode ? 12 : 6}>
              <div className="fw-semibold mb-1" style={{ fontSize: '0.78rem' }}>
                📊 {t('lab.methodsMatrixTitle')}
                {pinned.filter(p => p.winnersByMethod).length > 0 && (
                  <span className="text-muted ms-2" style={{ fontSize: '0.65rem', fontWeight: 400 }}>
                    + {pinned.filter(p => p.winnersByMethod).length} {t('lab.perturbationsCompared')}
                  </span>
                )}
              </div>
              <MethodsMatrix result={result} pinned={pinned} t={t} />
            </Col>
          </Row>

          {/* ── Pinned perturbations ── */}
          <PinnedPerturbationsPanel
            pinned={pinned}
            onUnpin={unpinPerturbation}
            onClear={clearPinned}
            t={t}
          />
        </Card.Body>
      )}
    </Card>
  );
};

export default LabCentralView;
