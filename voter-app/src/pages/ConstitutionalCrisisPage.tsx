import React, { useState } from 'react';
import { Alert, Badge, Button, Card, Col, Container, Row, Spinner, Tab, Tabs } from 'react-bootstrap';
import CandidateEditor, { CandidateConfig, newCandidate, newBlankCandidate } from '../components/ScenarioBuilder/CandidateEditor';
import ElectorateConfig, { ElectorateState } from '../components/ScenarioBuilder/ElectorateConfig';
import ScenarioAPanel from '../components/ConstitutionalCrisis/ScenarioAPanel';
import ScenarioBPanel from '../components/ConstitutionalCrisis/ScenarioBPanel';
import ScenarioCPanel from '../components/ConstitutionalCrisis/ScenarioCPanel';
import {
  runConstitutionalScenario,
  runScenario,
  ConstitutionalResult,
  ScenarioResult,
} from '../services/simulationCompareApi';

const COLORS = ['#4e79a7', '#e15759', '#59a14f', '#f28e2b', '#76b7b2', '#edc948'];

function toApiCandidates(candidates: CandidateConfig[]) {
  return candidates.map((c) => ({
    name: c.name,
    ideology: c.ideology,
    positions: { economy: c.economy, environment: c.environment, social: c.social },
    is_blank: c.isBlank,
  }));
}

function toApiElectorate(e: ElectorateState) {
  return { num_voters: e.numVoters, ideology_preset: e.ideologyPreset, dissatisfaction_rate: e.dissatisfactionRate };
}

// ── Initial results banner ─────────────────────────────────────────────────

const InitialResultsBanner: React.FC<{ results: ScenarioResult; candidates: CandidateConfig[] }> = ({ results, candidates }) => {
  const colorMap = Object.fromEntries(
    candidates.filter((c) => !c.isBlank).map((c, i) => [c.name, COLORS[i % COLORS.length]])
  );
  const blankPct = results.with_blank.blank_pct ?? 0;
  const blankWins = Object.values(results.with_blank.methods).some((m) => m.winner === 'Blank' || m.blank_rule_applied?.blank_triggered);

  return (
    <Card className={`mb-4 border-${blankWins ? 'danger' : 'success'}`}>
      <Card.Header className={`bg-${blankWins ? 'danger' : 'success'} text-white`}>
        <strong>
          {blankWins ? '🚨 Vote blanc victorieux — scénarios constitutionnels disponibles' : '✓ Vote blanc non décisif'}
        </strong>
        <span className="ms-3 fw-normal" style={{ fontSize: '0.9rem' }}>
          {Math.round(blankPct * 100)}% des électeurs ont voté blanc
        </span>
      </Card.Header>
      <Card.Body className="py-2">
        <div className="d-flex flex-wrap gap-3">
          {Object.entries(results.with_blank.methods).map(([m, d]) => {
            const effective = d.blank_rule_applied?.winner ?? d.winner;
            return (
              <div key={m} style={{ fontSize: '0.82rem' }}>
                <span className="text-muted">{m} → </span>
                {effective === 'Blank' || effective == null ? (
                  <Badge bg="warning" text="dark">⬜ Vote Blanc</Badge>
                ) : (
                  <Badge style={{ backgroundColor: colorMap[effective] ?? '#999' }}>{effective}</Badge>
                )}
                {d.blank_rule_applied?.blank_triggered && <span className="ms-1 text-danger">🚨</span>}
              </div>
            );
          })}
        </div>
      </Card.Body>
    </Card>
  );
};

// ── Main page ──────────────────────────────────────────────────────────────

const ConstitutionalCrisisPage: React.FC = () => {
  // Initial election config
  const [candidates, setCandidates] = useState<CandidateConfig[]>([
    newCandidate('Alice', -0.4),
    newCandidate('Bob', 0.4),
    newBlankCandidate(),
  ]);
  const [electorate, setElectorate] = useState<ElectorateState>({
    numVoters: 500,
    ideologyPreset: 'polarized',
    dissatisfactionRate: 0.45,
  });

  // Initial simulation
  const [initResult, setInitResult]   = useState<ScenarioResult | null>(null);
  const [initLoading, setInitLoading] = useState(false);
  const [initError, setInitError]     = useState<string | null>(null);

  // Scenario results
  const [resA, setResA] = useState<ConstitutionalResult | null>(null);
  const [resB, setResB] = useState<ConstitutionalResult | null>(null);
  const [resC, setResC] = useState<ConstitutionalResult | null>(null);
  const [loadA, setLoadA] = useState(false);
  const [loadB, setLoadB] = useState(false);
  const [loadC, setLoadC] = useState(false);

  const realCandidates = candidates.filter((c) => !c.isBlank);
  const blankWins = initResult
    ? Object.values(initResult.with_blank.methods).some(
        (m) => m.winner === 'Blank' || m.blank_rule_applied?.blank_triggered
      )
    : false;

  const baseInitialElection = {
    candidates: toApiCandidates(candidates),
    electorate: toApiElectorate(electorate),
    blank_rule: 'competitive',
  };

  const runInitial = async () => {
    setInitLoading(true);
    setInitError(null);
    setInitResult(null);
    try {
      const r = await runScenario({
        candidates: toApiCandidates(candidates),
        electorate: toApiElectorate(electorate),
        blank_rule: 'competitive',
        methods: ['plurality', 'irv', 'borda', 'schulze', 'approval'],
      });
      setInitResult(r);
    } catch {
      setInitError('Simulation échouée. Vérifiez que le backend est démarré.');
    } finally {
      setInitLoading(false);
    }
  };

  const runA = async (round2: CandidateConfig[]) => {
    setLoadA(true);
    try {
      const r = await runConstitutionalScenario({
        initial_election: baseInitialElection,
        blank_triggered: blankWins,
        scenario_type: 'new_election',
        params: { new_candidates: toApiCandidates(round2) },
      });
      setResA(r);
    } finally { setLoadA(false); }
  };

  const runB = async (duration: 3 | 6, drift: number) => {
    setLoadB(true);
    try {
      const r = await runConstitutionalScenario({
        initial_election: baseInitialElection,
        blank_triggered: blankWins,
        scenario_type: 'provisional',
        params: { provisional_duration: duration, drift_magnitude: drift },
      });
      setResB(r);
    } finally { setLoadB(false); }
  };

  const runC = async (numSeats: number) => {
    setLoadC(true);
    try {
      const r = await runConstitutionalScenario({
        initial_election: baseInitialElection,
        blank_triggered: blankWins,
        scenario_type: 'dissolution',
        params: { num_seats: numSeats },
      });
      setResC(r);
    } finally { setLoadC(false); }
  };

  return (
    <Container className="py-4" style={{ maxWidth: 960 }}>
      <h2 className="mb-1">Simulateur de crise constitutionnelle</h2>
      <p className="text-muted mb-4">
        Que se passe-t-il <em>après</em> que le vote blanc a gagné ? Trois modèles constitutionnels pour explorer les conséquences.
      </p>

      {/* Initial election config */}
      <Card className="mb-4">
        <Card.Header className="fw-semibold d-flex justify-content-between align-items-center">
          Configuration de l'élection initiale
          <Button variant="primary" size="sm" onClick={runInitial} disabled={initLoading || realCandidates.length < 2}>
            {initLoading ? <><Spinner size="sm" className="me-2" />Simulation…</> : '▶ Simuler l\'élection initiale'}
          </Button>
        </Card.Header>
        <Card.Body>
          <Row className="g-4">
            <Col md={7}>
              <p className="fw-semibold small text-muted mb-2">Candidats</p>
              <CandidateEditor candidates={candidates} onChange={setCandidates} />
            </Col>
            <Col md={5}>
              <p className="fw-semibold small text-muted mb-2">Électorat</p>
              <ElectorateConfig config={electorate} onChange={(p) => setElectorate((e) => ({ ...e, ...p }))} />
            </Col>
          </Row>
        </Card.Body>
      </Card>

      {initError && <Alert variant="danger">{initError}</Alert>}

      {!initResult && !initLoading && (
        <Alert variant="info">
          Configurez l'élection et cliquez <strong>Simuler l'élection initiale</strong>.
          Pour que les scénarios constitutionnels se déclenchent, le taux d'insatisfaction doit être assez élevé
          et le vote blanc doit être victorieux.
        </Alert>
      )}

      {initResult && (
        <>
          <InitialResultsBanner results={initResult} candidates={candidates} />

          {!blankWins && (
            <Alert variant="warning">
              Le vote blanc n'a pas gagné dans cette configuration. Augmentez le taux d'insatisfaction
              ou réduisez l'offre politique pour déclencher un scénario de crise.
            </Alert>
          )}

          {blankWins && (
            <Tabs defaultActiveKey="A" className="mb-3">
              <Tab
                eventKey="A"
                title={<span>🗳️ A — Nouvelle élection</span>}
              >
                <Card>
                  <Card.Body>
                    <ScenarioAPanel
                      initialCandidates={candidates}
                      result={resA}
                      loading={loadA}
                      onRun={runA}
                    />
                  </Card.Body>
                </Card>
              </Tab>

              <Tab
                eventKey="B"
                title={<span>⏱️ B — Gouvernement provisoire</span>}
              >
                <Card>
                  <Card.Body>
                    <ScenarioBPanel
                      candidateNames={realCandidates.map((c) => c.name)}
                      result={resB}
                      loading={loadB}
                      onRun={runB}
                    />
                  </Card.Body>
                </Card>
              </Tab>

              <Tab
                eventKey="C"
                title={<span>🏛️ C — Dissolution proportionnelle</span>}
              >
                <Card>
                  <Card.Body>
                    <ScenarioCPanel
                      result={resC}
                      loading={loadC}
                      onRun={runC}
                    />
                  </Card.Body>
                </Card>
              </Tab>
            </Tabs>
          )}
        </>
      )}
    </Container>
  );
};

export default ConstitutionalCrisisPage;
