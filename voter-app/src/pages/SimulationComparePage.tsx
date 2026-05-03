import React, { useMemo, useState } from 'react';
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Container,
  Form,
  Modal,
  Row,
  Spinner,
  Tab,
  Table,
  Tabs,
} from 'react-bootstrap';
import CondorcetMatrix from '../components/Simulation/CondorcetMatrix';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  CondorcetMatrixResult,
  ScenarioDetail,
  ScenarioSummary,
  SensitivityResult,
  SimulationCompareResult,
  StrategicImpactPoint,
} from '../types';
import {
  getCondorcetMatrix,
  getSensitivityAnalysis,
  runComparisonSimulation,
  runStrategicImpactAnalysis,
} from '../services/simulationCompareApi';
import {
  deleteScenario,
  getScenario,
  listScenarios,
  saveScenario,
} from '../services/scenariosApi';

// ── Constants ──────────────────────────────────────────────────────────────

const CANDIDATE_PALETTE = ['#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f', '#edc948'];

const METHOD_LABELS: Record<string, string> = {
  plurality: 'Plurality',
  two_round: 'Two-Round',
  borda: 'Borda',
  approval: 'Approval',
  irv: 'IRV',
  coombs: "Coombs'",
  bucklin: 'Bucklin',
  minimax: 'Minimax',
  schulze: 'Schulze',
  kemeny_young: 'Kemeny-Young',
  simple_score: 'Simple Score',
  star_voting: 'STAR',
  median_voting: 'Median Score',
  mean_median_hybrid: 'Mean-Median',
  variance_based: 'Variance-Based',
};

const METHOD_LINE_COLORS: Record<string, string> = {
  plurality: '#e15759',
  two_round: '#f28e2b',
  borda: '#4e79a7',
  approval: '#76b7b2',
  irv: '#59a14f',
  coombs: '#edc948',
  bucklin: '#b07aa1',
  minimax: '#ff9da7',
  schulze: '#9c755f',
  kemeny_young: '#bab0ac',
  simple_score: '#86bcb6',
  star_voting: '#e05c5c',
  median_voting: '#499894',
  mean_median_hybrid: '#f1ce63',
  variance_based: '#d37295',
};

const STRATEGIC_PERCENTAGES = [0, 10, 20, 30, 40, 50];

const METHOD_DESCRIPTIONS: Record<string, string> = {
  plurality:
    'Each voter votes for one candidate; the most votes wins. Simple, but vulnerable to vote-splitting: a similar candidate entering the race can reverse the outcome (spoiler effect).',
  two_round:
    'If no candidate reaches a majority in round 1, the top two face a runoff. Reduces vote-splitting but still incentivises strategic voting in the first round.',
  borda:
    'Voters rank all candidates; each rank earns points (last = 0). Totals decide the winner. Rewards broad appeal, but susceptible to the "burial" strategy: placing a strong rival last to minimise their score.',
  approval:
    'Voters approve any number of candidates; the most-approved wins. Eliminates the spoiler effect. The strategic challenge is calibrating how many candidates to approve.',
  irv:
    'Instant Runoff Voting: the weakest candidate (fewest first choices) is eliminated each round until someone has a majority. Can still incentivise compromise voting when your preferred candidate is not viable.',
  coombs:
    "Like IRV but eliminates the candidate with the most last-place votes each round. Tends to elect more centrist winners than standard IRV.",
  bucklin:
    'Voters rank candidates. Approval is expanded rank-by-rank until a majority is reached. A hybrid between ranked and approval voting.',
  minimax:
    "Minimises the maximum pairwise opposition: the winner is the candidate whose worst head-to-head defeat is the least bad. A Condorcet-extension method.",
  schulze:
    'Finds the strongest chain of pairwise victories (Floyd–Warshall path strength). Satisfies Condorcet, monotonicity, and many other criteria. Widely used in online elections.',
  kemeny_young:
    'Finds the complete ranking minimising the total Kendall-tau distance from all voter rankings. Computationally expensive (O(n!) candidates) but theoretically very robust.',
  simple_score:
    'Voters assign a numeric score to each candidate; the highest average wins. High expressivity, but exaggeration (giving 5 to your favourite, 0 to the rest) is the dominant strategy.',
  star_voting:
    'Score Then Automatic Runoff: the two highest-scoring candidates face a pairwise runoff. Combines score expressivity with resistance to strategic polarisation.',
  median_voting:
    'The winner has the highest median score. Inherently resistant to exaggeration — one extreme voter cannot shift the median as easily as the mean.',
  mean_median_hybrid:
    '50 % mean + 50 % median composite score. Balances expressivity and resistance to strategic manipulation.',
  variance_based:
    'Score = mean − 0.5 × std_dev. Penalises polarising candidates who score high with some voters but low with others, favouring consistent broad support.',
};

const IDEOLOGY_OPTIONS = [
  { value: 'random', label: 'Random' },
  { value: 'centrist', label: 'Centrist' },
  { value: 'polarized', label: 'Polarized' },
  { value: 'left_skewed', label: 'Left-skewed' },
  { value: 'right_skewed', label: 'Right-skewed' },
];

// ── Helpers ────────────────────────────────────────────────────────────────

function avg(values: number[]): number {
  if (values.length === 0) return 0;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

function round(value: number, decimals = 3): number {
  return Math.round(value * 10 ** decimals) / 10 ** decimals;
}

/** Most frequent winner for a given method across N simulation runs. */
function mostCommonWinner(results: SimulationCompareResult[], method: string): string | null {
  const winners = results
    .map((r) => r.methods[method]?.winner)
    .filter((w): w is string => !!w);
  if (!winners.length) return null;
  const counts = winners.reduce(
    (acc, w) => ({ ...acc, [w]: (acc[w] ?? 0) + 1 }),
    {} as Record<string, number>
  );
  return Object.entries(counts).sort((a, b) => b[1] - a[1])[0][0];
}

// ── Sub-components ─────────────────────────────────────────────────────────

interface WinnerMatrixTableProps {
  results: SimulationCompareResult[];
  allMethodNames: string[];
  colorMap: Record<string, string>;
  label?: string;
  onCellClick?: (methodKey: string, simIndex: number) => void;
}

const WinnerMatrixTable: React.FC<WinnerMatrixTableProps> = ({
  results,
  allMethodNames,
  colorMap,
  label,
  onCellClick,
}) => (
  <div style={{ overflowX: 'auto' }}>
    {label && (
      <p className="fw-semibold text-center mb-2" style={{ fontSize: '0.9rem' }}>
        {label}
      </p>
    )}
    <Table bordered hover size="sm" style={{ minWidth: 500 }}>
      <thead className="table-light">
        <tr>
          <th style={{ minWidth: 130 }}>Method</th>
          {results.map((_, i) => (
            <th key={i} className="text-center" style={{ minWidth: 72 }}>
              #{i + 1}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {allMethodNames.map((method) => (
          <tr key={method}>
            <td>
              <strong>{METHOD_LABELS[method] || method}</strong>
            </td>
            {results.map((r, i) => {
              const winner = r.methods[method]?.winner;
              const notCondorcet =
                r.condorcet_winner && r.methods[method]?.condorcet_consistent === false;
              return (
                <td
                  key={i}
                  className="text-center"
                  style={onCellClick ? { cursor: 'pointer' } : undefined}
                  onClick={onCellClick ? () => onCellClick(method, i) : undefined}
                  title={onCellClick ? 'Click for details' : undefined}
                >
                  {winner ? (
                    <Badge
                      style={{
                        backgroundColor: colorMap[winner] ?? '#999',
                        fontSize: '0.72rem',
                      }}
                    >
                      {winner}
                      {notCondorcet ? ' *' : ''}
                    </Badge>
                  ) : (
                    <span className="text-muted">—</span>
                  )}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </Table>
  </div>
);

// ── Main component ─────────────────────────────────────────────────────────

interface ScenarioConfig {
  numVoters: number;
  candidateInput: string;
  ideology_distribution: string;
}

const SimulationComparePage: React.FC = () => {
  // ── Scenario A config ──
  const [numSimulations, setNumSimulations] = useState(10);
  const [configA, setConfigA] = useState<ScenarioConfig>({
    numVoters: 500,
    candidateInput: 'Alice, Bob, Charlie',
    ideology_distribution: 'random',
  });

  // ── Scenario B config ──
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
  const [resultsB, setResultsB] = useState<SimulationCompareResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ── Drill-down state ──
  const [drilldownTarget, setDrilldownTarget] = useState<{
    methodKey: string;
    simIndex: number;
  } | null>(null);

  // ── Export helpers ──
  const _exportDate = new Date().toISOString().slice(0, 10);

  const exportJSON = () => {
    const blob = new Blob(
      [JSON.stringify({ comparisonResults, strategicData }, null, 2)],
      { type: 'application/json' }
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `simulation_results_${_exportDate}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportCSV = () => {
    const header =
      'simulation_id,method,winner,bayesian_regret,majority_satisfaction,' +
      'strategic_vulnerability,condorcet_consistent\n';
    const rows = comparisonResults.flatMap((r, idx) =>
      Object.entries(r.methods).map(([method, m]) =>
        [
          idx + 1,
          method,
          m.winner ?? '',
          m.bayesian_regret ?? '',
          m.majority_satisfaction ?? '',
          m.strategic_vulnerability ?? '',
          m.condorcet_consistent ?? '',
        ].join(',')
      )
    );
    const blob = new Blob([header + rows.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `simulation_results_${_exportDate}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // ── Scenario save / load state ──
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [saveName, setSaveName] = useState('');
  const [saving, setSaving] = useState(false);
  const [showLoadModal, setShowLoadModal] = useState(false);
  const [scenarioList, setScenarioList] = useState<ScenarioSummary[]>([]);
  const [loadingList, setLoadingList] = useState(false);

  // ── Sensitivity state ──
  const [sensitivityVariable, setSensitivityVariable] = useState<
    'ideology_distribution' | 'num_voters' | 'strategic_pct'
  >('ideology_distribution');
  const [sensitivityValuesInput, setSensitivityValuesInput] = useState(
    'random, centrist, polarized, left_skewed, right_skewed'
  );
  const [sensitivityData, setSensitivityData] = useState<SensitivityResult | null>(null);
  const [sensitivityLoading, setSensitivityLoading] = useState(false);

  // ── Derived ──
  const candidateNamesA = useMemo(
    () => configA.candidateInput.split(',').map((s) => s.trim()).filter(Boolean),
    [configA.candidateInput]
  );

  const candidateNamesB = useMemo(
    () => configB.candidateInput.split(',').map((s) => s.trim()).filter(Boolean),
    [configB.candidateInput]
  );

  // Shared color map: same candidate name always gets the same color across A and B.
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

  const metricsData = useMemo(() => {
    if (!comparisonResults.length) return [];
    return allMethodNames.map((method) => {
      const values = comparisonResults.map((r) => r.methods[method]);
      return {
        method: METHOD_LABELS[method] || method,
        'Bayesian Regret': round(avg(values.map((v) => v.bayesian_regret ?? 0))),
        'Majority Satisfaction': round(avg(values.map((v) => v.majority_satisfaction ?? 0))),
        'Strategic Vulnerability': round(avg(values.map((v) => v.strategic_vulnerability ?? 0))),
      };
    });
  }, [comparisonResults, allMethodNames]);

  const strategicChartData = useMemo(
    () =>
      strategicData.map((point) => ({
        pct: `${point.strategic_pct}%`,
        ...Object.fromEntries(
          Object.entries(point.methods).map(([m, v]) => [METHOD_LABELS[m] || m, v])
        ),
      })),
    [strategicData]
  );

  /** Side-by-side winner diff table, sorted: disagreements first. */
  const diffData = useMemo(() => {
    if (!resultsB || !allMethodNames.length) return [];
    return allMethodNames
      .map((method) => ({
        method,
        winnerA: mostCommonWinner(comparisonResults, method),
        winnerB: mostCommonWinner(resultsB, method),
      }))
      .sort((a, b) => {
        const aDiffers = a.winnerA !== a.winnerB ? 0 : 1;
        const bDiffers = b.winnerA !== b.winnerB ? 0 : 1;
        return aDiffers - bDiffers;
      });
  }, [allMethodNames, comparisonResults, resultsB]);

  // ── Sensitivity derived data ──

  const sensitivityMethodNames = useMemo(
    () =>
      sensitivityData?.results.length
        ? Object.keys(sensitivityData.results[0].winners_by_method)
        : [],
    [sensitivityData]
  );

  const sensitivityColorMap = useMemo(() => {
    if (!sensitivityData) return {} as Record<string, string>;
    const names = new Set<string>();
    sensitivityData.results.forEach((r) =>
      Object.values(r.winners_by_method).forEach((w) => { if (w) names.add(w); })
    );
    return Object.fromEntries(
      [...names].map((n, i) => [n, CANDIDATE_PALETTE[i % CANDIDATE_PALETTE.length]])
    );
  }, [sensitivityData]);

  const sensitivityLineData = useMemo(
    () =>
      (sensitivityData?.results ?? []).map((r) => ({
        label: String(r.value),
        ...Object.fromEntries(
          sensitivityMethodNames.map((m) => [
            METHOD_LABELS[m] || m,
            r.regret_by_method[m] ?? null,
          ])
        ),
      })),
    [sensitivityData, sensitivityMethodNames]
  );

  // ── Default values per variable ──

  const DEFAULT_SENSITIVITY_VALUES: Record<string, string> = {
    ideology_distribution: 'random, centrist, polarized, left_skewed, right_skewed',
    num_voters: '100, 250, 500, 1000, 2000',
    strategic_pct: '0, 10, 20, 30, 40, 50',
  };

  // ── Run ──

  const runSensitivity = async () => {
    const raw = sensitivityValuesInput.split(',').map((s) => s.trim()).filter(Boolean);
    if (!raw.length) return;
    const parsedValues: (string | number)[] =
      sensitivityVariable === 'ideology_distribution'
        ? raw
        : raw.map(Number).filter((n) => !isNaN(n));
    if (!parsedValues.length) return;

    setSensitivityLoading(true);
    try {
      const result = await getSensitivityAnalysis({
        base_config: {
          num_voters: configA.numVoters,
          candidates: candidateNamesA,
          ideology_distribution: configA.ideology_distribution,
        },
        variable: sensitivityVariable,
        values: parsedValues,
      });
      setSensitivityData(result);
    } catch {
      // Swallow — error visible in the tab itself
    } finally {
      setSensitivityLoading(false);
    }
  };

  // ── Scenario handlers ──

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
      const list = await listScenarios();
      setScenarioList(list);
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
      const paramsB = {
        num_voters: configB.numVoters,
        candidates: candidateNamesB,
        ideology_distribution: configB.ideology_distribution,
      };

      const [simResultsA, strategicResults, condorcetResult, simResultsB] = await Promise.all([
        Promise.all(
          Array.from({ length: numSimulations }, () => runComparisonSimulation(paramsA))
        ),
        runStrategicImpactAnalysis({ ...paramsA, strategic_percentages: STRATEGIC_PERCENTAGES }),
        getCondorcetMatrix(paramsA),
        scenarioCount === 2
          ? Promise.all(
              Array.from({ length: numSimulations }, () => runComparisonSimulation(paramsB))
            )
          : Promise.resolve(null),
      ]);

      setComparisonResults(simResultsA);
      setStrategicData(strategicResults);
      setCondorcetData(condorcetResult);
      setResultsB(simResultsB);
    } catch {
      setError('Analysis failed. Make sure the backend is running and the endpoints exist.');
    } finally {
      setLoading(false);
    }
  };

  const hasResults = comparisonResults.length > 0;

  // ── Shared config form row ──
  const ConfigRow = ({
    config,
    onChange,
    label,
  }: {
    config: ScenarioConfig;
    onChange: (patch: Partial<ScenarioConfig>) => void;
    label?: string;
  }) => (
    <Row className="g-2 align-items-end">
      {label && (
        <Col xs={12}>
          <span className="fw-semibold text-muted small">{label}</span>
        </Col>
      )}
      <Col md={4}>
        <Form.Label className="small mb-1">Candidates (comma-separated)</Form.Label>
        <Form.Control
          size="sm"
          type="text"
          value={config.candidateInput}
          onChange={(e) => onChange({ candidateInput: e.target.value })}
          placeholder="Alice, Bob, Charlie"
        />
      </Col>
      <Col md={3}>
        <Form.Label className="small mb-1">Voters</Form.Label>
        <Form.Control
          size="sm"
          type="number"
          min={100}
          max={2000}
          step={100}
          value={config.numVoters}
          onChange={(e) => onChange({ numVoters: Number(e.target.value) })}
        />
      </Col>
      <Col md={3}>
        <Form.Label className="small mb-1">Electorate distribution</Form.Label>
        <Form.Select
          size="sm"
          value={config.ideology_distribution}
          onChange={(e) => onChange({ ideology_distribution: e.target.value })}
        >
          {IDEOLOGY_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </Form.Select>
      </Col>
    </Row>
  );

  // ── Render ──
  return (
    <Container className="py-4">
      <h2 className="mb-1">Comparative Voting Methods Analysis</h2>
      <p className="text-muted mb-3">
        Run multiple simulations on the same population and compare how each voting method
        performs. Add a second scenario to study the spoiler effect or IIA violations.
      </p>

      <div className="d-flex gap-2 mb-4">
        <Button
          variant="outline-secondary"
          size="sm"
          onClick={handleOpenLoadModal}
        >
          📂 Load scenario
        </Button>
        {hasResults && (
          <>
            <Button
              variant="outline-success"
              size="sm"
              onClick={() => { setSaveName(''); setShowSaveModal(true); }}
            >
              💾 Save
            </Button>
            <Button variant="outline-primary" size="sm" onClick={exportJSON}>
              ⬇ JSON
            </Button>
            <Button variant="outline-primary" size="sm" onClick={exportCSV}>
              ⬇ CSV
            </Button>
          </>
        )}
      </div>

      {/* ── Configuration ── */}
      <Card className="mb-4">
        <Card.Header className="d-flex align-items-center justify-content-between">
          <strong>Configuration</strong>
          {scenarioCount === 1 ? (
            <Button
              size="sm"
              variant="outline-secondary"
              onClick={() => setScenarioCount(2)}
            >
              + Add scenario B
            </Button>
          ) : (
            <Button
              size="sm"
              variant="outline-danger"
              onClick={() => { setScenarioCount(1); setResultsB(null); }}
            >
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
              <Form.Range
                min={5}
                max={20}
                value={numSimulations}
                onChange={(e) => setNumSimulations(Number(e.target.value))}
              />
            </Col>
            <Col md={2}>
              <Button
                variant="primary"
                className="w-100"
                onClick={runAnalysis}
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Spinner size="sm" className="me-2" />
                    Running…
                  </>
                ) : (
                  'Run Analysis'
                )}
              </Button>
            </Col>
          </Row>

          {scenarioCount === 1 ? (
            <ConfigRow
              config={configA}
              onChange={(p) => setConfigA((c) => ({ ...c, ...p }))}
            />
          ) : (
            <Row className="g-3">
              <Col md={6}>
                <ConfigRow
                  config={configA}
                  onChange={(p) => setConfigA((c) => ({ ...c, ...p }))}
                  label="Scenario A"
                />
              </Col>
              <Col md={6}>
                <ConfigRow
                  config={configB}
                  onChange={(p) => setConfigB((c) => ({ ...c, ...p }))}
                  label="Scenario B"
                />
              </Col>
            </Row>
          )}
        </Card.Body>
      </Card>

      {error && <Alert variant="danger">{error}</Alert>}

      {!hasResults && !loading && (
        <Alert variant="info">
          Configure the simulation above and click <strong>Run Analysis</strong> to generate
          results.
        </Alert>
      )}

      {hasResults && (
        <Tabs defaultActiveKey="winners" className="mb-3">

          {/* ── Tab 1: Winner Matrix ── */}
          <Tab eventKey="winners" title={scenarioCount === 2 ? 'Scenario Comparison' : 'Winner Matrix'}>
            {/* Colour legend */}
            <div className="mb-3 d-flex gap-3 flex-wrap align-items-center">
              {Object.entries(candidateColorMap).map(([name, color]) => (
                <span key={name} className="d-flex align-items-center gap-1">
                  <span
                    style={{
                      display: 'inline-block',
                      width: 12,
                      height: 12,
                      borderRadius: 3,
                      backgroundColor: color,
                    }}
                  />
                  <small>{name}</small>
                </span>
              ))}
              {comparisonResults.some((r) =>
                Object.values(r.methods).some((m) => m.condorcet_consistent === false)
              ) && (
                <small className="text-muted">* = Condorcet winner not elected</small>
              )}
            </div>

            {scenarioCount === 2 && resultsB ? (
              <>
                {/* Side-by-side matrices */}
                <Row className="g-3 mb-4">
                  <Col md={6}>
                    <WinnerMatrixTable
                      results={comparisonResults}
                      allMethodNames={allMethodNames}
                      colorMap={candidateColorMap}
                      label={`Scenario A — ${configA.candidateInput} (${IDEOLOGY_OPTIONS.find(o => o.value === configA.ideology_distribution)?.label ?? configA.ideology_distribution})`}
                      onCellClick={(m, i) => setDrilldownTarget({ methodKey: m, simIndex: i })}
                    />
                  </Col>
                  <Col md={6}>
                    <WinnerMatrixTable
                      results={resultsB}
                      allMethodNames={allMethodNames}
                      colorMap={candidateColorMap}
                      label={`Scenario B — ${configB.candidateInput} (${IDEOLOGY_OPTIONS.find(o => o.value === configB.ideology_distribution)?.label ?? configB.ideology_distribution})`}
                    />
                  </Col>
                </Row>

                {/* Differences table */}
                <Card>
                  <Card.Header>
                    <strong>Differences</strong>
                    <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
                      — most frequent winner per method across {numSimulations} runs
                    </span>
                  </Card.Header>
                  <Card.Body className="p-0">
                    <Table bordered size="sm" className="mb-0">
                      <thead className="table-light">
                        <tr>
                          <th style={{ minWidth: 140 }}>Method</th>
                          <th className="text-center">Scenario A winner</th>
                          <th className="text-center">Scenario B winner</th>
                          <th className="text-center" style={{ width: 60 }}></th>
                        </tr>
                      </thead>
                      <tbody>
                        {diffData.map(({ method, winnerA, winnerB }) => {
                          const differs = winnerA !== winnerB;
                          return (
                            <tr
                              key={method}
                              style={differs ? { backgroundColor: '#fff8e1' } : undefined}
                            >
                              <td>
                                <strong>{METHOD_LABELS[method] || method}</strong>
                              </td>
                              <td className="text-center">
                                {winnerA ? (
                                  <Badge
                                    style={{
                                      backgroundColor: candidateColorMap[winnerA] ?? '#999',
                                    }}
                                  >
                                    {winnerA}
                                  </Badge>
                                ) : (
                                  <span className="text-muted">—</span>
                                )}
                              </td>
                              <td className="text-center">
                                {winnerB ? (
                                  <Badge
                                    style={{
                                      backgroundColor: candidateColorMap[winnerB] ?? '#999',
                                    }}
                                  >
                                    {winnerB}
                                  </Badge>
                                ) : (
                                  <span className="text-muted">—</span>
                                )}
                              </td>
                              <td className="text-center fw-bold" style={{ fontSize: '1.1rem' }}>
                                {differs ? (
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
                  </Card.Body>
                </Card>
              </>
            ) : (
              /* Single scenario matrix */
              <Card>
                <Card.Body style={{ overflowX: 'auto' }}>
                  <WinnerMatrixTable
                    results={comparisonResults}
                    allMethodNames={allMethodNames}
                    colorMap={candidateColorMap}
                    onCellClick={(m, i) => setDrilldownTarget({ methodKey: m, simIndex: i })}
                  />
                  <small className="text-muted d-block mt-2">
                    Click any cell to see details for that method &amp; simulation run.
                  </small>
                </Card.Body>
              </Card>
            )}
          </Tab>

          {/* ── Tab 2: Comparative Metrics ── */}
          <Tab eventKey="metrics" title="Metrics">
            <Card className="mb-4">
              <Card.Header>
                <strong>Comparative Metrics</strong>
                <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
                  — averaged across {numSimulations} simulations (Scenario A)
                </span>
              </Card.Header>
              <Card.Body>
                <div className="d-flex gap-4 mb-3 flex-wrap">
                  {[
                    { label: 'Bayesian Regret', color: '#e15759', note: 'lower is better' },
                    { label: 'Majority Satisfaction', color: '#59a14f', note: 'higher is better' },
                    { label: 'Strategic Vulnerability', color: '#f28e2b', note: 'lower is better' },
                  ].map(({ label, color, note }) => (
                    <span key={label} className="d-flex align-items-center gap-1">
                      <span
                        style={{
                          display: 'inline-block',
                          width: 14,
                          height: 14,
                          borderRadius: 2,
                          backgroundColor: color,
                        }}
                      />
                      <small>
                        {label} <span className="text-muted">({note})</span>
                      </small>
                    </span>
                  ))}
                </div>
                <ResponsiveContainer width="100%" height={380}>
                  <BarChart data={metricsData} margin={{ bottom: 90, left: 10, right: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="method"
                      tick={{ fontSize: 11 }}
                      angle={-45}
                      textAnchor="end"
                      interval={0}
                    />
                    <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(v: number) => v.toFixed(3)} />
                    <Bar dataKey="Bayesian Regret" fill="#e15759" />
                    <Bar dataKey="Majority Satisfaction" fill="#59a14f" />
                    <Bar dataKey="Strategic Vulnerability" fill="#f28e2b" />
                  </BarChart>
                </ResponsiveContainer>
              </Card.Body>
            </Card>
          </Tab>

          {/* ── Tab 3: Strategic Impact ── */}
          <Tab eventKey="strategic" title="Strategic Impact">
            <Card className="mb-4">
              <Card.Header>
                <strong>Strategic Voting Impact on Bayesian Regret</strong>
                <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
                  — how each method degrades as the proportion of strategic voters increases
                </span>
              </Card.Header>
              <Card.Body>
                <p className="text-muted small mb-3">
                  Methods whose line rises steeply are more vulnerable to tactical voting.
                  Flat lines indicate resistance to strategic manipulation.
                </p>
                {strategicData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={420}>
                    <LineChart
                      data={strategicChartData}
                      margin={{ top: 5, right: 20, bottom: 20, left: 10 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        dataKey="pct"
                        label={{
                          value: 'Strategic voters (%)',
                          position: 'insideBottom',
                          offset: -10,
                          fontSize: 12,
                        }}
                      />
                      <YAxis
                        label={{
                          value: 'Bayesian Regret',
                          angle: -90,
                          position: 'insideLeft',
                          fontSize: 12,
                        }}
                        tick={{ fontSize: 11 }}
                      />
                      <Tooltip
                        formatter={(v: number) => (v !== null ? v.toFixed(4) : '—')}
                      />
                      <Legend
                        verticalAlign="bottom"
                        wrapperStyle={{ paddingTop: 20, fontSize: 11 }}
                      />
                      {allMethodNames.map((method) => (
                        <Line
                          key={method}
                          type="monotone"
                          dataKey={METHOD_LABELS[method] || method}
                          stroke={METHOD_LINE_COLORS[method] ?? '#999'}
                          strokeWidth={method === 'plurality' ? 2.5 : 1.5}
                          dot={false}
                          activeDot={{ r: 4 }}
                        />
                      ))}
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <Alert variant="info">No strategic impact data available.</Alert>
                )}
              </Card.Body>
            </Card>
          </Tab>

          {/* ── Tab 4: Condorcet Matrix ── */}
          <Tab eventKey="condorcet" title="Condorcet Matrix">
            <Card className="mb-4">
              <Card.Header>
                <strong>Condorcet Matrix</strong>
                <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
                  — pairwise head-to-head preferences across the population (Scenario A)
                </span>
              </Card.Header>
              <Card.Body>
                {condorcetData ? (
                  <CondorcetMatrix result={condorcetData} />
                ) : (
                  <Alert variant="info">No Condorcet data available.</Alert>
                )}
              </Card.Body>
            </Card>
          </Tab>

          {/* ── Tab 5: Sensitivity Analysis ── */}
          <Tab eventKey="sensitivity" title="Sensitivity">
            <Card className="mb-4">
              <Card.Header>
                <strong>Sensitivity Analysis</strong>
                <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
                  — vary one parameter and observe how winners change (uses Scenario A config)
                </span>
              </Card.Header>
              <Card.Body>
                {/* ── Config form ── */}
                <Row className="g-3 align-items-end mb-4">
                  <Col md={3}>
                    <Form.Label className="small mb-1">Variable</Form.Label>
                    <Form.Select
                      size="sm"
                      value={sensitivityVariable}
                      onChange={(e) => {
                        const v = e.target.value as typeof sensitivityVariable;
                        setSensitivityVariable(v);
                        setSensitivityValuesInput(DEFAULT_SENSITIVITY_VALUES[v] ?? '');
                      }}
                    >
                      <option value="ideology_distribution">Electorate distribution</option>
                      <option value="num_voters">Number of voters</option>
                      <option value="strategic_pct">Strategic voter %</option>
                    </Form.Select>
                  </Col>
                  <Col md={6}>
                    <Form.Label className="small mb-1">
                      Values to test{' '}
                      <span className="text-muted">
                        (comma-separated
                        {sensitivityVariable !== 'ideology_distribution' ? ', numbers' : ''})
                      </span>
                    </Form.Label>
                    <Form.Control
                      size="sm"
                      type="text"
                      value={sensitivityValuesInput}
                      onChange={(e) => setSensitivityValuesInput(e.target.value)}
                    />
                  </Col>
                  <Col md={3}>
                    <Button
                      variant="primary"
                      size="sm"
                      className="w-100"
                      onClick={runSensitivity}
                      disabled={sensitivityLoading}
                    >
                      {sensitivityLoading ? (
                        <>
                          <Spinner size="sm" className="me-2" />
                          Running…
                        </>
                      ) : (
                        'Run Sensitivity'
                      )}
                    </Button>
                  </Col>
                </Row>

                {sensitivityData && (
                  <>
                    {/* ── Heatmap ── */}
                    <p className="fw-semibold mb-2">Winner heatmap</p>
                    <div style={{ overflowX: 'auto' }} className="mb-4">
                      <Table bordered size="sm" className="text-center" style={{ minWidth: 400 }}>
                        <thead className="table-light">
                          <tr>
                            <th style={{ minWidth: 130, textAlign: 'left' }}>Method</th>
                            {sensitivityData.results.map((r) => (
                              <th key={String(r.value)} style={{ minWidth: 90 }}>
                                {String(r.value)}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {sensitivityMethodNames.map((method) => {
                            const winners = sensitivityData.results.map(
                              (r) => r.winners_by_method[method] ?? null
                            );
                            const allSame = winners.every((w) => w === winners[0]);
                            return (
                              <tr
                                key={method}
                                style={!allSame ? { backgroundColor: '#fff8e1' } : undefined}
                              >
                                <td className="text-start ps-2">
                                  <strong>{METHOD_LABELS[method] || method}</strong>
                                </td>
                                {winners.map((winner, ci) => (
                                  <td key={ci}>
                                    {winner ? (
                                      <Badge
                                        style={{
                                          backgroundColor:
                                            sensitivityColorMap[winner] ?? '#999',
                                          fontSize: '0.72rem',
                                        }}
                                      >
                                        {winner}
                                      </Badge>
                                    ) : (
                                      <span className="text-muted">—</span>
                                    )}
                                  </td>
                                ))}
                              </tr>
                            );
                          })}
                        </tbody>
                      </Table>
                    </div>
                    <small className="text-muted d-block mb-4">
                      Highlighted rows indicate methods where the winner changes across values.
                    </small>

                    {/* ── Regret line chart ── */}
                    <p className="fw-semibold mb-2">Bayesian Regret by value</p>
                    <ResponsiveContainer width="100%" height={380}>
                      <LineChart
                        data={sensitivityLineData}
                        margin={{ top: 5, right: 20, bottom: 40, left: 10 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis
                          dataKey="label"
                          tick={{ fontSize: 10 }}
                          angle={-30}
                          textAnchor="end"
                          interval={0}
                        />
                        <YAxis tick={{ fontSize: 11 }} />
                        <Tooltip
                          formatter={(v: number) => (v !== null ? v.toFixed(4) : '—')}
                        />
                        <Legend
                          verticalAlign="bottom"
                          wrapperStyle={{ paddingTop: 10, fontSize: 10 }}
                        />
                        {sensitivityMethodNames.map((method) => (
                          <Line
                            key={method}
                            type="monotone"
                            dataKey={METHOD_LABELS[method] || method}
                            stroke={METHOD_LINE_COLORS[method] ?? '#999'}
                            strokeWidth={method === 'plurality' ? 2.5 : 1.5}
                            dot={{ r: 3 }}
                            connectNulls
                          />
                        ))}
                      </LineChart>
                    </ResponsiveContainer>
                  </>
                )}

                {!sensitivityData && !sensitivityLoading && (
                  <Alert variant="info" className="mb-0">
                    Select a variable, adjust the values and click{' '}
                    <strong>Run Sensitivity</strong>.
                  </Alert>
                )}
              </Card.Body>
            </Card>
          </Tab>

        </Tabs>
      )}
      {/* ── Drill-down modal ── */}
      {drilldownTarget && (() => {
        const { methodKey, simIndex } = drilldownTarget;
        const r = comparisonResults[simIndex];
        const m = r?.methods[methodKey];
        if (!r || !m) return null;
        const winner = m.winner;

        return (
          <Modal
            show
            centered
            size="lg"
            onHide={() => setDrilldownTarget(null)}
          >
            <Modal.Header closeButton>
              <Modal.Title>
                {METHOD_LABELS[methodKey] || methodKey}
                <span className="text-muted fw-normal ms-2" style={{ fontSize: '1rem' }}>
                  — Simulation #{simIndex + 1}
                </span>
              </Modal.Title>
            </Modal.Header>
            <Modal.Body>

              {/* a) Winner */}
              <div className="text-center mb-4">
                <div className="text-muted small mb-1">Winner</div>
                {winner ? (
                  <Badge
                    style={{
                      backgroundColor: candidateColorMap[winner] ?? '#999',
                      fontSize: '1.1rem',
                      padding: '0.45em 1.1em',
                    }}
                  >
                    {winner}
                  </Badge>
                ) : (
                  <span className="text-muted">No winner</span>
                )}
              </div>

              {/* b) Metrics table */}
              <Table bordered size="sm" className="mb-3">
                <tbody>
                  {[
                    {
                      label: 'Bayesian Regret',
                      value: m.bayesian_regret != null ? m.bayesian_regret.toFixed(4) : '—',
                      note: 'lower = better',
                    },
                    {
                      label: 'Majority Satisfaction',
                      value:
                        m.majority_satisfaction != null
                          ? `${(m.majority_satisfaction * 100).toFixed(1)} %`
                          : '—',
                      note: 'higher = better',
                    },
                    {
                      label: 'Strategic Vulnerability',
                      value:
                        m.strategic_vulnerability != null
                          ? `${(m.strategic_vulnerability * 100).toFixed(1)} %`
                          : '—',
                      note: 'lower = better',
                    },
                  ].map(({ label, value, note }) => (
                    <tr key={label}>
                      <td className="fw-semibold" style={{ width: '40%' }}>
                        {label}
                      </td>
                      <td>{value}</td>
                      <td className="text-muted small">{note}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>

              {/* c) Condorcet comparison */}
              {r.condorcet_winner ? (
                m.condorcet_consistent ? (
                  <Alert variant="success" className="py-2 mb-3">
                    ✓ Elected the Condorcet winner
                  </Alert>
                ) : (
                  <Alert variant="warning" className="py-2 mb-3">
                    ✗ The Condorcet winner was{' '}
                    <strong>
                      <Badge
                        style={{
                          backgroundColor: candidateColorMap[r.condorcet_winner] ?? '#999',
                        }}
                      >
                        {r.condorcet_winner}
                      </Badge>
                    </strong>
                  </Alert>
                )
              ) : (
                <Alert variant="secondary" className="py-2 mb-3">
                  No Condorcet winner in this simulation (cycle or tie at the top).
                </Alert>
              )}

              {/* d) Method description */}
              <p className="text-muted small mb-0" style={{ lineHeight: 1.6 }}>
                <strong>{METHOD_LABELS[methodKey] || methodKey}: </strong>
                {METHOD_DESCRIPTIONS[methodKey] ?? 'No description available.'}
              </p>
            </Modal.Body>
            <Modal.Footer>
              <Button variant="secondary" onClick={() => setDrilldownTarget(null)}>
                Close
              </Button>
            </Modal.Footer>
          </Modal>
        );
      })()}

      {/* ── Save modal ── */}
    <Modal show={showSaveModal} onHide={() => setShowSaveModal(false)} centered>
      <Modal.Header closeButton>
        <Modal.Title>Save scenario</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <Form.Label>Scenario name</Form.Label>
        <Form.Control
          type="text"
          value={saveName}
          onChange={(e) => setSaveName(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleSave(); }}
          placeholder="My scenario"
          autoFocus
        />
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={() => setShowSaveModal(false)}>
          Cancel
        </Button>
        <Button
          variant="success"
          onClick={handleSave}
          disabled={saving || !saveName.trim()}
        >
          {saving ? <><Spinner size="sm" className="me-2" />Saving…</> : 'Save'}
        </Button>
      </Modal.Footer>
    </Modal>

    {/* ── Load modal ── */}
    <Modal
      show={showLoadModal}
      onHide={() => setShowLoadModal(false)}
      size="lg"
      centered
    >
      <Modal.Header closeButton>
        <Modal.Title>Load scenario</Modal.Title>
      </Modal.Header>
      <Modal.Body style={{ maxHeight: '60vh', overflowY: 'auto' }}>
        {loadingList ? (
          <div className="text-center py-3">
            <Spinner />
          </div>
        ) : scenarioList.length === 0 ? (
          <Alert variant="info" className="mb-0">
            No saved scenarios yet. Run an analysis and click{' '}
            <strong>Save scenario</strong> to save one.
          </Alert>
        ) : (
          <Table bordered hover size="sm">
            <thead className="table-light">
              <tr>
                <th>Name</th>
                <th>Saved</th>
                <th style={{ width: 160 }}></th>
              </tr>
            </thead>
            <tbody>
              {scenarioList.map((s) => (
                <tr key={s.id}>
                  <td className="align-middle">{s.name}</td>
                  <td className="align-middle text-muted small">
                    {new Date(s.created_at).toLocaleString()}
                  </td>
                  <td className="text-center">
                    <Button
                      size="sm"
                      variant="outline-primary"
                      className="me-2"
                      onClick={() =>
                        getScenario(s.id).then((detail) => handleLoad(detail))
                      }
                    >
                      Load
                    </Button>
                    <Button
                      size="sm"
                      variant="outline-danger"
                      onClick={() => handleDelete(s.id)}
                    >
                      ✕
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={() => setShowLoadModal(false)}>
          Close
        </Button>
      </Modal.Footer>
    </Modal>

    </Container>
  );
};

export default SimulationComparePage;
