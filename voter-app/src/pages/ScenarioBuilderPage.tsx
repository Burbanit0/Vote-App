import React, { useEffect, useState } from 'react';
import { Alert, Badge, Button, Card, Container, Form, Modal, Spinner, Table } from 'react-bootstrap';
import CandidateEditor, { CandidateConfig, newCandidate, newBlankCandidate } from '../components/ScenarioBuilder/CandidateEditor';
import ElectorateConfig, { ElectorateState } from '../components/ScenarioBuilder/ElectorateConfig';
import BlankVoteRuleSelector, { BlankRule } from '../components/ScenarioBuilder/BlankVoteRuleSelector';
import { runScenario, ScenarioResult } from '../services/simulationCompareApi';
import { buildShareURL, copyShareURL, decodeShareConfig, readShareParam } from '../utils/shareUtils';
import { useToast } from '../components/shared/ToastNotification';
import { useExpertMode } from '../context/ExpertModeContext';
import { useMetaTags } from '../hooks/useMetaTags';

// ── Constants ──────────────────────────────────────────────────────────────

const STEPS = ['Candidats', 'Électorat', 'Règle vote blanc', 'Résultats'];

const METHOD_LABELS: Record<string, string> = {
  plurality: 'Scrutin uninominal',
  irv: 'Scrutin préférentiel (IRV)',
  borda: 'Méthode de Borda',
  schulze: 'Méthode de Schulze',
  approval: 'Vote par approbation',
};

const CANDIDATE_COLORS = ['#4e79a7', '#e15759', '#59a14f', '#f28e2b', '#76b7b2', '#edc948'];

// ── Step indicator ─────────────────────────────────────────────────────────

const StepIndicator: React.FC<{ step: number }> = ({ step }) => (
  <div className="d-flex align-items-center mb-4">
    {STEPS.map((label, i) => (
      <React.Fragment key={i}>
        <div className="d-flex flex-column align-items-center">
          <div
            className="rounded-circle d-flex align-items-center justify-content-center fw-bold"
            style={{
              width: 36, height: 36, fontSize: '0.9rem',
              backgroundColor: i < step ? '#198754' : i === step ? '#0d6efd' : '#dee2e6',
              color: i <= step ? 'white' : '#6c757d',
            }}
          >
            {i < step ? '✓' : i + 1}
          </div>
          <small className="mt-1 text-center" style={{ fontSize: '0.72rem', maxWidth: 80, color: i === step ? '#0d6efd' : '#6c757d' }}>
            {label}
          </small>
        </div>
        {i < STEPS.length - 1 && (
          <div style={{ flex: 1, height: 2, backgroundColor: i < step ? '#198754' : '#dee2e6', margin: '0 4px', marginBottom: 20 }} />
        )}
      </React.Fragment>
    ))}
  </div>
);

// ── Results display ────────────────────────────────────────────────────────

const WinnerBadge: React.FC<{ winner: string | null; colorMap: Record<string, string> }> = ({ winner, colorMap }) => {
  if (!winner) return <span className="text-muted">—</span>;
  if (winner === 'Blank') return <Badge bg="warning" text="dark">⬜ Vote Blanc</Badge>;
  return (
    <Badge style={{ backgroundColor: colorMap[winner] ?? '#999', fontSize: '0.75rem' }}>{winner}</Badge>
  );
};

const ResultsView: React.FC<{
  results: ScenarioResult;
  candidates: CandidateConfig[];
  blankRule: BlankRule;
}> = ({ results, candidates, blankRule }) => {
  const colorMap: Record<string, string> = Object.fromEntries(
    candidates.filter((c) => !c.isBlank).map((c, i) => [c.name, CANDIDATE_COLORS[i % CANDIDATE_COLORS.length]])
  );

  const methods = Object.keys(results.without_blank.methods);
  let blankTriggeredCount = 0;
  let resultChangedCount = 0;

  methods.forEach((m) => {
    const wb = results.with_blank.methods[m];
    const no = results.without_blank.methods[m];
    if (wb?.blank_rule_applied?.blank_triggered) blankTriggeredCount++;
    if (wb?.blank_rule_applied?.winner !== no?.winner) resultChangedCount++;
  });

  return (
    <div>
      {/* Summary banner */}
      <div className="d-flex gap-3 mb-4 flex-wrap">
        <Card className="text-center px-3 py-2" style={{ minWidth: 140 }}>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#e15759' }}>
            {Math.round(results.with_blank.blank_pct * 100)}%
          </div>
          <small className="text-muted">Électeurs votent blanc</small>
        </Card>
        <Card className="text-center px-3 py-2" style={{ minWidth: 140 }}>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#f28e2b' }}>
            {resultChangedCount}/{methods.length}
          </div>
          <small className="text-muted">Résultats modifiés</small>
        </Card>
        <Card className="text-center px-3 py-2" style={{ minWidth: 140 }}>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#dc3545' }}>
            {blankTriggeredCount}/{methods.length}
          </div>
          <small className="text-muted">Crises déclenchées</small>
        </Card>
        {results.without_blank.condorcet_winner && (
          <Card className="text-center px-3 py-2" style={{ minWidth: 140 }}>
            <div style={{ fontSize: '0.95rem', fontWeight: 700 }}>
              <WinnerBadge winner={results.without_blank.condorcet_winner} colorMap={colorMap} />
            </div>
            <small className="text-muted">Vainqueur de Condorcet</small>
          </Card>
        )}
      </div>

      {/* Comparison table */}
      <div style={{ overflowX: 'auto' }}>
        <Table bordered size="sm">
          <thead className="table-light">
            <tr>
              <th style={{ minWidth: 160 }}>Méthode</th>
              <th className="text-center" style={{ minWidth: 120 }}>Sans vote blanc</th>
              <th className="text-center" style={{ minWidth: 120 }}>Avec vote blanc</th>
              <th className="text-center" style={{ minWidth: 90 }}>% blanc</th>
              <th style={{ minWidth: 200 }}>Conséquence</th>
            </tr>
          </thead>
          <tbody>
            {methods.map((method) => {
              const noBlank = results.without_blank.methods[method];
              const withBlank = results.with_blank.methods[method];
              const rule = withBlank?.blank_rule_applied;
              const triggered = rule?.blank_triggered ?? false;
              const winnerChanged = rule?.winner !== noBlank?.winner;

              return (
                <tr key={method} style={triggered ? { backgroundColor: '#fff8e1' } : winnerChanged ? { backgroundColor: '#e8f4e8' } : undefined}>
                  <td className="fw-semibold ps-2">{METHOD_LABELS[method] ?? method}</td>
                  <td className="text-center">
                    <WinnerBadge winner={noBlank?.winner ?? null} colorMap={colorMap} />
                  </td>
                  <td className="text-center">
                    <WinnerBadge winner={rule?.winner ?? null} colorMap={colorMap} />
                    {triggered && <span className="ms-1">🚨</span>}
                  </td>
                  <td className="text-center">
                    <strong>{Math.round(results.with_blank.blank_pct * 100)}%</strong>
                  </td>
                  <td style={{ fontSize: '0.8rem', color: triggered ? '#856404' : '#495057' }}>
                    {rule?.consequence ?? '—'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      </div>

      <small className="text-muted d-block mt-2">
        🟡 Fond jaune = crise déclenchée &nbsp;·&nbsp; 🟢 Fond vert = résultat modifié par le vote blanc
      </small>
    </div>
  );
};

// ── Main page ──────────────────────────────────────────────────────────────

const ScenarioBuilderPage: React.FC = () => {
  const [step, setStep] = useState(0);

  const [candidates, setCandidates] = useState<CandidateConfig[]>([
    newCandidate('Alice', -0.5),
    newCandidate('Bob', 0.5),
    newBlankCandidate(),
  ]);

  const [electorate, setElectorate] = useState<ElectorateState>({
    numVoters: 500,
    ideologyPreset: 'random',
    dissatisfactionRate: 0.2,
  });

  const [blankRule, setBlankRule] = useState<BlankRule>('symbolic');
  const [results, setResults] = useState<ScenarioResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [linkCopied, setLinkCopied] = useState(false);
  const [showShareModal, setShowShareModal] = useState(false);
  const [urlCopied, setUrlCopied] = useState(false);
  const toast = useToast();
  const { expertMode } = useExpertMode();

  // ── Meta tags ──────────────────────────────────────────────────────────────
  const realCandidateNames = candidates.filter((c) => !c.isBlank).map((c) => c.name).join(', ');
  useMetaTags({
    title: results
      ? `Élection simulée : ${realCandidateNames} — Vote Lab`
      : 'Constructeur de scénario électoral — Vote Lab',
    description: results
      ? `${Object.keys(results.without_blank.methods).length} méthodes comparées sur ${electorate.numVoters} électeurs avec le vote blanc.`
      : 'Configurez vos candidats, votre électorat et testez 5 méthodes de vote avec le vote blanc.',
  });

  // ── Share URL + Twitter text for results modal ─────────────────────────────
  const shareUrl = buildShareURL({ candidates, electorate, blankRule });
  const divergentLabels = results
    ? Object.entries(results.without_blank.methods)
        .filter(([m, d]) => m !== 'plurality' && d.winner !== results.without_blank.methods['plurality']?.winner && d.winner)
        .map(([, d]) => d.winner)
        .filter((w, i, arr) => arr.indexOf(w) === i)
        .slice(0, 2)
    : [];
  const twitterText = results
    ? `J'ai simulé une élection avec Vote Lab — résultat : ${divergentLabels.length >= 2 ? `${divergentLabels[0]} et ${divergentLabels[1]} élisent des vainqueurs différents` : 'les méthodes de vote changent le résultat'} ! ${shareUrl}`
    : `Testez comment votre bulletin change tout sur Vote Lab ! ${shareUrl}`;

  // Restore config from URL on mount
  useEffect(() => {
    const raw = readShareParam();
    if (!raw) return;
    const cfg = decodeShareConfig<{ candidates?: CandidateConfig[]; electorate?: ElectorateState; blankRule?: BlankRule }>(raw);
    if (!cfg) return;
    if (cfg.candidates) setCandidates(cfg.candidates);
    if (cfg.electorate) setElectorate(cfg.electorate);
    if (cfg.blankRule) setBlankRule(cfg.blankRule);
  }, []);

  const copyShareLink = async () => {
    await copyShareURL({ candidates, electorate, blankRule });
    setLinkCopied(true);
    setTimeout(() => setLinkCopied(false), 2000);
  };

  const realCandidates = candidates.filter((c) => !c.isBlank);
  const hasBlankCandidate = candidates.some((c) => c.isBlank);

  const canProceed = [
    realCandidates.length >= 2 && realCandidates.every((c) => c.name.trim()),
    true,
    true,
  ];

  const run = async () => {
    setLoading(true);
    try {
      const data = await runScenario({
        candidates: candidates.map((c) => ({
          name: c.name,
          ideology: c.ideology,
          positions: { economy: c.economy, environment: c.environment, social: c.social },
          is_blank: c.isBlank,
        })),
        electorate: {
          num_voters: electorate.numVoters,
          ideology_preset: electorate.ideologyPreset,
          dissatisfaction_rate: electorate.dissatisfactionRate,
        },
        blank_rule: blankRule,
        methods: ['plurality', 'irv', 'borda', 'schulze', 'approval'],
      });
      setResults(data);
      setStep(3);
    } catch {
      toast.error('La simulation a échoué. Vérifiez que le backend est démarré.');
    } finally {
      setLoading(false);
    }
  };

  const stepContent = [
    <CandidateEditor key="ce" candidates={candidates} onChange={setCandidates} />,
    <ElectorateConfig key="el" config={electorate} onChange={(p) => setElectorate((e) => ({ ...e, ...p }))} expertMode={expertMode} />,
    <BlankVoteRuleSelector key="bv" selected={blankRule} onChange={setBlankRule} hasBlankCandidate={hasBlankCandidate} />,
    results ? <ResultsView key="res" results={results} candidates={candidates} blankRule={blankRule} /> : null,
  ];

  return (
    <Container className="py-4" style={{ maxWidth: 900 }}>
      <h2 className="mb-1">Constructeur de scénario électoral</h2>
      <p className="text-muted mb-4">
        Configurez une élection réaliste et observez comment la méthode de vote — et la reconnaissance du vote blanc — changent le résultat.
      </p>

      <StepIndicator step={step} />

      <Card className="mb-4">
        <Card.Header className="fw-semibold">{STEPS[step]}</Card.Header>
        <Card.Body>{stepContent[step]}</Card.Body>
      </Card>



      {step < 2 && realCandidates.length < 2 && (
        <Alert variant="warning" className="py-2">
          Ajoutez au moins 2 candidats réels pour continuer.
        </Alert>
      )}

      <div className="d-flex justify-content-between">
        <div>
          {step > 0 && step < 3 && (
            <Button variant="outline-secondary" onClick={() => setStep((s) => s - 1)}>
              ← Retour
            </Button>
          )}
          {step === 3 && (
            <Button variant="outline-secondary" onClick={() => { setStep(0); setResults(null); }}>
              ↺ Recommencer
            </Button>
          )}
        </div>
        <div>
          <div className="d-flex gap-2">
          <Button variant={linkCopied ? 'success' : 'outline-info'} size="sm" onClick={copyShareLink}>
            {linkCopied ? '✓ Lien copié !' : '🔗 Partager'}
          </Button>
          {step === 3 && results && (
            <Button variant="outline-primary" size="sm" onClick={() => setShowShareModal(true)}>
              📤 Partager ces résultats
            </Button>
          )}
          {step < 2 && (
            <Button variant="primary" onClick={() => setStep((s) => s + 1)} disabled={!canProceed[step]}>
              Suivant →
            </Button>
          )}
          {step === 2 && (
            <Button variant="success" onClick={run} disabled={loading}>
              {loading ? <><Spinner size="sm" className="me-2" />Simulation en cours…</> : '▶ Lancer la simulation'}
            </Button>
          )}
        </div>
        </div>
      </div>

      {/* ── Share results modal ── */}
      <Modal show={showShareModal} onHide={() => setShowShareModal(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>📤 Partager ces résultats</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form.Label className="fw-semibold small">Lien permanent</Form.Label>
          <div className="d-flex gap-2 mb-3">
            <Form.Control size="sm" readOnly value={shareUrl} style={{ fontSize: '0.78rem' }} />
            <Button
              size="sm"
              variant={urlCopied ? 'success' : 'outline-secondary'}
              onClick={async () => {
                await navigator.clipboard.writeText(shareUrl);
                setUrlCopied(true);
                setTimeout(() => setUrlCopied(false), 2000);
              }}
            >
              {urlCopied ? '✓' : '📋'}
            </Button>
          </div>
          <Form.Label className="fw-semibold small">Texte pour Twitter / X</Form.Label>
          <Form.Control
            as="textarea"
            rows={4}
            readOnly
            value={twitterText}
            style={{ fontSize: '0.82rem', resize: 'none' }}
          />
          <div className="mt-3 d-flex gap-2">
            <a
              href={`https://twitter.com/intent/tweet?text=${encodeURIComponent(twitterText)}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              <Button variant="outline-dark" size="sm">𝕏 Ouvrir sur Twitter →</Button>
            </a>
          </div>
        </Modal.Body>
      </Modal>

    </Container>
  );
};

export default ScenarioBuilderPage;
