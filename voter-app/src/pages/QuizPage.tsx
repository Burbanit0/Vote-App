import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Alert, Badge, Button, Card, Col, Container, ProgressBar, Row } from 'react-bootstrap';
import questions, { QuizQuestion } from '../data/quizQuestions';
import { useMetaTags } from '../hooks/useMetaTags';

// ── Types & constants ───────────────────────────────────────────────────────

type Difficulty = 'all' | QuizQuestion['difficulty'];

const DIFFICULTY_LABELS: Record<Difficulty, string> = {
  all:           'Toutes',
  'débutant':    'Débutant',
  'intermédiaire':'Intermédiaire',
  'expert':      'Expert',
};

const DIFFICULTY_VARIANTS: Record<Difficulty, string> = {
  all:            'secondary',
  'débutant':     'success',
  'intermédiaire':'warning',
  'expert':       'danger',
};

const LS_KEY = (d: Difficulty) => `votelab_quiz_best_${d}`;

// ── Fisher-Yates shuffle ────────────────────────────────────────────────────

function shuffle<T>(arr: T[]): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// ── Score message ────────────────────────────────────────────────────────────

function scoreMessage(score: number, total: number): { text: string; variant: string } {
  const pct = score / total;
  if (pct > 0.75)  return { text: '🏆 Expert en théorie du vote !',  variant: 'success' };
  if (pct >= 0.5)  return { text: '👍 Bon niveau — continuez !',      variant: 'primary' };
  return              { text: '📚 Réessayez — vous progresserez !',   variant: 'warning' };
}

// ── Option button ────────────────────────────────────────────────────────────

interface OptionProps {
  text: string;
  index: number;
  chosen: number | null;
  correct: number;
  onClick: () => void;
}

const OptionButton: React.FC<OptionProps> = ({ text, index, chosen, correct, onClick }) => {
  const answered = chosen !== null;
  let variant = 'outline-secondary';
  if (answered) {
    if (index === correct)         variant = 'success';
    else if (index === chosen)     variant = 'danger';
    else                           variant = 'outline-secondary';
  }

  return (
    <Button
      variant={variant}
      className="w-100 text-start mb-2"
      style={{
        whiteSpace: 'normal',
        wordBreak: 'break-word',
        transition: 'background-color 0.25s, border-color 0.25s',
        minHeight: 44,
      }}
      onClick={!answered ? onClick : undefined}
      disabled={answered && index !== correct && index !== chosen}
      aria-pressed={answered ? index === chosen : undefined}
    >
      <span className="me-2 fw-bold" aria-hidden="true">
        {String.fromCharCode(65 + index)}.
      </span>
      {text}
      {answered && index === correct && <span className="ms-2" aria-label="bonne réponse">✓</span>}
      {answered && index === chosen && index !== correct && <span className="ms-2" aria-label="mauvaise réponse">✗</span>}
    </Button>
  );
};

// ── QuizPage ────────────────────────────────────────────────────────────────

const QuizPage: React.FC = () => {
  useMetaTags({
    title: 'Quiz — Théorie du vote — Vote Lab',
    description: '20 questions sur les méthodes de vote : pluralité, Borda, IRV, Condorcet, Arrow…',
  });

  const [difficulty, setDifficulty] = useState<Difficulty>('all');
  const [deck, setDeck]             = useState<QuizQuestion[]>([]);
  const [qIndex, setQIndex]         = useState(0);
  const [chosen, setChosen]         = useState<number | null>(null);
  const [score, setScore]           = useState(0);
  const [finished, setFinished]     = useState(false);
  const [bestScores, setBestScores] = useState<Record<Difficulty, number | null>>({
    all: null, 'débutant': null, 'intermédiaire': null, 'expert': null,
  });

  // ── Load best scores from localStorage ────────────────────────────────────
  useEffect(() => {
    const loaded: Record<Difficulty, number | null> = {
      all: null, 'débutant': null, 'intermédiaire': null, 'expert': null,
    };
    (Object.keys(loaded) as Difficulty[]).forEach((d) => {
      const raw = localStorage.getItem(LS_KEY(d));
      if (raw !== null) loaded[d] = Number(raw);
    });
    setBestScores(loaded);
  }, []);

  // ── Build a shuffled deck when difficulty or replay ────────────────────────
  const buildDeck = useCallback((diff: Difficulty) => {
    const pool = diff === 'all' ? questions : questions.filter((q) => q.difficulty === diff);
    setDeck(shuffle(pool));
    setQIndex(0);
    setChosen(null);
    setScore(0);
    setFinished(false);
  }, []);

  useEffect(() => { buildDeck(difficulty); }, [difficulty, buildDeck]);

  // ── Answer handler ────────────────────────────────────────────────────────
  const handleAnswer = (index: number) => {
    if (chosen !== null) return;
    setChosen(index);
    if (index === deck[qIndex].correctIndex) setScore((s) => s + 1);
  };

  // ── Next question ─────────────────────────────────────────────────────────
  const handleNext = () => {
    if (qIndex + 1 >= deck.length) {
      setFinished(true);
      // Save best score
      const newScore = score + (chosen === deck[qIndex].correctIndex ? 0 : 0); // already incremented
      const actualScore = chosen === deck[qIndex].correctIndex ? score : score;
      const finalScore = actualScore; // score is already updated in handleAnswer
      const prev = bestScores[difficulty];
      if (prev === null || finalScore > prev) {
        localStorage.setItem(LS_KEY(difficulty), String(finalScore));
        setBestScores((b) => ({ ...b, [difficulty]: finalScore }));
      }
    } else {
      setQIndex((i) => i + 1);
      setChosen(null);
    }
  };

  // ── Completed score (last question) ───────────────────────────────────────
  // When finished is set we need to persist the current score state
  const finalScore = useMemo(() => {
    if (!finished) return score;
    return score;
  }, [finished, score]);

  // Persist when finishing
  useEffect(() => {
    if (!finished || !deck.length) return;
    const prev = bestScores[difficulty];
    if (prev === null || finalScore > prev) {
      localStorage.setItem(LS_KEY(difficulty), String(finalScore));
      setBestScores((b) => ({ ...b, [difficulty]: finalScore }));
    }
  }, [finished]); // eslint-disable-line react-hooks/exhaustive-deps

  const current   = deck[qIndex];
  const total     = deck.length;
  const progress  = total > 0 ? Math.round(((qIndex + (chosen !== null ? 1 : 0)) / total) * 100) : 0;
  const best      = bestScores[difficulty];

  // ── Difficulty filter ─────────────────────────────────────────────────────
  const DiffFilter = (
    <div className="d-flex gap-2 flex-wrap mb-4" role="group" aria-label="Filtrer par difficulté">
      {(Object.keys(DIFFICULTY_LABELS) as Difficulty[]).map((d) => {
        const count = d === 'all' ? questions.length : questions.filter((q) => q.difficulty === d).length;
        return (
          <Button
            key={d}
            variant={difficulty === d ? DIFFICULTY_VARIANTS[d] : `outline-${DIFFICULTY_VARIANTS[d]}`}
            size="sm"
            onClick={() => setDifficulty(d)}
            aria-pressed={difficulty === d}
          >
            {DIFFICULTY_LABELS[d]}
            <Badge bg="light" text="dark" className="ms-1">{count}</Badge>
          </Button>
        );
      })}
    </div>
  );

  // ── Results screen ────────────────────────────────────────────────────────
  if (finished) {
    const { text, variant } = scoreMessage(finalScore, total);
    const isNewBest = best !== null && finalScore >= best;

    return (
      <Container className="py-5" style={{ maxWidth: 680 }}>
        <h1 className="mb-1 fw-bold">🗳️ Quiz — Théorie du vote</h1>
        {DiffFilter}

        <Card className="text-center shadow-sm">
          <Card.Body className="py-5">
            <div style={{ fontSize: '3.5rem', lineHeight: 1 }} aria-hidden="true">
              {finalScore > total * 0.75 ? '🏆' : finalScore >= total * 0.5 ? '👍' : '📚'}
            </div>
            <h2 className="mt-3 fw-bold">
              {finalScore} <span className="text-muted fw-normal">/ {total}</span>
            </h2>
            <Alert variant={variant} className="mt-3 mb-3">
              {text}
            </Alert>

            {isNewBest && (
              <Alert variant="success" className="py-2 mb-3" style={{ fontSize: '0.9rem' }}>
                🎉 Nouveau record pour ce niveau !
              </Alert>
            )}

            {best !== null && (
              <p className="text-muted small mb-4">
                Votre record ({DIFFICULTY_LABELS[difficulty]}) : <strong>{best} / {total}</strong>
              </p>
            )}

            <Row className="g-2 justify-content-center">
              <Col xs="auto">
                <Button variant="primary" onClick={() => buildDeck(difficulty)}>
                  🔄 Rejouer
                </Button>
              </Col>
              <Col xs="auto">
                <Button variant="outline-secondary" onClick={() => {
                  const d: Difficulty = difficulty === 'débutant' ? 'intermédiaire' : difficulty === 'intermédiaire' ? 'expert' : 'débutant';
                  setDifficulty(d);
                }}>
                  Changer de niveau
                </Button>
              </Col>
            </Row>
          </Card.Body>
        </Card>
      </Container>
    );
  }

  if (!current) return null;

  const diffBadgeVariant = DIFFICULTY_VARIANTS[current.difficulty as Difficulty] ?? 'secondary';

  // ── Question screen ───────────────────────────────────────────────────────
  return (
    <Container className="py-4" style={{ maxWidth: 680 }}>
      <div className="d-flex align-items-start justify-content-between mb-1 flex-wrap gap-2">
        <h1 className="fw-bold mb-0 h4">🗳️ Quiz — Théorie du vote</h1>
        {best !== null && (
          <span className="text-muted small align-self-center">
            Record : <strong>{best} / {total}</strong>
          </span>
        )}
      </div>

      {DiffFilter}

      {/* Progress */}
      <div className="d-flex align-items-center gap-2 mb-3">
        <ProgressBar
          now={progress}
          className="flex-grow-1"
          style={{ height: 8 }}
          aria-label={`Progression : question ${qIndex + 1} sur ${total}`}
        />
        <span className="text-muted small" style={{ whiteSpace: 'nowrap' }}>
          {qIndex + 1} / {total}
        </span>
        <span className="text-success small" style={{ whiteSpace: 'nowrap' }}>
          ✓ {score}
        </span>
      </div>

      {/* Question card */}
      <Card className="shadow-sm mb-3">
        <Card.Body>
          <div className="d-flex align-items-start justify-content-between mb-3 gap-2">
            <Badge bg={diffBadgeVariant} style={{ fontSize: '0.72rem', whiteSpace: 'nowrap' }}>
              {current.difficulty}
            </Badge>
            {current.method && (
              <Badge bg="secondary" style={{ fontSize: '0.72rem', whiteSpace: 'nowrap' }}>
                {current.method}
              </Badge>
            )}
          </div>

          {current.context && (
            <Alert variant="light" className="py-2 mb-3" style={{ fontSize: '0.88rem', borderLeft: '3px solid #0d6efd' }}>
              {current.context}
            </Alert>
          )}

          <p className="fw-semibold mb-4" style={{ fontSize: '1.05rem', lineHeight: 1.5 }}>
            {current.question}
          </p>

          {current.options.map((opt, i) => (
            <OptionButton
              key={i}
              text={opt}
              index={i}
              chosen={chosen}
              correct={current.correctIndex}
              onClick={() => handleAnswer(i)}
            />
          ))}

          {/* Explanation */}
          {chosen !== null && (
            <Alert
              variant={chosen === current.correctIndex ? 'success' : 'danger'}
              className="mt-3 mb-0"
              style={{ fontSize: '0.88rem', lineHeight: 1.55 }}
            >
              <strong>{chosen === current.correctIndex ? '✓ Correct !' : '✗ Incorrect.'}</strong>{' '}
              {current.explanation}
            </Alert>
          )}
        </Card.Body>
      </Card>

      {/* Next button */}
      {chosen !== null && (
        <div className="text-end">
          <Button variant="primary" onClick={handleNext}>
            {qIndex + 1 < total ? 'Question suivante →' : 'Voir mes résultats →'}
          </Button>
        </div>
      )}
    </Container>
  );
};

export default QuizPage;
