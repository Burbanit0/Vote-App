import React, { useState } from 'react';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Tab, Tabs } from '@/components/ui/bootstrap-tabs';
import { Button } from '@/components/ui/button';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Col, Container, Row } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import { Trans, useTranslation } from 'react-i18next';
import { useToast } from '../components/shared/ToastNotification';
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
  const { t } = useTranslation();
  const colorMap = Object.fromEntries(
    candidates.filter((c) => !c.isBlank).map((c, i) => [c.name, COLORS[i % COLORS.length]])
  );
  const blankPct = results.with_blank.blank_pct ?? 0;
  const blankWins = Object.values(results.with_blank.methods).some((m) => m.winner === 'Blank' || m.blank_rule_applied?.blank_triggered);

  return (
    <Card className={`mb-4 border-${blankWins ? 'danger' : 'success'}`}>
      <CardHeader className={`block space-y-0 border-b border-border px-4 py-2 bg-${blankWins ? 'danger' : 'success'} text-white`}>
        <strong>
          {blankWins ? t('crisis.blankWins') : t('crisis.blankNotDecisive')}
        </strong>
        <span className="ms-3 fw-normal" style={{ fontSize: '0.9rem' }}>
          {t('crisis.blanksVoted', { pct: Math.round(blankPct * 100) })}
        </span>
      </CardHeader>
      <CardBody className="py-2">
        <div className="d-flex flex-wrap gap-3">
          {Object.entries(results.with_blank.methods).map(([m, d]) => {
            const effective = d.blank_rule_applied?.winner ?? d.winner;
            return (
              <div key={m} style={{ fontSize: '0.82rem' }}>
                <span className="text-muted">{m} → </span>
                {effective === 'Blank' || effective == null ? (
                  <Badge variant="warning">{t('common.blankBadge')}</Badge>
                ) : (
                  <Badge style={{ backgroundColor: colorMap[effective] ?? '#999' }}>{effective}</Badge>
                )}
                {d.blank_rule_applied?.blank_triggered && <span className="ms-1 text-danger">🚨</span>}
              </div>
            );
          })}
        </div>
      </CardBody>
    </Card>
  );
};

// ── Main page ──────────────────────────────────────────────────────────────

const ConstitutionalCrisisPage: React.FC = () => {
  const { t } = useTranslation();
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
  const toast = useToast();

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
      toast.error(t('crisis.errSimFailed'));
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
      <h2 className="mb-1">{t('crisis.pageTitle')}</h2>
      <p className="text-muted mb-4"><Trans i18nKey="crisis.pageSubtitle" /></p>

      {/* Initial election config */}
      <Card className="mb-4">
        <CardHeader className="block space-y-0 border-b border-border px-4 py-2 fw-semibold d-flex justify-content-between align-items-center">
          {t('crisis.initialConfig')}
          <Button variant="primary" size="sm" onClick={runInitial} disabled={initLoading || realCandidates.length < 2}>
            {initLoading ? <><Spinner size="sm" className="me-2" />{t('crisis.simulating')}</> : t('crisis.simulateInitial')}
          </Button>
        </CardHeader>
        <CardBody>
          <Row className="g-4">
            <Col md={7}>
              <p className="fw-semibold small text-muted mb-2">{t('common.candidates')}</p>
              <CandidateEditor candidates={candidates} onChange={setCandidates} />
            </Col>
            <Col md={5}>
              <p className="fw-semibold small text-muted mb-2">{t('common.electorate')}</p>
              <ElectorateConfig config={electorate} onChange={(p) => setElectorate((e) => ({ ...e, ...p }))} />
            </Col>
          </Row>
        </CardBody>
      </Card>



      {!initResult && !initLoading && (
        <Alert variant="info">
          <Trans i18nKey="crisis.configHint" />
        </Alert>
      )}

      {initResult && (
        <>
          <InitialResultsBanner results={initResult} candidates={candidates} />

          {!blankWins && (
            <Alert variant="warning">
              {t('crisis.blankNotWon')}
            </Alert>
          )}

          {blankWins && (
            <Tabs defaultActiveKey="A" className="mb-3">
              <Tab
                eventKey="A"
                title={<span>{t('crisis.tabA')}</span>}
              >
                <Card>
                  <CardBody>
                    <ScenarioAPanel
                      initialCandidates={candidates}
                      result={resA}
                      loading={loadA}
                      onRun={runA}
                    />
                  </CardBody>
                </Card>
              </Tab>

              <Tab
                eventKey="B"
                title={<span>{t('crisis.tabB')}</span>}
              >
                <Card>
                  <CardBody>
                    <ScenarioBPanel
                      candidateNames={realCandidates.map((c) => c.name)}
                      result={resB}
                      loading={loadB}
                      onRun={runB}
                    />
                  </CardBody>
                </Card>
              </Tab>

              <Tab
                eventKey="C"
                title={<span>{t('crisis.tabC')}</span>}
              >
                <Card>
                  <CardBody>
                    <ScenarioCPanel
                      result={resC}
                      loading={loadC}
                      onRun={runC}
                    />
                  </CardBody>
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
