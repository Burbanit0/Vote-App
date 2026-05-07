import React, { useMemo, useState } from 'react';
import { Alert, Button, Card, Col, Container, Form, Row, Spinner, Tab, Tabs } from 'react-bootstrap';
import CondorcetMatrix from '../components/Simulation/CondorcetMatrix';
import ArrowCriteriaMatrix from '../components/Simulation/ArrowCriteriaMatrix';
import BandwagonAnalysis from '../components/Simulation/BandwagonAnalysis';
import MultiwinnerAnalysis from '../components/Simulation/MultiwinnerAnalysis';
import MonteCarloResults from '../components/Simulation/MonteCarloResults';
import WinnerMatrixTab from '../components/Simulation/WinnerMatrixTab';
import MetricsTab from '../components/Simulation/MetricsTab';
import StrategicImpactTab from '../components/Simulation/StrategicImpactTab';
import SensitivityTab from '../components/Simulation/SensitivityTab';
import RealElectionsTab from '../components/Simulation/RealElectionsTab';
import ScenarioModals from '../components/Simulation/ScenarioModals';
import ScenarioConfigRow from '../components/Simulation/ScenarioConfigRow';
import {
  CANDIDATE_PALETTE,
  ScenarioConfig,
  STRATEGIC_PERCENTAGES,
} from '../components/Simulation/simulationConstants';
import {
  ArrowCriteriaResult,
  CondorcetMatrixResult,
  ScenarioDetail,
  ScenarioSummary,
  SimulationCompareResult,
  StrategicImpactPoint,
} from '../types';
import {
  getArrowCriteria,
  getCondorcetMatrix,
  runComparisonSimulation,
  runStrategicImpactAnalysis,
} from '../services/simulationCompareApi';
import { deleteScenario, getScenario, listScenarios, saveScenario } from '../services/scenariosApi';

const SimulationComparePage: React.FC = () => {
  // ── Scenario config ──
  const [numSimulations, setNumSimulations] = useState(10);
  const [configA, setConfigA] = useState<ScenarioConfig>({
    numVoters: 500,
    candidateInput: 'Alice, Bob, Charlie',
    ideology_distribution: 'random',
  });
  const [scenarioCount, setScenarioCount] = useState<1 | 2>(1);
  const [configB, setConfigB] = useState<ScenarioConfig>({
    numVoters: 500,
    candidateInput: 'Alice, Bob, Charlie, Carol',
    ideology_distribution: 'random',
  });

  // ── Results ──
  const [comparisonResults, setComparisonResults] = useState<SimulationCompareResult[]>([]);
  const [strategicData, setStrategicData] = useState<StrategicImpactPoint[]>([]);
  const [condorcetData, setCondorcetData] = useState<CondorcetMatrixResult | null>(null);
  const [arrowData, setArrowData] = useState<ArrowCriteriaResult | null>(null);
  const [resultsB, setResultsB] = useState<SimulationCompareResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ── Save / Load modal state ──
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [saveName, setSaveName] = useState('');
  const [saving, setSaving] = useState(false);
  const [showLoadModal, setShowLoadModal] = useState(false);
  const [scenarioList, setScenarioList] = useState<ScenarioSummary[]>([]);
  const [loadingList, setLoadingList] = useState(false);

  // ── Derived ──
  const candidateNamesA = useMemo(
    () => configA.candidateInput.split(',').map((s) => s.trim()).filter(Boolean),
    [configA.candidateInput]
  );
  const candidateNamesB = useMemo(
    () => configB.candidateInput.split(',').map((s) => s.trim()).filter(Boolean),
    [configB.candidateInput]
  );
  const candidateColorMap = useMemo(() => {
    const names = new Set<string>();
    [...comparisonResults, ...(resultsB ?? [])].forEach((r) =>
      Object.values(r.methods).forEach((m) => { if (m.winner) names.add(m.winner); })
    );
    return Object.fromEntries(
      [...names].map((name, i) => [name, CANDIDATE_PALETTE[i % CANDIDATE_PALETTE.length]])
    );
  }, [comparisonResults, resultsB]);
  const allMethodNames = useMemo(
    () => (comparisonResults.length > 0 ? Object.keys(comparisonResults[0].methods) : []),
    [comparisonResults]
  );

  // ── Run analysis ──
  const runAnalysis = async () => {
    if (candidateNamesA.length < 2) {
      setError('Scenario A needs at least 2 candidate names.');
      return;
    }
    if (scenarioCount === 2 && candidateNamesB.length < 2) {
      setError('Scenario B needs at least 2 candidate names.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const paramsA = {
        num_voters: configA.numVoters,
        candidates: candidateNamesA,
        ideology_distribution: configA.ideology_distribution,
      };
      const [simResultsA, strategicResults, condorcetResult, arrowResult, simResultsB] =
        await Promise.all([
          Promise.all(Array.from({ length: numSimulations }, () => runComparisonSimulation(paramsA))),
          runStrategicImpactAnalysis({ ...paramsA, strategic_percentages: STRATEGIC_PERCENTAGES }),
          getCondorcetMatrix(paramsA),
          getArrowCriteria(paramsA),
          scenarioCount === 2
            ? Promise.all(
                Array.from({ length: numSimulations }, () =>
                  runComparisonSimulation({
                    num_voters: configB.numVoters,
                    candidates: candidateNamesB,
                    ideology_distribution: configB.ideology_distribution,
                  })
                )
              )
            : Promise.resolve(null),
        ]);
      setComparisonResults(simResultsA);
      setStrategicData(strategicResults);
      setCondorcetData(condorcetResult);
      setArrowData(arrowResult);
      setResultsB(simResultsB);
    } catch {
      setError('Analysis failed. Make sure the backend is running and the endpoints exist.');
    } finally {
      setLoading(false);
    }
  };

  // ── Export ──
  const exportDate = new Date().toISOString().slice(0, 10);

  const exportJSON = () => {
    const blob = new Blob(
      [JSON.stringify({ comparisonResults, strategicData }, null, 2)],
      { type: 'application/json' }
    );
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `simulation_results_${exportDate}.json`;
    a.click();
  };

  const exportCSV = () => {
    const header = 'simulation_id,method,winner,bayesian_regret,majority_satisfaction,strategic_vulnerability,condorcet_consistent\n';
    const rows = comparisonResults.flatMap((r, idx) =>
      Object.entries(r.methods).map(([method, m]) =>
        [idx + 1, method, m.winner ?? '', m.bayesian_regret ?? '', m.majority_satisfaction ?? '', m.strategic_vulnerability ?? '', m.condorcet_consistent ?? ''].join(',')
      )
    );
    const blob = new Blob([header + rows.join('\n')], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `simulation_results_${exportDate}.csv`;
    a.click();
  };

  // ── Scenario persistence ──
  const handleSave = async () => {
    if (!saveName.trim()) return;
    setSaving(true);
    try {
      await saveScenario(
        saveName.trim(),
        { numSimulations, configA, configB, scenarioCount },
        { comparisonResults, strategicData, condorcetData, resultsB }
      );
      setShowSaveModal(false);
      setSaveName('');
    } finally {
      setSaving(false);
    }
  };

  const handleOpenLoadModal = async () => {
    setShowLoadModal(true);
    setLoadingList(true);
    try {
      setScenarioList(await listScenarios());
    } finally {
      setLoadingList(false);
    }
  };

  const handleLoad = async (scenario: ScenarioDetail) => {
    const cfg = scenario.config as any;
    const res = scenario.results as any;
    if (cfg) {
      if (cfg.numSimulations != null) setNumSimulations(cfg.numSimulations);
      if (cfg.configA) setConfigA(cfg.configA);
      if (cfg.configB) setConfigB(cfg.configB);
      if (cfg.scenarioCount) setScenarioCount(cfg.scenarioCount);
    }
    if (res) {
      if (res.comparisonResults) setComparisonResults(res.comparisonResults);
      if (res.strategicData) setStrategicData(res.strategicData);
      if ('condorcetData' in res) setCondorcetData(res.condorcetData);
      if ('resultsB' in res) setResultsB(res.resultsB);
    }
    setShowLoadModal(false);
  };

  const handleDelete = async (id: number) => {
    await deleteScenario(id);
    setScenarioList((prev) => prev.filter((s) => s.id !== id));
  };

  const hasResults = comparisonResults.length > 0;
  const baseParamsA = { num_voters: configA.numVoters, candidates: candidateNamesA, ideology_distribution: configA.ideology_distribution };

  return (
    <Container className="py-4">
      <h2 className="mb-1">Comparative Voting Methods Analysis</h2>
      <p className="text-muted mb-3">
        Run multiple simulations on the same population and compare how each voting method
        performs. Add a second scenario to study the spoiler effect or IIA violations.
      </p>

      <div className="d-flex gap-2 mb-4">
        <Button variant="outline-secondary" size="sm" onClick={handleOpenLoadModal}>
          📂 Load scenario
        </Button>
        {hasResults && (
          <>
            <Button variant="outline-success" size="sm" onClick={() => { setSaveName(''); setShowSaveModal(true); }}>
              💾 Save
            </Button>
            <Button variant="outline-primary" size="sm" onClick={exportJSON}>⬇ JSON</Button>
            <Button variant="outline-primary" size="sm" onClick={exportCSV}>⬇ CSV</Button>
          </>
        )}
      </div>

      {/* ── Configuration ── */}
      <Card className="mb-4">
        <Card.Header className="d-flex align-items-center justify-content-between">
          <strong>Configuration</strong>
          {scenarioCount === 1 ? (
            <Button size="sm" variant="outline-secondary" onClick={() => setScenarioCount(2)}>
              + Add scenario B
            </Button>
          ) : (
            <Button size="sm" variant="outline-danger" onClick={() => { setScenarioCount(1); setResultsB(null); }}>
              − Remove scenario B
            </Button>
          )}
        </Card.Header>
        <Card.Body>
          <Row className="g-3 align-items-end mb-3">
            <Col md={4}>
              <Form.Label>
                Simulations per scenario: <strong>{numSimulations}</strong>
              </Form.Label>
              <Form.Range min={5} max={20} value={numSimulations} onChange={(e) => setNumSimulations(Number(e.target.value))} />
            </Col>
            <Col md={2}>
              <Button variant="primary" className="w-100" onClick={runAnalysis} disabled={loading}>
                {loading ? <><Spinner size="sm" className="me-2" />Running…</> : 'Run Analysis'}
              </Button>
            </Col>
          </Row>
          {scenarioCount === 1 ? (
            <ScenarioConfigRow config={configA} onChange={(p) => setConfigA((c) => ({ ...c, ...p }))} />
          ) : (
            <Row className="g-3">
              <Col md={6}>
                <ScenarioConfigRow config={configA} onChange={(p) => setConfigA((c) => ({ ...c, ...p }))} label="Scenario A" />
              </Col>
              <Col md={6}>
                <ScenarioConfigRow config={configB} onChange={(p) => setConfigB((c) => ({ ...c, ...p }))} label="Scenario B" />
              </Col>
            </Row>
          )}
        </Card.Body>
      </Card>

      {error && <Alert variant="danger">{error}</Alert>}
      {!hasResults && !loading && (
        <Alert variant="info">
          Configure the simulation above and click <strong>Run Analysis</strong> to generate results.
        </Alert>
      )}

      {hasResults && (
        <Tabs defaultActiveKey="winners" className="mb-3">

          <Tab eventKey="winners" title={scenarioCount === 2 ? 'Scenario Comparison' : 'Winner Matrix'}>
            <WinnerMatrixTab
              comparisonResults={comparisonResults}
              resultsB={resultsB}
              allMethodNames={allMethodNames}
              candidateColorMap={candidateColorMap}
              configA={configA}
              configB={configB}
              numSimulations={numSimulations}
              scenarioCount={scenarioCount}
            />
          </Tab>

          <Tab eventKey="metrics" title="Metrics">
            <MetricsTab
              comparisonResults={comparisonResults}
              allMethodNames={allMethodNames}
              numSimulations={numSimulations}
            />
          </Tab>

          <Tab eventKey="strategic" title="Strategic Impact">
            <StrategicImpactTab strategicData={strategicData} allMethodNames={allMethodNames} />
          </Tab>

          <Tab eventKey="condorcet" title="Condorcet Matrix">
            <Card className="mb-4">
              <Card.Header>
                <strong>Condorcet Matrix</strong>
                <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
                  — pairwise head-to-head preferences across the population (Scenario A)
                </span>
              </Card.Header>
              <Card.Body>
                {condorcetData
                  ? <CondorcetMatrix result={condorcetData} />
                  : <Alert variant="info">No Condorcet data available.</Alert>}
              </Card.Body>
            </Card>
          </Tab>

          <Tab eventKey="arrow" title="Arrow Criteria">
            <Card className="mb-4">
              <Card.Header>
                <strong>Arrow's Impossibility Criteria</strong>
                <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
                  — empirical verification on the simulated population (Scenario A)
                </span>
              </Card.Header>
              <Card.Body>
                {arrowData
                  ? <ArrowCriteriaMatrix result={arrowData} />
                  : <Alert variant="info">No Arrow criteria data available.</Alert>}
              </Card.Body>
            </Card>
          </Tab>

          <Tab eventKey="bandwagon" title="Bandwagon">
            <BandwagonAnalysis baseParams={baseParamsA} />
          </Tab>

          <Tab eventKey="montecarlo" title="Monte Carlo">
            <MonteCarloResults baseParams={baseParamsA} />
          </Tab>

          <Tab eventKey="real-elections" title="Real Elections">
            <RealElectionsTab />
          </Tab>

          <Tab eventKey="multiwinner" title="Multi-winner">
            <MultiwinnerAnalysis />
          </Tab>

          <Tab eventKey="sensitivity" title="Sensitivity">
            <SensitivityTab
              baseConfig={{
                numVoters: configA.numVoters,
                candidates: candidateNamesA,
                ideology_distribution: configA.ideology_distribution,
              }}
            />
          </Tab>

        </Tabs>
      )}

      <ScenarioModals
        showSaveModal={showSaveModal}
        setShowSaveModal={setShowSaveModal}
        saveName={saveName}
        setSaveName={setSaveName}
        saving={saving}
        handleSave={handleSave}
        showLoadModal={showLoadModal}
        setShowLoadModal={setShowLoadModal}
        scenarioList={scenarioList}
        loadingList={loadingList}
        handleLoad={handleLoad}
        handleDelete={handleDelete}
      />
    </Container>
  );
};

export default SimulationComparePage;
