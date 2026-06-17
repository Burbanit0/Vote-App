import React, { useCallback, useEffect, useMemo, useState } from 'react';
import questions, { QuizQuestion } from '../data/quizQuestions';
import { useMetaTags } from '../hooks/useMetaTags';
import { Alert } from '@/components/ui/alert';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';

// ── Tailwind-migrated (Phase 6) ──────────────────────────────────────────────
// The quiz uses many stateful Bootstrap button/badge colours (success/danger/
// outline-*), so buttons + badges are explicit Tailwind via these helpers.
const BTN_BASE =
  'inline-flex items-center justify-center gap-1 rounded-md text-sm font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none h-9 px-4 py-2';
const BTN_SM = 'h-8 px-3 text-xs';
const BTN_VARIANT: Record<string, string> = {
  primary: 'bg-primary text-primary-foreground hover:bg-primary/90',
  success: 'bg-[#198754] text-white hover:bg-[#198754]/90',
  danger: 'bg-[#dc3545] text-white hover:bg-[#dc3545]/90',
  warning: 'bg-[#ffc107] text-black hover:bg-[#ffc107]/90',
  secondary: 'bg-slate-500 text-white hover:bg-slate-500/90',
  'outline-secondary': 'border border-input bg-background hover:bg-accent',
  'outline-success': 'border border-[#198754] text-[#198754] hover:bg-[#198754]/10',
  'outline-warning': 'border border-[#ffc107] text-[#9a7400] hover:bg-[#ffc107]/10',
  'outline-danger': 'border border-[#dc3545] text-[#dc3545] hover:bg-[#dc3545]/10',
};
const btn = (variant: string) =>
  cn(BTN_BASE, BTN_VARIANT[variant] ?? BTN_VARIANT['outline-secondary']);

const BADGE_BASE = 'inline-flex items-center rounded-md px-2.5 py-0.5 text-xs font-semibold';
const BADGE_VARIANT: Record<string, string> = {
  secondary: 'bg-slate-500 text-white',
  success: 'bg-[#198754] text-white',
  warning: 'bg-[#ffc107] text-black',
  danger: 'bg-[#dc3545] text-white',
  light: 'bg-slate-100 text-slate-900',
};
const badge = (variant: string) =>
  cn(BADGE_BASE, BADGE_VARIANT[variant] ?? BADGE_VARIANT['secondary']);

// ── Types & constants ───────────────────────────────────────────────────────

type Difficulty = 'all' | QuizQuestion['difficulty'];

const DIFFICULTY_LABELS: Record<Difficulty, string> = {
  all: 'Toutes',
  débutant: 'Débutant',
  intermédiaire: 'Intermédiaire',
  expert: 'Expert',
};

const DIFFICULTY_VARIANTS: Record<Difficulty, string> = {
  all: 'secondary',
  débutant: 'success',
  intermédiaire: 'warning',
  expert: 'danger',
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
  if (pct > 0.75) return { text: '🏆 Expert en théorie du vote !', variant: 'success' };
  if (pct >= 0.5) return { text: '👍 Bon niveau — continuez !', variant: 'primary' };
  return { text: '📚 Réessayez — vous progresserez !', variant: 'warning' };
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
    if (index === correct) variant = 'success';
    else if (index === chosen) variant = 'danger';
    else variant = 'outline-secondary';
  }

  return (
    <button
      className={cn(
        btn(variant),
        'mb-2 min-h-[44px] w-full justify-start whitespace-normal break-words text-left'
      )}
      onClick={!answered ? onClick : undefined}
      disabled={answered && index !== correct && index !== chosen}
      aria-pressed={answered ? index === chosen : undefined}
    >
      <span className="mr-2 font-bold" aria-hidden="true">
        {String.fromCharCode(65 + index)}.
      </span>
      {text}
      {answered && index === correct && (
        <span className="ml-2" aria-label="bonne réponse">
          ✓
        </span>
      )}
      {answered && index === chosen && index !== correct && (
        <span className="ml-2" aria-label="mauvaise réponse">
          ✗
        </span>
      )}
    </button>
  );
};

// ── QuizPage ────────────────────────────────────────────────────────────────

const QuizPage: React.FC = () => {
  useMetaTags({
    title: 'Quiz — Théorie du vote — Vote Lab',
    description: '20 questions sur les méthodes de vote : pluralité, Borda, IRV, Condorcet, Arrow…',
  });

  const [difficulty, setDifficulty] = useState<Difficulty>('all');
  const [deck, setDeck] = useState<QuizQuestion[]>([]);
  const [qIndex, setQIndex] = useState(0);
  const [chosen, setChosen] = useState<number | null>(null);
  const [score, setScore] = useState(0);
  const [finished, setFinished] = useState(false);
  const [bestScores, setBestScores] = useState<Record<Difficulty, number | null>>({
    all: null,
    débutant: null,
    intermédiaire: null,
    expert: null,
  });

  // ── Load best scores from localStorage ────────────────────────────────────
  useEffect(() => {
    const loaded: Record<Difficulty, number | null> = {
      all: null,
      débutant: null,
      intermédiaire: null,
      expert: null,
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

  useEffect(() => {
    buildDeck(difficulty);
  }, [difficulty, buildDeck]);

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
  }, [finished]);

  const current = deck[qIndex];
  const total = deck.length;
  const progress = total > 0 ? Math.round(((qIndex + (chosen !== null ? 1 : 0)) / total) * 100) : 0;
  const best = bestScores[difficulty];

  // ── Difficulty filter ─────────────────────────────────────────────────────
  const DiffFilter = (
    <div className="mb-6 flex flex-wrap gap-2" role="group" aria-label="Filtrer par difficulté">
      {(Object.keys(DIFFICULTY_LABELS) as Difficulty[]).map((d) => {
        const count =
          d === 'all' ? questions.length : questions.filter((q) => q.difficulty === d).length;
        const v = DIFFICULTY_VARIANTS[d];
        return (
          <button
            key={d}
            className={cn(btn(difficulty === d ? v : `outline-${v}`), BTN_SM)}
            onClick={() => setDifficulty(d)}
            aria-pressed={difficulty === d}
          >
            {DIFFICULTY_LABELS[d]}
            <span className={cn(badge('light'), 'ml-1')}>{count}</span>
          </button>
        );
      })}
    </div>
  );

  // ── Results screen ────────────────────────────────────────────────────────
  if (finished) {
    const { text, variant } = scoreMessage(finalScore, total);
    const isNewBest = best !== null && finalScore >= best;

    return (
      <div data-style="tailwind" className="mx-auto w-full max-w-[680px] px-3 py-12">
        <h1 className="mb-1 text-3xl font-bold">🗳️ Quiz — Théorie du vote</h1>
        {DiffFilter}

        <Card className="text-center shadow-sm">
          <CardContent className="p-6 py-12">
            <div className="text-[3.5rem] leading-none" aria-hidden="true">
              {finalScore > total * 0.75 ? '🏆' : finalScore >= total * 0.5 ? '👍' : '📚'}
            </div>
            <h2 className="mt-4 text-2xl font-bold">
              {finalScore} <span className="font-normal text-muted-foreground">/ {total}</span>
            </h2>
            <Alert variant={variant as never} className="mb-4 mt-4">
              {text}
            </Alert>

            {isNewBest && (
              <Alert variant="success" className="mb-4 py-2 text-[0.9rem]">
                🎉 Nouveau record pour ce niveau !
              </Alert>
            )}

            {best !== null && (
              <p className="mb-6 text-sm text-muted-foreground">
                Votre record ({DIFFICULTY_LABELS[difficulty]}) :{' '}
                <strong>
                  {best} / {total}
                </strong>
              </p>
            )}

            <div className="flex flex-wrap justify-center gap-2">
              <button className={btn('primary')} onClick={() => buildDeck(difficulty)}>
                🔄 Rejouer
              </button>
              <button
                className={btn('outline-secondary')}
                onClick={() => {
                  const d: Difficulty =
                    difficulty === 'débutant'
                      ? 'intermédiaire'
                      : difficulty === 'intermédiaire'
                        ? 'expert'
                        : 'débutant';
                  setDifficulty(d);
                }}
              >
                Changer de niveau
              </button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!current) return null;

  const diffBadgeVariant = DIFFICULTY_VARIANTS[current.difficulty as Difficulty] ?? 'secondary';

  // ── Question screen ───────────────────────────────────────────────────────
  return (
    <div data-style="tailwind" className="mx-auto w-full max-w-[680px] px-3 py-6">
      <div className="mb-1 flex flex-wrap items-start justify-between gap-2">
        <h1 className="mb-0 text-xl font-bold">🗳️ Quiz — Théorie du vote</h1>
        {best !== null && (
          <span className="self-center text-sm text-muted-foreground">
            Record :{' '}
            <strong>
              {best} / {total}
            </strong>
          </span>
        )}
      </div>

      {DiffFilter}

      {/* Progress */}
      <div className="mb-4 flex items-center gap-2">
        <Progress
          now={progress}
          className="h-2 flex-grow"
          aria-label={`Progression : question ${qIndex + 1} sur ${total}`}
        />
        <span className="whitespace-nowrap text-sm text-muted-foreground">
          {qIndex + 1} / {total}
        </span>
        <span className="whitespace-nowrap text-sm text-[#198754]">✓ {score}</span>
      </div>

      {/* Question card */}
      <Card className="mb-4 shadow-sm">
        <CardContent className="p-6">
          <div className="mb-4 flex items-start justify-between gap-2">
            <span className={cn(badge(diffBadgeVariant), 'whitespace-nowrap text-[0.72rem]')}>
              {current.difficulty}
            </span>
            {current.method && (
              <span className={cn(badge('secondary'), 'whitespace-nowrap text-[0.72rem]')}>
                {current.method}
              </span>
            )}
          </div>

          {current.context && (
            <Alert
              variant="light"
              className="mb-4 border-l-[3px] border-l-[#0d6efd] py-2 text-[0.88rem]"
            >
              {current.context}
            </Alert>
          )}

          <p className="mb-6 text-[1.05rem] font-semibold leading-normal">{current.question}</p>

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
              className="mb-0 mt-4 text-[0.88rem] leading-relaxed"
            >
              <strong>{chosen === current.correctIndex ? '✓ Correct !' : '✗ Incorrect.'}</strong>{' '}
              {current.explanation}
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Next button */}
      {chosen !== null && (
        <div className="text-right">
          <button className={btn('primary')} onClick={handleNext}>
            {qIndex + 1 < total ? 'Question suivante →' : 'Voir mes résultats →'}
          </button>
        </div>
      )}
    </div>
  );
};

export default QuizPage;
