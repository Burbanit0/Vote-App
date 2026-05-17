import React, { useCallback, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import {
  Accordion, Alert, Badge, Button, Card, Col, Container,
  Dropdown, Form, Row, Spinner, Tab, Table, Tabs,
} from 'react-bootstrap';
import { useTranslation } from 'react-i18next';
import { useMetaTags } from '../hooks/useMetaTags';
import { useElection, ElectionCandidate } from '../context/ElectionContext';
import { simulateElection, ElectionResult } from '../services/electionApi';
import LiveBadge from '../components/shared/LiveBadge';
import IdeologyMapChart from '../components/Simulation/IdeologyMapChart';
import VoteStepAnimator from '../components/Simulation/VoteStepAnimator';
import MonteCarloResults from '../components/Simulation/MonteCarloResults';
import ManipulabilityChart from '../components/Simulation/ManipulabilityChart';
import BlankVoteDivergencePanel from '../components/shared/BlankVoteDivergencePanel';
import CampaignSensitivityPanel from '../components/shared/CampaignSensitivityPanel';
import CombinedEffectsMatrix from '../components/shared/CombinedEffectsMatrix';
import HistoricalReferencePanel from '../components/shared/HistoricalReferencePanel';

const COLORS: Record<string, string> = {
  Green: '#007A33', Liberal: '#005CAB', Conservative: '#C8590A', Independent: '#6c757d',
};

// ── Results table ─────────────────────────────────────────────────────────────

const ResultsTab: React.FC<{ result: ElectionResult; t: (k: string) => string }> = ({ result, t }) => {
  const hasBlank = result.config.blank_vote?.enabled;
  const rows = Object.entries(result.methods).sort(([a], [b]) => a.localeCompare(b));

  return (
    <div>
      {/* Summary badges */}
      <div className="d-flex gap-2 flex-wrap mb-3">
        <Badge bg="primary">
          {t('electionLab.methodAgreement')}: {Math.round(result.inter_method_agreement * 100)}%
        </Badge>
        {result.condorcet_winner && (
          <Badge bg="success">Condorcet: {result.condorcet_winner} ✓</Badge>
        )}
        {hasBlank && (
          <Badge bg="warning" text="dark">
            {t('electionLab.blankRate')}: {Math.round(result.blank_rate * 100)}%
          </Badge>
        )}
      </div>

      <Table bordered size="sm" responsive>
        <thead className="table-light">
          <tr>
            <th>{t('common.method')}</th>
            <th>{t('electionLab.winner')}</th>
            {hasBlank && <th>{t('electionLab.winnerWithBlank')}</th>}
            <th>{t('simulation.bayesianRegret')}</th>
            <th>Condorcet ✓</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([method, md]) => {
            const isCondorcet = result.condorcet_winner && md.winner === result.condorcet_winner;
            return (
              <tr key={method}>
                <td className="fw-semibold" style={{ fontSize: '0.82rem' }}>{method}</td>
                <td>
                  {md.winner
                    ? <Badge style={{ background: COLORS[result.candidates.find(c => c.name === md.winner)?.party ?? ''] ?? '#666' }}>{md.winner}</Badge>
                    : <span className="text-muted">—</span>}
                  {isCondorcet && ' ✓'}
                </td>
                {hasBlank && (
                  <td>
                    {md.winner_with_blank
                      ? <Badge bg={md.blank_triggered ? 'warning' : 'secondary'} text="dark">{md.winner_with_blank}</Badge>
                      : <span className="text-muted">—</span>}
                    {md.blank_triggered && <span className="text-warning ms-1">⚠</span>}
                  </td>
                )}
                <td style={{ fontSize: '0.8rem' }}>{md.bayesian_regret?.toFixed(4) ?? '—'}</td>
                <td className="text-center">
                  {md.condorcet_consistent === true && <span style={{ color: '#007A33' }}>✓</span>}
                  {md.condorcet_consistent === false && <span style={{ color: '#B71C1C' }}>✗</span>}
                  {md.condorcet_consistent === null && <span className="text-muted">—</span>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </Table>
    </div>
  );
};

// ── Parameter panel ───────────────────────────────────────────────────────────

const ParameterPanel: React.FC<{ t: (k: string) => string }> = ({ t }) => {
  const { config, setConfig, setConfigDeep } = useElection();

  const updateCandidate = (idx: number, patch: Partial<ElectionCandidate>) => {
    const updated = config.candidates.map((c, i) => i === idx ? { ...c, ...patch } : c);
    setConfig({ candidates: updated });
  };

  const addCandidate = () => {
    if (config.candidates.length >= 6) return;
    const names = ['Dave', 'Eve', 'Frank', 'Grace'];
    const name = names[config.candidates.length - 3] ?? `C${config.candidates.length + 1}`;
    setConfig({ candidates: [...config.candidates, { name, x: 0.0, y: 0.0 }] });
  };

  const removeCandidate = (idx: number) => {
    if (config.candidates.length <= 2) return;
    setConfig({ candidates: config.candidates.filter((_, i) => i !== idx) });
  };

  return (
    <Accordion defaultActiveKey={['0', '1']} alwaysOpen>
      {/* Section 1 — Candidates */}
      <Accordion.Item eventKey="0">
        <Accordion.Header>{t('electionLab.sectionCandidates')}</Accordion.Header>
        <Accordion.Body className="p-2">
          {config.candidates.map((c, i) => (
            <Card key={i} className="mb-2" style={{ fontSize: '0.8rem' }}>
              <Card.Body className="p-2">
                <div className="d-flex align-items-center gap-2 mb-1">
                  <Form.Control
                    size="sm" value={c.name} style={{ maxWidth: 90 }}
                    onChange={(e) => updateCandidate(i, { name: e.target.value })}
                  />
                  {config.candidates.length > 2 && (
                    <Button variant="outline-danger" size="sm" style={{ padding: '1px 6px', fontSize: '0.7rem' }}
                      onClick={() => removeCandidate(i)}>✕</Button>
                  )}
                </div>
                <Form.Label className="small mb-0">
                  {t('electionLab.economy')}: {c.x.toFixed(2)}
                </Form.Label>
                <Form.Range min={-1} max={1} step={0.05} value={c.x}
                  onChange={(e) => updateCandidate(i, { x: Number(e.target.value) })} />
                <Form.Label className="small mb-0">
                  {t('electionLab.social')}: {c.y.toFixed(2)}
                </Form.Label>
                <Form.Range min={-1} max={1} step={0.05} value={c.y}
                  onChange={(e) => updateCandidate(i, { y: Number(e.target.value) })} />
              </Card.Body>
            </Card>
          ))}
          {config.candidates.length < 6 && (
            <Button variant="outline-secondary" size="sm" className="w-100" onClick={addCandidate}>
              + {t('electionLab.addCandidate')}
            </Button>
          )}
        </Accordion.Body>
      </Accordion.Item>

      {/* Section 2 — Electorate */}
      <Accordion.Item eventKey="1">
        <Accordion.Header>{t('electionLab.sectionElectorate')}</Accordion.Header>
        <Accordion.Body className="p-2">
          <Form.Label className="small mb-0">
            {t('electionLab.numVoters')}: <strong>{config.num_voters}</strong>
          </Form.Label>
          <Form.Range min={50} max={1000} step={50} value={config.num_voters}
            onChange={(e) => setConfig({ num_voters: Number(e.target.value) })} />

          <Form.Label className="small mb-1">{t('electionLab.ideology')}</Form.Label>
          <Form.Select size="sm" value={config.ideology} className="mb-2"
            onChange={(e) => setConfig({ ideology: e.target.value })}>
            {['random', 'centrist', 'polarized', 'left_skewed', 'right_skewed'].map((v) => (
              <option key={v} value={v}>{t(`ideology.${v}`)}</option>
            ))}
          </Form.Select>

          <Form.Label className="small mb-1">{t('electionLab.seed')}</Form.Label>
          <Form.Control size="sm" type="number" value={config.seed}
            onChange={(e) => setConfig({ seed: Number(e.target.value) })} />
        </Accordion.Body>
      </Accordion.Item>

      {/* Section 3 — Campaign */}
      <Accordion.Item eventKey="2">
        <Accordion.Header>
          {t('electionLab.sectionCampaign')}
          {config.campaign.enabled && <Badge bg="primary" className="ms-2" style={{ fontSize: '0.6rem' }}>ON</Badge>}
        </Accordion.Header>
        <Accordion.Body className="p-2">
          <Form.Check type="switch" id="campaign-enabled"
            label={<span className="small">{t('electionLab.enabled')}</span>}
            checked={config.campaign.enabled}
            onChange={(e) => setConfigDeep('campaign.enabled', e.target.checked)}
            className="mb-2" />
          {config.campaign.enabled && (
            <>
              <Form.Label className="small mb-0">
                {t('electionLab.numDays')}: <strong>{config.campaign.num_days}</strong>
              </Form.Label>
              <Form.Range min={7} max={60} step={1} value={config.campaign.num_days}
                onChange={(e) => setConfigDeep('campaign.num_days', Number(e.target.value))} />
              <Form.Label className="small mb-0">
                {t('electionLab.pollingEffect')}: <strong>{config.campaign.polling_effect.toFixed(2)}</strong>
              </Form.Label>
              <Form.Range min={0} max={1} step={0.05} value={config.campaign.polling_effect}
                onChange={(e) => setConfigDeep('campaign.polling_effect', Number(e.target.value))} />
            </>
          )}
        </Accordion.Body>
      </Accordion.Item>

      {/* Section 4 — Blank vote */}
      <Accordion.Item eventKey="3">
        <Accordion.Header>
          {t('electionLab.sectionBlank')}
          {config.blank_vote.enabled && <Badge bg="warning" text="dark" className="ms-2" style={{ fontSize: '0.6rem' }}>ON</Badge>}
        </Accordion.Header>
        <Accordion.Body className="p-2">
          <Form.Check type="switch" id="blank-enabled"
            label={<span className="small">{t('electionLab.enabled')}</span>}
            checked={config.blank_vote.enabled}
            onChange={(e) => setConfigDeep('blank_vote.enabled', e.target.checked)}
            className="mb-2" />
          {config.blank_vote.enabled && (
            <>
              <Form.Label className="small mb-1">{t('electionLab.blankRule')}</Form.Label>
              <Form.Select size="sm" value={config.blank_vote.rule} className="mb-3"
                onChange={(e) => setConfigDeep('blank_vote.rule', e.target.value)}>
                <option value="symbolic">Symbolique</option>
                <option value="competitive">Compétitif</option>
                <option value="threshold_30">Seuil 30%</option>
              </Form.Select>

              <div className="border rounded p-2" style={{ fontSize: '0.78rem' }}>
                <strong>{t('electionLab.contagion')}</strong>
                <Form.Check type="switch" id="contagion-enabled"
                  label={<span className="small">{t('electionLab.enabled')}</span>}
                  checked={config.blank_vote.contagion.enabled}
                  onChange={(e) => setConfigDeep('blank_vote.contagion.enabled', e.target.checked)}
                  className="mt-1 mb-1" />
                {config.blank_vote.contagion.enabled && (
                  <>
                    <Form.Label className="small mb-0">β (contagion): {config.blank_vote.contagion.beta.toFixed(2)}</Form.Label>
                    <Form.Range min={0} max={1} step={0.05} value={config.blank_vote.contagion.beta}
                      onChange={(e) => setConfigDeep('blank_vote.contagion.beta', Number(e.target.value))} />
                    <Form.Label className="small mb-0">γ (récupération): {config.blank_vote.contagion.gamma.toFixed(2)}</Form.Label>
                    <Form.Range min={0} max={1} step={0.05} value={config.blank_vote.contagion.gamma}
                      onChange={(e) => setConfigDeep('blank_vote.contagion.gamma', Number(e.target.value))} />
                    <Form.Label className="small mb-1">Réseau</Form.Label>
                    <Form.Select size="sm" value={config.blank_vote.contagion.network}
                      onChange={(e) => setConfigDeep('blank_vote.contagion.network', e.target.value)}>
                      <option value="random">Aléatoire</option>
                      <option value="watts_strogatz">Petit monde</option>
                      <option value="block">Blocs</option>
                    </Form.Select>
                  </>
                )}
              </div>
            </>
          )}
        </Accordion.Body>
      </Accordion.Item>

      {/* Section 5 — Information model */}
      <Accordion.Item eventKey="4">
        <Accordion.Header>
          {t('electionLab.sectionInfo')}
          {config.information_model.enabled && <Badge bg="info" className="ms-2" style={{ fontSize: '0.6rem' }}>ON</Badge>}
        </Accordion.Header>
        <Accordion.Body className="p-2">
          <Form.Check type="switch" id="info-enabled"
            label={<span className="small">{t('electionLab.enabled')}</span>}
            checked={config.information_model.enabled}
            onChange={(e) => setConfigDeep('information_model.enabled', e.target.checked)}
            className="mb-2" />
          {config.information_model.enabled && config.candidates.map((c) => (
            <div key={c.name} className="mb-2">
              <Form.Label className="small mb-0">
                {t('electionLab.mediaBias')} {c.name}:
                <strong className="ms-1">
                  {(config.information_model.media_bias[c.name] ?? 0).toFixed(2)}
                </strong>
              </Form.Label>
              <Form.Range min={-1} max={1} step={0.1}
                value={config.information_model.media_bias[c.name] ?? 0}
                onChange={(e) => setConfigDeep(`information_model.media_bias.${c.name}`, Number(e.target.value))} />
            </div>
          ))}
        </Accordion.Body>
      </Accordion.Item>
    </Accordion>
  );
};

// ── Main page ─────────────────────────────────────────────────────────────────

// ── Sub-simulation shortcuts ──────────────────────────────────────────────────

const SUB_SIMS = [
  { href: '/scenario-builder',      icon: '🎮', key: 'electionLab.subSimulator' },
  { href: '/simulation/compare',    icon: '⚖️', key: 'electionLab.subCompare' },
  { href: '/campaign',              icon: '📅', key: 'electionLab.subCampaign' },
  { href: '/constitutional-crisis', icon: '□',  key: 'electionLab.subBlank' },
  { href: '/blank-contagion',       icon: '🦠', key: 'electionLab.subContagion' },
  { href: '/what-if',               icon: '🔮', key: 'electionLab.subWhatIf' },
] as const;

// ── Main page ─────────────────────────────────────────────────────────────────

const ElectionLabPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  useMetaTags({
    title: 'Election Lab — Vote Lab',
    description: 'Simulation unifiée : combinez campagne, vote blanc, modèle d\'information et comparez toutes les méthodes de vote sur une même élection.',
  });

  const { config, applyScenario, resetConfig, scenarioNames, scenarioMeta } = useElection();

  const [result,  setResult]  = useState<ElectionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);
  const runIdRef              = useRef(0);

  const runSimulation = useCallback(async () => {
    const myRun = ++runIdRef.current;
    setLoading(true);
    setError(null);
    try {
      const res = await simulateElection(config);
      if (runIdRef.current === myRun) setResult(res);
    } catch {
      if (runIdRef.current === myRun) setError(t('electionLab.error'));
    } finally {
      if (runIdRef.current === myRun) setLoading(false);
    }
  }, [config, t]);

  const candidateNames = config.candidates.map((c) => c.name);
  const baseParams = {
    num_candidates: candidateNames.length,
    candidates:     candidateNames,
    num_voters:     config.num_voters,
    ideology_distribution: config.ideology,
  };

  return (
    <Container fluid className="py-4" style={{ maxWidth: 1400 }}>
      {/* Header */}
      <div className="d-flex align-items-center justify-content-between mb-2 flex-wrap gap-2">
        <div>
          <h2 className="mb-0 fw-bold d-flex align-items-center gap-2 flex-wrap">
            🔬 {t('electionLab.title')}
            {scenarioMeta && (
              <Badge bg="primary" style={{ fontSize: '0.6rem', fontWeight: 600 }}>
                🗳️ {scenarioMeta.name}
              </Badge>
            )}
          </h2>
          {scenarioMeta ? (
            <div className="d-flex align-items-center gap-2 flex-wrap mt-1">
              <Badge bg="secondary" style={{ fontSize: '0.62rem' }}>
                {scenarioMeta.phenomenon}
              </Badge>
              <span className="text-muted" style={{ fontSize: '0.8rem' }}>
                {scenarioMeta.description}
              </span>
            </div>
          ) : (
            <p className="text-muted mb-0" style={{ fontSize: '0.85rem' }}>
              {t('electionLab.subtitle')}
            </p>
          )}
        </div>
        <div className="d-flex gap-2 flex-wrap">
          <Dropdown>
            <Dropdown.Toggle variant="outline-secondary" size="sm">
              📋 {t('electionLab.scenario')}
            </Dropdown.Toggle>
            <Dropdown.Menu>
              {scenarioNames.map((name) => (
                <Dropdown.Item key={name} onClick={() => applyScenario(name)}>
                  {t(`electionLab.scenario_${name}`, { defaultValue: name })}
                </Dropdown.Item>
              ))}
              <Dropdown.Divider />
              <Dropdown.Item onClick={resetConfig} className="text-muted">
                ↺ {t('electionLab.reset')}
              </Dropdown.Item>
            </Dropdown.Menu>
          </Dropdown>
        </div>
      </div>

      {/* Sub-simulation shortcuts */}
      <div
        className="d-flex align-items-center gap-2 flex-wrap mb-3 p-2 rounded"
        style={{ background: 'var(--bs-secondary-bg, #f8f9fa)', fontSize: '0.78rem' }}
      >
        <span className="text-muted fw-semibold" style={{ whiteSpace: 'nowrap' }}>
          {t('electionLab.goDeeper')} :
        </span>
        {SUB_SIMS.map(({ href, icon, key }) => (
          <Button
            key={href}
            variant="outline-secondary"
            size="sm"
            onClick={() => navigate(href)}
            style={{ fontSize: '0.76rem', padding: '2px 8px', whiteSpace: 'nowrap' }}
          >
            {icon} {t(key)} ↗
          </Button>
        ))}
      </div>

      <Row className="g-3">
        {/* ── Parameter panel ── */}
        <Col xs={12} md={4} lg={3}>
          <ParameterPanel t={t} />

          <div className="mt-3 d-flex align-items-center gap-2">
            <Button
              variant="primary" className="flex-grow-1"
              onClick={runSimulation}
              disabled={loading}
            >
              {loading
                ? <><Spinner size="sm" className="me-2" />{t('electionLab.simulating')}</>
                : `🗳️ ${result ? t('electionLab.resimulate') : t('electionLab.simulate')}`}
            </Button>
            <LiveBadge loading={loading && !!result} />
          </div>

          {/* Active modules badges */}
          <div className="d-flex flex-wrap gap-1 mt-2" style={{ fontSize: '0.72rem' }}>
            {config.campaign.enabled         && <Badge bg="primary">⏱ {t('electionLab.sectionCampaign')}</Badge>}
            {config.blank_vote.enabled        && <Badge bg="warning" text="dark">□ {t('electionLab.sectionBlank')}</Badge>}
            {config.blank_vote.contagion.enabled && <Badge bg="danger">🦠 {t('electionLab.contagion')}</Badge>}
            {config.information_model.enabled && <Badge bg="info">📡 {t('electionLab.sectionInfo')}</Badge>}
          </div>
        </Col>

        {/* ── Results panel ── */}
        <Col xs={12} md={8} lg={9}>
          {error && <Alert variant="danger">{error}</Alert>}

          {!result && !loading && (
            <Alert variant="info">
              {t('electionLab.noResults')}
            </Alert>
          )}

          {loading && !result && (
            <div className="text-center py-5">
              <Spinner className="mb-2" />
              <div className="text-muted small">{t('electionLab.simulating')}</div>
            </div>
          )}

          {result && (
            <div style={{ opacity: loading ? 0.65 : 1, transition: 'opacity 0.25s' }}>
              <Tabs defaultActiveKey="results" className="mb-3">
                <Tab eventKey="results" title={`📊 ${t('electionLab.tabResults')}`}>
                  <ResultsTab result={result} t={t} />
                  <HistoricalReferencePanel result={result} />
                </Tab>
                <Tab eventKey="map" title={`🗺 ${t('electionLab.tabMap')}`}>
                  <IdeologyMapChart defaultCandidates={candidateNames} />
                </Tab>
                <Tab eventKey="animation" title={`▶ ${t('electionLab.tabAnimation')}`}>
                  <VoteStepAnimator defaultCandidates={candidateNames} />
                </Tab>
                <Tab eventKey="montecarlo" title={`🎲 ${t('electionLab.tabMonteCarlo')}`}>
                  <MonteCarloResults baseParams={baseParams} />
                </Tab>
                <Tab eventKey="manipulability" title={`⚡ ${t('electionLab.tabManipulability')}`}>
                  <ManipulabilityChart baseParams={baseParams} />
                </Tab>
                <Tab eventKey="blank-divergence" title={`📊 ${t('electionLab.tabBlankDivergence')}`}>
                  <BlankVoteDivergencePanel />
                </Tab>
                <Tab eventKey="campaign-sensitivity" title={`📈 ${t('electionLab.tabCampaignSensitivity')}`}>
                  <CampaignSensitivityPanel />
                </Tab>
                <Tab eventKey="combined-effects" title={`🔬 ${t('electionLab.tabCombinedEffects')}`}>
                  <CombinedEffectsMatrix />
                </Tab>
              </Tabs>
            </div>
          )}
        </Col>
      </Row>
    </Container>
  );
};

export default ElectionLabPage;
