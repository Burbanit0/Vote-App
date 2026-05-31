/**
 * E2EVDemo — Interactive step-by-step pedagogical demo of the
 * End-to-End Verifiable (E2E-V) voting protocol (ElectionGuard style).
 *
 * 4 steps:
 *   1. Vote selection + "encryption"
 *   2. Public bulletin board — find your verification code
 *   3. Homomorphic counting — no individual decryption
 *   4. Optional self-audit — reveal your own vote
 */
import React, { useCallback, useState } from 'react';
import { $api } from '../../api/hooks';
import { useTranslation } from 'react-i18next';
import {
  Alert, Badge, Button, Card, Col, Form, Row, Spinner,
} from 'react-bootstrap';

const DEFAULT_CANDIDATES = ['Alice', 'Bob', 'Carol'];
const DEMO_VOTERS = 12;

// ── Types ─────────────────────────────────────────────────────────────────────

interface Voter {
  id:               number;
  encrypted_ballot: string;
  verification_code: string;
  vote_HIDDEN:      string;
}

interface BulletinEntry {
  encrypted_ballot:  string;
  verification_code: string;
}

interface E2EFullData {
  voters:                Voter[];
  public_bulletin_board: BulletinEntry[];
  aggregate_result:      Record<string, number>;
  winner:                string;
  audit_proof:           string;
}

// ── Step indicators ───────────────────────────────────────────────────────────

const STEP_LABELS = ['e2ev.step1', 'e2ev.step2', 'e2ev.step3', 'e2ev.step4'];

interface StepPipProps { current: number; t: (k: string) => string; }

const StepPip: React.FC<StepPipProps> = ({ current, t }) => (
  <div className="d-flex gap-2 mb-4 flex-wrap">
    {STEP_LABELS.map((key, i) => (
      <span
        key={i}
        className={`d-flex align-items-center gap-1 px-2 py-1 rounded`}
        style={{
          fontSize: '0.78rem',
          background: i < current ? '#198754' : i === current ? '#005CAB' : '#f0f0f0',
          color: i <= current ? '#fff' : '#6c757d',
        }}
      >
        {i + 1}. {t(key)}
      </span>
    ))}
  </div>
);

// ── Main component ────────────────────────────────────────────────────────────

interface Props {
  candidates?: string[];
  seed?:       number;
}

const E2EVDemo: React.FC<Props> = ({
  candidates = DEFAULT_CANDIDATES,
  seed       = 42,
}) => {
  const { t } = useTranslation();

  const [step,      setStep]      = useState(0);   // 0=idle, 1-4=steps
  const [chosen,    setChosen]    = useState('');
  const sim = $api.useMutation('post', '/api/v2/tech/e2e-demo');
  const data: E2EFullData | null = (sim.data as E2EFullData | undefined) ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('e2ev.error') : null;
  const [codeFound, setCodeFound] = useState(false);
  const [revealed,  setRevealed]  = useState(false);

  const myVoter   = data?.voters[0];
  const myCode    = myVoter?.verification_code ?? '';
  const myHidden  = myVoter?.vote_HIDDEN ?? '';

  const handleVote = useCallback(() => {
    if (!chosen) return;
    sim.mutate({ body: {
      candidates,
      num_demo_voters: DEMO_VOTERS,
      seed,
      user_vote: chosen,
    } }, {
      onSuccess: () => {
        setStep(1);
        setCodeFound(false);
        setRevealed(false);
      },
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chosen, candidates, seed, t, sim]);

  const reset = () => {
    setStep(0);
    setChosen('');
    sim.reset();
    setCodeFound(false);
    setRevealed(false);
  };

  return (
    <div data-testid="e2ev-demo">
      {step > 0 && <StepPip current={step - 1} t={t} />}

      {/* ── Step 0: idle — choose candidate ──────────────────────────── */}
      {step === 0 && (
        <div>
          <p style={{ fontSize: '0.85rem' }}>{t('e2ev.intro')}</p>
          <Form.Label className="fw-semibold" style={{ fontSize: '0.9rem' }}>
            {t('e2ev.chooseCandidate')}
          </Form.Label>
          <div className="d-flex gap-2 flex-wrap mb-3">
            {candidates.map((c) => (
              <Button
                key={c}
                size="sm"
                variant={chosen === c ? 'primary' : 'outline-secondary'}
                data-testid={`candidate-btn-${c}`}
                onClick={() => setChosen(c)}
              >
                {c}
              </Button>
            ))}
          </div>
          <Button variant="success" onClick={handleVote}
            disabled={!chosen || loading} data-testid="vote-btn">
            {loading
              ? <><Spinner size="sm" animation="border" /> {t('e2ev.encrypting')}</>
              : `🗳️ ${t('e2ev.vote')}`}
          </Button>
          {error && <Alert variant="danger" className="mt-2">{error}</Alert>}
        </div>
      )}

      {/* ── Step 1: ballot encrypted, code received ───────────────────── */}
      {step === 1 && myVoter && (
        <div data-testid="step1-content">
          <Alert variant="success">
            <div className="fw-bold mb-1">{t('e2ev.step1Done')}</div>
            <div style={{ fontSize: '0.85rem' }}>{t('e2ev.step1Desc')}</div>
          </Alert>

          <Card className="mb-3" style={{ background: '#f8f9fa' }}>
            <Card.Body>
              <Row>
                <Col xs={12} md={6}>
                  <div className="text-muted" style={{ fontSize: '0.75rem' }}>{t('e2ev.yourBallot')}</div>
                  <code style={{ fontSize: '1.1rem', color: '#6f42c1' }}>
                    🔒 {myVoter.encrypted_ballot}
                  </code>
                </Col>
                <Col xs={12} md={6}>
                  <div className="text-muted" style={{ fontSize: '0.75rem' }}>{t('e2ev.yourCode')}</div>
                  <span
                    data-testid="my-verification-code"
                    style={{
                      fontFamily: 'monospace', fontSize: '1.1rem',
                      background: '#fff3cd', padding: '4px 8px', borderRadius: 4,
                    }}>
                    🔑 {myCode}
                  </span>
                </Col>
              </Row>
              <div className="text-muted mt-2" style={{ fontSize: '0.75rem' }}>
                {t('e2ev.codeExplain')}
              </div>
            </Card.Body>
          </Card>

          <Button variant="primary" onClick={() => setStep(2)} data-testid="next-step-btn">
            {t('e2ev.nextStep')} →
          </Button>
        </div>
      )}

      {/* ── Step 2: public bulletin board ────────────────────────────── */}
      {step === 2 && data && (
        <div data-testid="step2-content">
          <p style={{ fontSize: '0.85rem' }}>{t('e2ev.step2Desc')}</p>

          <div className="border rounded p-2 mb-3" style={{ background: '#f8f9fa', maxHeight: 260, overflowY: 'auto' }}
            data-testid="bulletin-board">
            {data.public_bulletin_board.map((entry, i) => {
              const isMyCode = entry.verification_code === myCode;
              return (
                <div
                  key={i}
                  className={`d-flex gap-2 align-items-center py-1 px-2 mb-1 rounded ${
                    isMyCode ? 'border border-warning' : ''
                  }`}
                  style={{
                    background: isMyCode ? '#fff3cd' : undefined,
                    cursor: isMyCode ? 'pointer' : 'default',
                    fontSize: '0.75rem',
                  }}
                  onClick={() => { if (isMyCode) setCodeFound(true); }}
                >
                  <code style={{ color: '#6f42c1', flex: 1 }}>🔒 {entry.encrypted_ballot}</code>
                  <span style={{ fontFamily: 'monospace', color: isMyCode ? '#856404' : '#6c757d' }}>
                    {entry.verification_code}
                    {isMyCode && <Badge bg="warning" text="dark" className="ms-1">{t('e2ev.yours')}</Badge>}
                  </span>
                </div>
              );
            })}
          </div>

          {!codeFound && (
            <Alert variant="info" style={{ fontSize: '0.8rem' }}>
              {t('e2ev.findYourCode')} <strong>{myCode}</strong>
            </Alert>
          )}
          {codeFound && (
            <Alert variant="success" data-testid="code-found-alert" style={{ fontSize: '0.8rem' }}>
              ✓ {t('e2ev.codeFound')}
            </Alert>
          )}

          <Button variant="primary" onClick={() => setStep(3)} className="mt-2" data-testid="to-step3-btn">
            {t('e2ev.nextStep')} →
          </Button>
        </div>
      )}

      {/* ── Step 3: aggregate counting ───────────────────────────────── */}
      {step === 3 && data && (
        <div data-testid="step3-content">
          <Alert variant="info" style={{ fontSize: '0.82rem' }}>
            <strong>∑ {t('e2ev.step3Title')}</strong>
            <br />{t('e2ev.step3Desc')}
          </Alert>

          <div className="d-flex flex-wrap gap-3 mb-3" data-testid="aggregate-display">
            {Object.entries(data.aggregate_result)
              .sort((a, b) => b[1] - a[1])
              .map(([cand, count]) => (
                <div key={cand} className="text-center border rounded p-2">
                  <div style={{ fontWeight: 700, fontSize: '0.85rem' }}>{cand}</div>
                  <div style={{ fontSize: '1.6rem', color: '#005CAB', fontWeight: 900 }}>{count}</div>
                  {cand === data.winner && (
                    <Badge bg="success" style={{ fontSize: '0.65rem' }}>🏆 {t('e2ev.winner')}</Badge>
                  )}
                </div>
              ))}
          </div>

          <Alert variant="secondary" style={{ fontSize: '0.78rem' }}>
            🔒 {data.audit_proof}
          </Alert>

          <Button variant="outline-secondary" size="sm" onClick={() => setStep(4)}
            className="mt-1" data-testid="to-step4-btn">
            {t('e2ev.revealOption')} (optionnel) →
          </Button>
          <Button variant="outline-danger" size="sm" onClick={reset} className="mt-1 ms-2">
            {t('e2ev.reset')}
          </Button>
        </div>
      )}

      {/* ── Step 4: self-audit (reveal) ──────────────────────────────── */}
      {step === 4 && myVoter && (
        <div data-testid="step4-content">
          <p style={{ fontSize: '0.85rem' }}>{t('e2ev.step4Desc')}</p>

          {!revealed && (
            <Button variant="warning" onClick={() => setRevealed(true)}
              data-testid="reveal-btn">
              🔓 {t('e2ev.revealMyVote')}
            </Button>
          )}

          {revealed && (
            <Alert variant="success" data-testid="revealed-result">
              <div className="fw-bold">{t('e2ev.revealResult')}</div>
              <div style={{ fontSize: '0.85rem' }}>
                {t('e2ev.yourBallot')}: <code>🔒 {myVoter.encrypted_ballot}</code><br />
                {t('e2ev.decrypts')}: <strong>{myHidden}</strong><br />
                {t('e2ev.codeWas')}: <code>{myCode}</code><br />
                {t('e2ev.consistent')}: ✓
              </div>
            </Alert>
          )}

          <Button variant="outline-danger" size="sm" onClick={reset} className="mt-2 d-block">
            {t('e2ev.reset')}
          </Button>
        </div>
      )}
    </div>
  );
};

export default E2EVDemo;
