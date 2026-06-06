import React, { useCallback, useRef, useState } from 'react';
import { Accordion } from '@/components/ui/accordion';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Tab, Tabs } from '@/components/ui/bootstrap-tabs';
import { Button } from '@/components/ui/button';
import { Card, CardBody } from '@/components/ui/card';
import { Dropdown } from '@/components/ui/dropdown';
import { Check, Control, Range, Select } from '@/components/ui/form-controls';
import { Col, Row } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import { Table } from '@/components/ui/table';
import { PageContainer } from '../theme';
import { useTranslation } from 'react-i18next';
import { useMetaTags } from '../hooks/useMetaTags';
import { useElection, ElectionCandidate } from '../stores/useElectionStore';
import { simulateElection, ElectionResult } from '../services/electionApi';
import LiveBadge from '../components/shared/LiveBadge';
import IdeologyMapChart from '../components/Simulation/IdeologyMapChart';
import VoteStepAnimator from '../components/Simulation/VoteStepAnimator';
import MonteCarloResults from '../components/Simulation/MonteCarloResults';
import ManipulabilityChart from '../components/Simulation/ManipulabilityChart';
import BlankVoteDivergencePanel from '../components/shared/BlankVoteDivergencePanel';
import CampaignSensitivityPanel from '../components/shared/CampaignSensitivityPanel';
import CombinedEffectsMatrix from '../components/shared/CombinedEffectsMatrix';
import ElectionPipelineAnimator from '../components/shared/ElectionPipelineAnimator';
import HistoricalReferencePanel from '../components/shared/HistoricalReferencePanel';
import MetricTooltip from '../components/shared/MetricTooltip';
import ElectionInsightPanel from '../components/shared/ElectionInsightPanel';
import ModelAssumptionsBanner from '../components/shared/ModelAssumptionsBanner';
import LabCentralView from '../components/shared/lab/LabCentralView';
import LabOnboardingTour, { LAB_TOUR_LS_KEY } from '../components/shared/lab/LabOnboardingTour';
import ScenarioIO from '../components/shared/lab/ScenarioIO';
import CollectiveWillPanel from '../components/shared/CollectiveWillPanel';
import AssumptionTesterPanel from '../components/shared/AssumptionTesterPanel';
import EpistocracyPanel from '../components/shared/EpistocracyPanel';
import IdentityVotingPanel from '../components/shared/IdentityVotingPanel';
import CoalitionPanel from '../components/shared/CoalitionPanel';
import DuelModePanel from '../components/shared/DuelModePanel';
import DistrictMap from '../components/shared/DistrictMap';
import PrimarySimulator from '../components/shared/PrimarySimulator';
import HistoricalReplay from '../components/shared/HistoricalReplay';
import JuryTheoremPanel from '../components/shared/JuryTheoremPanel';
import AdaptiveVotingPanel from '../components/shared/AdaptiveVotingPanel';
import AbstentionPanel from '../components/shared/AbstentionPanel';
import STVPanel from '../components/shared/STVPanel';
import GerrymanderMap from '../components/shared/GerrymanderMap';
import MultiwinnerCompare from '../components/shared/MultiwinnerCompare';
import AffectivePolarizationPanel from '../components/shared/AffectivePolarizationPanel';
import CascadePanel from '../components/shared/CascadePanel';
import BehavioralBiasPanel from '../components/shared/BehavioralBiasPanel';
import LiquidDemocracyPanel from '../components/shared/LiquidDemocracyPanel';
import ConvictionVotingPanel from '../components/shared/ConvictionVotingPanel';
import NOTAPanel from '../components/shared/NOTAPanel';
import BallotComplexityPanel from '../components/shared/BallotComplexityPanel';
import ShyVoterPanel from '../components/shared/ShyVoterPanel';
import ElectoralFatiguePanel from '../components/shared/ElectoralFatiguePanel';
import ManipulationAnalysisPanel from '../components/shared/ManipulationAnalysisPanel';
import ChoiceOverloadPanel from '../components/shared/ChoiceOverloadPanel';
import DemographicTurnoutPanel from '../components/shared/DemographicTurnoutPanel';
import CompulsoryVotingPanel from '../components/shared/CompulsoryVotingPanel';
import DeliberationPanel from '../components/shared/DeliberationPanel';
import HotellingPanel from '../components/shared/HotellingPanel';
import PolarizationPanel from '../components/shared/PolarizationPanel';
import SortitionPanel from '../components/shared/SortitionPanel';
import PartyDynamicsPanel from '../components/shared/PartyDynamicsPanel';

const COLORS: Record<string, string> = {
  Green: '#007A33',
  Liberal: '#005CAB',
  Conservative: '#C8590A',
  Independent: '#6c757d',
};

// ── Results table ─────────────────────────────────────────────────────────────

const ResultsTab: React.FC<{ result: ElectionResult; t: (k: string) => string }> = ({
  result,
  t,
}) => {
  const hasBlank = result.config.blank_vote?.enabled;
  const rows = Object.entries(result.methods).sort(([a], [b]) => a.localeCompare(b));

  return (
    <div>
      {/* Summary badges */}
      <div className="flex gap-2 flex-wrap mb-3">
        <Badge variant="primary" className="inline-flex items-center gap-1">
          {t('electionLab.methodAgreement')}: {Math.round(result.inter_method_agreement * 100)}%
          <MetricTooltip metric="method_agreement" placement="bottom" />
        </Badge>
        {result.condorcet_winner && (
          <Badge variant="success">Condorcet: {result.condorcet_winner} ✓</Badge>
        )}
        {hasBlank && (
          <Badge variant="warning">
            {t('electionLab.blankRate')}: {Math.round(result.blank_rate * 100)}%
          </Badge>
        )}
      </div>

      <Table className="[&_th]:p-1 [&_td]:p-1 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_th]:border [&_td]:border">
        <thead className="table-light">
          <tr>
            <th>{t('common.method')}</th>
            <th>{t('electionLab.winner')}</th>
            {hasBlank && <th>{t('electionLab.winnerWithBlank')}</th>}
            <th className="flex items-center gap-1">
              {t('simulation.bayesianRegret')}
              <MetricTooltip metric="bayesian_regret" placement="bottom" />
            </th>
            <th>
              Condorcet ✓
              <MetricTooltip metric="condorcet_compliance" placement="bottom" />
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([method, md]) => {
            const isCondorcet = result.condorcet_winner && md.winner === result.condorcet_winner;
            return (
              <tr key={method}>
                <td className="font-semibold" style={{ fontSize: '0.82rem' }}>
                  {method}
                </td>
                <td>
                  {md.winner ? (
                    <Badge
                      style={{
                        background:
                          COLORS[
                            result.candidates.find((c) => c.name === md.winner)?.party ?? ''
                          ] ?? '#666',
                      }}
                    >
                      {md.winner}
                    </Badge>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                  {isCondorcet && ' ✓'}
                </td>
                {hasBlank && (
                  <td>
                    {md.winner_with_blank ? (
                      <Badge variant={md.blank_triggered ? 'warning' : 'secondary'}>
                        {md.winner_with_blank}
                      </Badge>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                    {md.blank_triggered && <span className="text-[#cc9a00] ms-1">⚠</span>}
                  </td>
                )}
                <td style={{ fontSize: '0.8rem' }}>{md.bayesian_regret?.toFixed(4) ?? '—'}</td>
                <td className="text-center">
                  {md.condorcet_consistent === true && <span style={{ color: '#007A33' }}>✓</span>}
                  {md.condorcet_consistent === false && <span style={{ color: '#B71C1C' }}>✗</span>}
                  {md.condorcet_consistent === null && (
                    <span className="text-muted-foreground">—</span>
                  )}
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
    const updated = config.candidates.map((c, i) => (i === idx ? { ...c, ...patch } : c));
    setConfig({ candidates: updated });
  };

  const addCandidate = () => {
    // Cap matches backend SINGLE_WINNER_CAP (8). Beyond this Kemeny-Young
    // exact becomes intractable (8! = 40320 permutations) and the engine
    // silently falls back to the KwikSort approximation — see backend.
    if (config.candidates.length >= 8) return;
    const names = ['Dave', 'Eve', 'Frank', 'Grace', 'Henry', 'Iris'];
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
              <CardBody className="p-2">
                <div className="flex items-center gap-2 mb-1">
                  <Control
                    size="sm"
                    value={c.name}
                    style={{ maxWidth: 90 }}
                    onChange={(e) => updateCandidate(i, { name: e.target.value })}
                  />
                  {config.candidates.length > 2 && (
                    <Button
                      variant="outline-danger"
                      size="sm"
                      style={{ padding: '1px 6px', fontSize: '0.7rem' }}
                      onClick={() => removeCandidate(i)}
                    >
                      ✕
                    </Button>
                  )}
                </div>
                <label className="mb-1 inline-block text-sm mb-0">
                  {t('electionLab.economy')}: {c.x.toFixed(2)}
                </label>
                <Range
                  min={-1}
                  max={1}
                  step={0.05}
                  value={c.x}
                  onChange={(e) => updateCandidate(i, { x: Number(e.target.value) })}
                />
                <label className="mb-1 inline-block text-sm mb-0">
                  {t('electionLab.social')}: {c.y.toFixed(2)}
                </label>
                <Range
                  min={-1}
                  max={1}
                  step={0.05}
                  value={c.y}
                  onChange={(e) => updateCandidate(i, { y: Number(e.target.value) })}
                />
              </CardBody>
            </Card>
          ))}
          {config.candidates.length < 6 && (
            <Button variant="outline-secondary" size="sm" className="w-full" onClick={addCandidate}>
              + {t('electionLab.addCandidate')}
            </Button>
          )}
        </Accordion.Body>
      </Accordion.Item>

      {/* Section 2 — Electorate */}
      <Accordion.Item eventKey="1">
        <Accordion.Header>{t('electionLab.sectionElectorate')}</Accordion.Header>
        <Accordion.Body className="p-2">
          <label className="mb-1 inline-block text-sm mb-0">
            {t('electionLab.numVoters')}: <strong>{config.num_voters}</strong>
          </label>
          <Range
            min={50}
            max={1000}
            step={50}
            value={config.num_voters}
            onChange={(e) => setConfig({ num_voters: Number(e.target.value) })}
          />

          <label className="mb-1 inline-block text-sm mb-1">{t('electionLab.ideology')}</label>
          <Select
            size="sm"
            value={config.ideology}
            className="mb-2"
            onChange={(e) => setConfig({ ideology: e.target.value })}
          >
            {['random', 'centrist', 'polarized', 'left_skewed', 'right_skewed'].map((v) => (
              <option key={v} value={v}>
                {t(`ideology.${v}`)}
              </option>
            ))}
          </Select>

          <label className="mb-1 inline-block text-sm mb-1">{t('electionLab.seed')}</label>
          <Control
            size="sm"
            type="number"
            value={config.seed}
            onChange={(e) => setConfig({ seed: Number(e.target.value) })}
          />
        </Accordion.Body>
      </Accordion.Item>

      {/* Section 3 — Campaign */}
      <Accordion.Item eventKey="2">
        <Accordion.Header>
          {t('electionLab.sectionCampaign')}
          {config.campaign.enabled && (
            <Badge variant="primary" className="ms-2" style={{ fontSize: '0.6rem' }}>
              ON
            </Badge>
          )}
        </Accordion.Header>
        <Accordion.Body className="p-2">
          <Check
            type="switch"
            id="campaign-enabled"
            label={<span className="text-sm">{t('electionLab.enabled')}</span>}
            checked={config.campaign.enabled}
            onChange={(e) => setConfigDeep('campaign.enabled', e.target.checked)}
            className="mb-2"
          />
          {config.campaign.enabled && (
            <>
              <label className="mb-1 inline-block text-sm mb-0">
                {t('electionLab.numDays')}: <strong>{config.campaign.num_days}</strong>
              </label>
              <Range
                min={7}
                max={60}
                step={1}
                value={config.campaign.num_days}
                onChange={(e) => setConfigDeep('campaign.num_days', Number(e.target.value))}
              />
              <label className="mb-1 inline-block text-sm mb-0">
                {t('electionLab.pollingEffect')}:{' '}
                <strong>{config.campaign.polling_effect.toFixed(2)}</strong>
              </label>
              <Range
                min={0}
                max={1}
                step={0.05}
                value={config.campaign.polling_effect}
                onChange={(e) => setConfigDeep('campaign.polling_effect', Number(e.target.value))}
              />
            </>
          )}
        </Accordion.Body>
      </Accordion.Item>

      {/* Section 4 — Blank vote */}
      <Accordion.Item eventKey="3">
        <Accordion.Header>
          {t('electionLab.sectionBlank')}
          {config.blank_vote.enabled && (
            <Badge variant="warning" className="ms-2" style={{ fontSize: '0.6rem' }}>
              ON
            </Badge>
          )}
        </Accordion.Header>
        <Accordion.Body className="p-2">
          <Check
            type="switch"
            id="blank-enabled"
            label={<span className="text-sm">{t('electionLab.enabled')}</span>}
            checked={config.blank_vote.enabled}
            onChange={(e) => setConfigDeep('blank_vote.enabled', e.target.checked)}
            className="mb-2"
          />
          {config.blank_vote.enabled && (
            <>
              <label className="mb-1 inline-block text-sm mb-1">{t('electionLab.blankRule')}</label>
              <Select
                size="sm"
                value={config.blank_vote.rule}
                className="mb-3"
                onChange={(e) => setConfigDeep('blank_vote.rule', e.target.value)}
              >
                <option value="symbolic">Symbolique</option>
                <option value="competitive">Compétitif</option>
                <option value="threshold_30">Seuil 30%</option>
              </Select>

              <div className="border border-border rounded p-2" style={{ fontSize: '0.78rem' }}>
                <strong>{t('electionLab.contagion')}</strong>
                <Check
                  type="switch"
                  id="contagion-enabled"
                  label={<span className="text-sm">{t('electionLab.enabled')}</span>}
                  checked={config.blank_vote.contagion.enabled}
                  onChange={(e) => setConfigDeep('blank_vote.contagion.enabled', e.target.checked)}
                  className="mt-1 mb-1"
                />
                {config.blank_vote.contagion.enabled && (
                  <>
                    <label className="mb-1 inline-block text-sm mb-0">
                      β (contagion): {config.blank_vote.contagion.beta.toFixed(2)}
                    </label>
                    <Range
                      min={0}
                      max={1}
                      step={0.05}
                      value={config.blank_vote.contagion.beta}
                      onChange={(e) =>
                        setConfigDeep('blank_vote.contagion.beta', Number(e.target.value))
                      }
                    />
                    <label className="mb-1 inline-block text-sm mb-0">
                      γ (récupération): {config.blank_vote.contagion.gamma.toFixed(2)}
                    </label>
                    <Range
                      min={0}
                      max={1}
                      step={0.05}
                      value={config.blank_vote.contagion.gamma}
                      onChange={(e) =>
                        setConfigDeep('blank_vote.contagion.gamma', Number(e.target.value))
                      }
                    />
                    <label className="mb-1 inline-block text-sm mb-1">Réseau</label>
                    <Select
                      size="sm"
                      value={config.blank_vote.contagion.network}
                      onChange={(e) =>
                        setConfigDeep('blank_vote.contagion.network', e.target.value)
                      }
                    >
                      <option value="random">Aléatoire</option>
                      <option value="watts_strogatz">Petit monde</option>
                      <option value="block">Blocs</option>
                    </Select>
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
          {config.information_model.enabled && (
            <Badge variant="info" className="ms-2" style={{ fontSize: '0.6rem' }}>
              ON
            </Badge>
          )}
        </Accordion.Header>
        <Accordion.Body className="p-2">
          <Check
            type="switch"
            id="info-enabled"
            label={<span className="text-sm">{t('electionLab.enabled')}</span>}
            checked={config.information_model.enabled}
            onChange={(e) => setConfigDeep('information_model.enabled', e.target.checked)}
            className="mb-2"
          />
          {config.information_model.enabled &&
            config.candidates.map((c) => (
              <div key={c.name} className="mb-2">
                <label className="mb-1 inline-block text-sm mb-0">
                  {t('electionLab.mediaBias')} {c.name}:
                  <strong className="ms-1">
                    {(config.information_model.media_bias[c.name] ?? 0).toFixed(2)}
                  </strong>
                </label>
                <Range
                  min={-1}
                  max={1}
                  step={0.1}
                  value={config.information_model.media_bias[c.name] ?? 0}
                  onChange={(e) =>
                    setConfigDeep(`information_model.media_bias.${c.name}`, Number(e.target.value))
                  }
                />
              </div>
            ))}
        </Accordion.Body>
      </Accordion.Item>
    </Accordion>
  );
};

// ── Main page ─────────────────────────────────────────────────────────────────

// ── Main page ─────────────────────────────────────────────────────────────────

const ElectionLabPage: React.FC = () => {
  const { t } = useTranslation();
  useMetaTags({
    title: 'Election Lab — Vote Lab',
    description:
      "Simulation unifiée : combinez campagne, vote blanc, modèle d'information et comparez toutes les méthodes de vote sur une même élection.",
  });

  const { config, applyScenario, resetConfig, scenarioNames, scenarioMeta } = useElection();

  const [result, setResult] = useState<ElectionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [duelMode, setDuelMode] = useState(false);
  const [duelMethA, setDuelMethA] = useState('plurality');
  const [duelMethB, setDuelMethB] = useState('schulze');
  // Initialise activeTab from `?tab=` query param if present, so deep links
  // from TheoryPage (or any "open in Lab" CTA) land on the correct tab.
  const [activeTab, setActiveTab] = useState(() => {
    try {
      const p = new URLSearchParams(window.location.search).get('tab');
      return p ?? 'results';
    } catch {
      return 'results';
    }
  });
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < 768);

  React.useEffect(() => {
    const mq = window.matchMedia('(max-width: 767px)');
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);
  const runIdRef = useRef(0);

  // ── Onboarding tour: auto-run on first visit, or when ?labTour=1 ────────
  const [tourRun, setTourRun] = useState(false);
  const startTour = useCallback(() => {
    try {
      localStorage.removeItem(LAB_TOUR_LS_KEY);
    } catch {
      /* */
    }
    setTourRun(false);
    setTimeout(() => setTourRun(true), 100);
  }, []);
  React.useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const forced = params.get('labTour') === '1';
    let completed = false;
    try {
      completed = localStorage.getItem(LAB_TOUR_LS_KEY) === 'true';
    } catch {
      /* */
    }
    if (forced || !completed) {
      // Wait long enough for the first simulation to render so target
      // elements (data-tour="lab-central" etc.) exist in the DOM.
      const id = setTimeout(() => setTourRun(true), 1200);
      return () => clearTimeout(id);
    }
  }, []);

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
    candidates: candidateNames,
    num_voters: config.num_voters,
    ideology_distribution: config.ideology,
    seed: config.seed,
  };

  return (
    <PageContainer variant="full">
      <LabOnboardingTour run={tourRun} onFinish={() => setTourRun(false)} />
      <ModelAssumptionsBanner />
      {/* Header */}
      <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
        <div>
          <h2 className="mb-0 font-bold flex items-center gap-2 flex-wrap">
            🔬 {t('electionLab.title')}
            {scenarioMeta && (
              <Badge variant="primary" style={{ fontSize: '0.6rem', fontWeight: 600 }}>
                🗳️ {scenarioMeta.name}
              </Badge>
            )}
          </h2>
          {scenarioMeta ? (
            <div className="flex items-center gap-2 flex-wrap mt-1">
              <Badge variant="secondary" style={{ fontSize: '0.62rem' }}>
                {scenarioMeta.phenomenon}
              </Badge>
              <span className="text-muted-foreground" style={{ fontSize: '0.8rem' }}>
                {scenarioMeta.description}
              </span>
            </div>
          ) : (
            <p className="text-muted-foreground mb-0" style={{ fontSize: '0.85rem' }}>
              {t('electionLab.subtitle')}
            </p>
          )}
        </div>
        <div className="flex gap-2 flex-wrap">
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
              <Dropdown.Item onClick={resetConfig} className="text-muted-foreground">
                ↺ {t('electionLab.reset')}
              </Dropdown.Item>
            </Dropdown.Menu>
          </Dropdown>
          <ScenarioIO />
          <Button
            variant="outline-secondary"
            size="sm"
            onClick={startTour}
            data-testid="lab-tour-replay"
            title={t('labTour.replayTitle')}
          >
            🎓 {t('labTour.replay')}
          </Button>
        </div>
      </div>

      <Row className="g-3">
        {/* ── Parameter panel ── */}
        <Col xs={12} md={4} lg={3}>
          <ParameterPanel t={t} />

          <div className="mt-3 flex items-center gap-2">
            <Button variant="primary" className="grow" onClick={runSimulation} disabled={loading}>
              {loading ? (
                <>
                  <Spinner size="sm" className="me-2" />
                  {t('electionLab.simulating')}
                </>
              ) : (
                `🗳️ ${result ? t('electionLab.resimulate') : t('electionLab.simulate')}`
              )}
            </Button>
            <LiveBadge loading={loading && !!result} />
          </div>

          {/* Active modules badges */}
          <div className="flex flex-wrap gap-1 mt-2" style={{ fontSize: '0.72rem' }}>
            {config.campaign.enabled && (
              <Badge variant="primary">⏱ {t('electionLab.sectionCampaign')}</Badge>
            )}
            {config.blank_vote.enabled && (
              <Badge variant="warning">□ {t('electionLab.sectionBlank')}</Badge>
            )}
            {config.blank_vote.contagion.enabled && (
              <Badge variant="danger">🦠 {t('electionLab.contagion')}</Badge>
            )}
            {config.information_model.enabled && (
              <Badge variant="info">📡 {t('electionLab.sectionInfo')}</Badge>
            )}
          </div>
        </Col>

        {/* ── Results panel ── */}
        <Col xs={12} md={8} lg={9}>
          {error && <Alert variant="danger">{error}</Alert>}

          {!result && !loading && <Alert variant="info">{t('electionLab.noResults')}</Alert>}

          {loading && !result && (
            <div className="text-center py-5">
              <Spinner className="mb-2" />
              <div className="text-muted-foreground text-sm">{t('electionLab.simulating')}</div>
            </div>
          )}

          {result && (
            <div style={{ opacity: loading ? 0.65 : 1, transition: 'opacity 0.25s' }}>
              {/* ── Persistent central view (always visible) ── */}
              <div data-tour="lab-central">
                <LabCentralView result={result} loading={loading} />
              </div>

              {/* Mode Duel toggle */}
              <div className="flex justify-end mb-2">
                <Button
                  size="sm"
                  variant={duelMode ? 'danger' : 'outline-secondary'}
                  onClick={() => setDuelMode(!duelMode)}
                  data-testid="duel-toggle"
                  style={{ fontSize: '0.78rem' }}
                >
                  ⚔ {duelMode ? t('duel.exitDuel') : t('duel.enterDuel')}
                </Button>
              </div>

              {/* ── Adaptive tab navigation ── */}
              {(() => {
                const TABS = [
                  // ═══ VOIR — analyses qui n'altèrent pas le résultat ═══
                  // Note: tab 'map' removed — its content is now persistent in LabCentralView
                  // above the tabs (toggle layers: points/heatmap/voronoi/median).
                  {
                    key: 'results',
                    icon: '📊',
                    label: t('electionLab.tabResults'),
                    group: 'see' as const,
                  },
                  {
                    key: 'animation',
                    icon: '▶',
                    label: t('electionLab.tabAnimation'),
                    group: 'see' as const,
                  },
                  {
                    key: 'montecarlo',
                    icon: '🎲',
                    label: t('electionLab.tabMonteCarlo'),
                    group: 'see' as const,
                  },
                  {
                    key: 'manipulability',
                    icon: '⚡',
                    label: t('electionLab.tabManipulability'),
                    group: 'see' as const,
                  },
                  {
                    key: 'pipeline',
                    icon: '🎬',
                    label: t('electionLab.tabPipeline'),
                    group: 'see' as const,
                  },
                  {
                    key: 'combined-effects',
                    icon: '🔬',
                    label: t('electionLab.tabCombinedEffects'),
                    group: 'see' as const,
                  },
                  {
                    key: 'hotelling',
                    icon: '⚖️',
                    label: t('electionLab.tabHotelling'),
                    group: 'see' as const,
                  },
                  {
                    key: 'polarization',
                    icon: '📊',
                    label: t('electionLab.tabPolarization'),
                    group: 'see' as const,
                  },
                  {
                    key: 'lab-collective-will',
                    icon: '🌊',
                    label: t('electionLab.tabLabCollectiveWill'),
                    group: 'see' as const,
                  },
                  {
                    key: 'lab-assumptions',
                    icon: '🔬',
                    label: t('electionLab.tabLabAssumptions'),
                    group: 'see' as const,
                  },

                  // ═══ PERTURBER — effets qui modifient le résultat de l'élection ═══
                  {
                    key: 'campaign-sensitivity',
                    icon: '📈',
                    label: t('electionLab.tabCampaignSensitivity'),
                    group: 'perturb' as const,
                  },
                  {
                    key: 'blank-divergence',
                    icon: '⬜',
                    label: t('electionLab.tabBlankDivergence'),
                    group: 'perturb' as const,
                  },
                  {
                    key: 'abstention',
                    icon: '📉',
                    label: t('electionLab.tabAbstention'),
                    group: 'perturb' as const,
                  },
                  {
                    key: 'compulsory',
                    icon: '⚖️',
                    label: t('electionLab.tabCompulsory'),
                    group: 'perturb' as const,
                  },
                  {
                    key: 'demographic',
                    icon: '👥',
                    label: t('electionLab.tabDemographic'),
                    group: 'perturb' as const,
                  },
                  {
                    key: 'cascade',
                    icon: '📡',
                    label: t('electionLab.tabCascade'),
                    group: 'perturb' as const,
                  },
                  {
                    key: 'behavioral',
                    icon: '🧠',
                    label: t('electionLab.tabBehavioral'),
                    group: 'perturb' as const,
                  },
                  {
                    key: 'affective',
                    icon: '💔',
                    label: t('electionLab.tabAffective'),
                    group: 'perturb' as const,
                  },
                  {
                    key: 'manipulation',
                    icon: '🕵',
                    label: t('electionLab.tabManipulation'),
                    group: 'perturb' as const,
                  },
                  {
                    key: 'adaptive',
                    icon: '⚙',
                    label: t('electionLab.tabAdaptive'),
                    group: 'perturb' as const,
                  },
                  {
                    key: 'shyvoter',
                    icon: '🤫',
                    label: t('electionLab.tabShyVoter'),
                    group: 'perturb' as const,
                  },
                  {
                    key: 'fatigue',
                    icon: '😴',
                    label: t('electionLab.tabFatigue'),
                    group: 'perturb' as const,
                  },
                  {
                    key: 'overload',
                    icon: '🤯',
                    label: t('electionLab.tabOverload'),
                    group: 'perturb' as const,
                  },
                  {
                    key: 'deliberation',
                    icon: '🗣',
                    label: t('electionLab.tabDeliberation'),
                    group: 'perturb' as const,
                  },
                  {
                    key: 'nota',
                    icon: '🚫',
                    label: t('electionLab.tabNota'),
                    group: 'perturb' as const,
                  },
                  {
                    key: 'ballot',
                    icon: '📋',
                    label: t('electionLab.tabBallot'),
                    group: 'perturb' as const,
                  },
                  {
                    key: 'lab-epistocracy',
                    icon: '🎓',
                    label: t('electionLab.tabLabEpistocracy'),
                    group: 'perturb' as const,
                  },
                  {
                    key: 'lab-identity',
                    icon: '🏳',
                    label: t('electionLab.tabLabIdentity'),
                    group: 'perturb' as const,
                  },

                  // ═══ VARIANTES — autres types d'élections (cas particuliers) ═══
                  {
                    key: 'coalition',
                    icon: '🏛',
                    label: t('electionLab.tabCoalition'),
                    group: 'variant' as const,
                  },
                  {
                    key: 'districts',
                    icon: '🗺',
                    label: t('electionLab.tabDistricts'),
                    group: 'variant' as const,
                  },
                  {
                    key: 'gerrymander',
                    icon: '🗺',
                    label: t('electionLab.tabGerrymander'),
                    group: 'variant' as const,
                  },
                  {
                    key: 'primary',
                    icon: '🗳',
                    label: t('electionLab.tabPrimary'),
                    group: 'variant' as const,
                  },
                  {
                    key: 'replay',
                    icon: '📺',
                    label: t('electionLab.tabReplay'),
                    group: 'variant' as const,
                  },
                  {
                    key: 'jury',
                    icon: '⚖️',
                    label: t('electionLab.tabJury'),
                    group: 'variant' as const,
                  },
                  {
                    key: 'stv',
                    icon: '🔄',
                    label: t('electionLab.tabSTV'),
                    group: 'variant' as const,
                  },
                  {
                    key: 'multiwinner',
                    icon: '🏛',
                    label: t('electionLab.tabMultiwinner'),
                    group: 'variant' as const,
                  },
                  {
                    key: 'liquid',
                    icon: '💧',
                    label: t('electionLab.tabLiquid'),
                    group: 'variant' as const,
                  },
                  {
                    key: 'conviction',
                    icon: '⛓',
                    label: t('electionLab.tabConviction'),
                    group: 'variant' as const,
                  },
                  {
                    key: 'party-dynamics',
                    icon: '📊',
                    label: t('electionLab.tabPartyDynamics'),
                    group: 'variant' as const,
                  },
                  {
                    key: 'sortition',
                    icon: '🎲',
                    label: t('electionLab.tabSortition'),
                    group: 'variant' as const,
                  },
                ];

                // ── Group metadata (label + color dot) ──────────────────────
                const GROUP_META = {
                  see: { label: t('electionLab.groupSee'), color: '#0d6efd' }, // blue
                  perturb: { label: t('electionLab.groupPerturb'), color: '#fd7e14' }, // orange
                  variant: { label: t('electionLab.groupVariant'), color: '#6f42c1' }, // purple
                };
                type TabGroup = keyof typeof GROUP_META;

                const tabContent: Record<string, React.ReactNode> = {
                  results: duelMode ? (
                    <DuelModePanel
                      result={result}
                      methodA={duelMethA}
                      methodB={duelMethB}
                      onMethodAChange={setDuelMethA}
                      onMethodBChange={setDuelMethB}
                    />
                  ) : (
                    <>
                      <ResultsTab result={result} t={t} />
                      <ElectionInsightPanel result={result} />
                      <HistoricalReferencePanel result={result} />
                    </>
                  ),
                  // 'map' removed — see LabCentralView for the persistent map.
                  animation: (
                    <VoteStepAnimator
                      defaultCandidates={candidateNames}
                      candidateConfigs={config.candidates}
                      numVoters={config.num_voters}
                      ideology={config.ideology}
                      seed={config.seed}
                    />
                  ),
                  montecarlo: <MonteCarloResults baseParams={baseParams} />,
                  manipulability: <ManipulabilityChart baseParams={baseParams} />,
                  'blank-divergence': <BlankVoteDivergencePanel />,
                  'campaign-sensitivity': <CampaignSensitivityPanel />,
                  pipeline: <ElectionPipelineAnimator />,
                  'combined-effects': <CombinedEffectsMatrix />,
                  coalition: <CoalitionPanel />,
                  districts: <DistrictMap />,
                  primary: <PrimarySimulator />,
                  replay: <HistoricalReplay />,
                  jury: <JuryTheoremPanel />,
                  adaptive: <AdaptiveVotingPanel />,
                  abstention: <AbstentionPanel />,
                  stv: <STVPanel />,
                  gerrymander: <GerrymanderMap />,
                  multiwinner: <MultiwinnerCompare />,
                  affective: <AffectivePolarizationPanel />,
                  hotelling: <HotellingPanel />,
                  polarization: <PolarizationPanel />,
                  cascade: <CascadePanel />,
                  behavioral: <BehavioralBiasPanel />,
                  liquid: <LiquidDemocracyPanel />,
                  conviction: <ConvictionVotingPanel />,
                  'party-dynamics': <PartyDynamicsPanel />,
                  sortition: <SortitionPanel />,
                  nota: <NOTAPanel />,
                  ballot: <BallotComplexityPanel />,
                  shyvoter: <ShyVoterPanel />,
                  fatigue: <ElectoralFatiguePanel />,
                  overload: <ChoiceOverloadPanel />,
                  manipulation: <ManipulationAnalysisPanel />,
                  demographic: <DemographicTurnoutPanel />,
                  compulsory: <CompulsoryVotingPanel />,
                  deliberation: <DeliberationPanel />,
                  // ── Théorie & limites — utilisent la config ElectionLab ─────────
                  'lab-collective-will': (
                    <CollectiveWillPanel
                      labMode
                      labCandidates={config.candidates}
                      labNumVoters={config.num_voters}
                      labSeed={config.seed}
                      labIdeology={config.ideology}
                    />
                  ),
                  'lab-assumptions': (
                    <AssumptionTesterPanel
                      labMode
                      labCandidates={config.candidates}
                      labNumVoters={config.num_voters}
                      labSeed={config.seed}
                      labIdeology={config.ideology}
                    />
                  ),
                  'lab-epistocracy': (
                    <EpistocracyPanel
                      labMode
                      labCandidates={config.candidates}
                      labNumVoters={config.num_voters}
                      labSeed={config.seed}
                    />
                  ),
                  'lab-identity': (
                    <IdentityVotingPanel
                      labMode
                      labCandidates={config.candidates}
                      labNumVoters={config.num_voters}
                      labSeed={config.seed}
                    />
                  ),
                };

                const currentIdx = TABS.findIndex((tab) => tab.key === activeTab);

                if (isMobile) {
                  // Group tabs for the optgroup-based mobile select
                  const tabsByGroup: Record<TabGroup, typeof TABS> = {
                    see: [],
                    perturb: [],
                    variant: [],
                  };
                  TABS.forEach((tab) => tabsByGroup[tab.group].push(tab));
                  return (
                    <div data-testid="mobile-tab-nav">
                      <Select
                        size="sm"
                        value={activeTab}
                        onChange={(e) => setActiveTab(e.target.value)}
                        className="mb-3"
                        style={{ fontSize: '0.85rem' }}
                        aria-label={t('electionLab.tabSelect')}
                        data-testid="tab-select"
                      >
                        {(Object.keys(GROUP_META) as TabGroup[]).map((grp) => (
                          <optgroup key={grp} label={GROUP_META[grp].label}>
                            {tabsByGroup[grp].map((tab) => (
                              <option key={tab.key} value={tab.key}>
                                {tab.icon} {tab.label}
                              </option>
                            ))}
                          </optgroup>
                        ))}
                      </Select>
                      <div className="flex justify-between items-center mb-2">
                        <Button
                          variant="outline-secondary"
                          size="sm"
                          disabled={currentIdx <= 0}
                          onClick={() => setActiveTab(TABS[currentIdx - 1]?.key ?? activeTab)}
                          aria-label={t('electionLab.prevTabAria')}
                        >
                          ‹
                        </Button>
                        <span className="text-muted-foreground" style={{ fontSize: '0.72rem' }}>
                          {currentIdx + 1} / {TABS.length}
                        </span>
                        <Button
                          variant="outline-secondary"
                          size="sm"
                          disabled={currentIdx >= TABS.length - 1}
                          onClick={() => setActiveTab(TABS[currentIdx + 1]?.key ?? activeTab)}
                          aria-label={t('electionLab.nextTabAria')}
                        >
                          ›
                        </Button>
                      </div>
                      {tabContent[activeTab]}
                    </div>
                  );
                }

                return (
                  <>
                    {/* ── Group legend ─────────────────────────────────────── */}
                    <div
                      className="flex gap-3 mb-2 flex-wrap"
                      style={{ fontSize: '0.72rem' }}
                      data-testid="tab-group-legend"
                    >
                      {(Object.keys(GROUP_META) as TabGroup[]).map((grp) => (
                        <span key={grp} className="flex items-center gap-1">
                          <span
                            style={{
                              display: 'inline-block',
                              width: 8,
                              height: 8,
                              borderRadius: '50%',
                              background: GROUP_META[grp].color,
                            }}
                          />
                          <span className="text-muted-foreground">{GROUP_META[grp].label}</span>
                        </span>
                      ))}
                    </div>
                    <Tabs
                      activeKey={activeTab}
                      onSelect={(k) => k && setActiveTab(k)}
                      className="mb-3 flex-nowrap overflow-auto"
                      data-testid="desktop-tab-nav"
                      data-tour="lab-tabs"
                      style={{ flexWrap: 'nowrap' }}
                    >
                      {TABS.map((tab) => (
                        <Tab
                          key={tab.key}
                          eventKey={tab.key}
                          title={
                            <span
                              style={{
                                whiteSpace: 'nowrap',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: 5,
                              }}
                              data-tour={
                                tab.key === 'animation'
                                  ? 'lab-animation-tab'
                                  : tab.key === 'abstention'
                                    ? 'lab-perturb-tab'
                                    : undefined
                              }
                            >
                              <span
                                style={{
                                  display: 'inline-block',
                                  width: 6,
                                  height: 6,
                                  borderRadius: '50%',
                                  background: GROUP_META[tab.group].color,
                                  flexShrink: 0,
                                }}
                                aria-hidden="true"
                              />
                              {tab.icon} {tab.label}
                            </span>
                          }
                        >
                          {activeTab === tab.key && tabContent[tab.key]}
                        </Tab>
                      ))}
                    </Tabs>
                  </>
                );
              })()}
            </div>
          )}
        </Col>
      </Row>
    </PageContainer>
  );
};

// Pinned perturbations + animation-step broadcast now live in useLabStore
// (Phase 5.5) — no providers needed; the store is shared module-level state.

export default ElectionLabPage;
