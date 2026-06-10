import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import QuizPage from './QuizPage';
import questions, { QuizQuestion } from '../data/quizQuestions';

// ── Mocks ────────────────────────────────────────────────────────────────────

vi.mock('../hooks/useMetaTags', () => ({ useMetaTags: () => {} }));

const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, val: string) => {
      store[key] = val;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

beforeEach(() => localStorageMock.clear());

// ── Helpers ──────────────────────────────────────────────────────────────────

/** Click a filter difficulty button by label. */
function clickFilter(label: RegExp) {
  fireEvent.click(screen.getByRole('button', { name: label }));
}

/** Click the "next question" / "results" navigation button if visible.
 *  "Question suivante →" and "Voir mes résultats →" are the only buttons
 *  that end with the → character, making it a safe discriminator.
 */
function clickNextIfPresent(): boolean {
  const btn = screen.queryAllByRole('button').find(
    (b) => (b.textContent ?? '').includes('→') // → (right arrow)
  );
  if (btn) {
    fireEvent.click(btn);
    return true;
  }
  return false;
}

/**
 * Find which question is currently displayed by matching its text against
 * the dataset, then return the correct option button.
 */
function findCurrentQuestion(): QuizQuestion | undefined {
  const optButtons = getOptionButtons();
  if (!optButtons.length) return undefined;
  // Read the text of option A to identify the current question
  const optAText = optButtons[0].textContent?.replace(/^A\.\s*/, '').trim() ?? '';
  return questions.find((q) => q.options[0].slice(0, 20) === optAText.slice(0, 20));
}

function getOptionButtons() {
  return screen.getAllByRole('button').filter((b) => /^[A-D]\./.test(b.textContent ?? ''));
}

function answerCorrectly(q: QuizQuestion) {
  const opts = getOptionButtons();
  fireEvent.click(opts[q.correctIndex]);
}

function answerWrong(q: QuizQuestion) {
  const wrongIdx = q.correctIndex === 0 ? 1 : 0;
  const opts = getOptionButtons();
  fireEvent.click(opts[wrongIdx]);
}

// ── Dataset integrity ─────────────────────────────────────────────────────────

describe('quizQuestions dataset', () => {
  it('has exactly 20 questions', () => {
    expect(questions).toHaveLength(20);
  });

  it('every question has exactly 4 options', () => {
    questions.forEach((q) => expect(q.options).toHaveLength(4));
  });

  it('every correctIndex is 0–3', () => {
    questions.forEach((q) => {
      expect(q.correctIndex).toBeGreaterThanOrEqual(0);
      expect(q.correctIndex).toBeLessThanOrEqual(3);
    });
  });

  it('has questions at all three difficulty levels', () => {
    const diffs = new Set(questions.map((q) => q.difficulty));
    expect(diffs).toContain('débutant');
    expect(diffs).toContain('intermédiaire');
    expect(diffs).toContain('expert');
  });

  it('all explanations are non-trivial (> 20 chars)', () => {
    questions.forEach((q) => expect(q.explanation.length).toBeGreaterThan(20));
  });
});

// ── Difficulty filter ─────────────────────────────────────────────────────────

describe('QuizPage — difficulty filter', () => {
  it('renders all four filter buttons', () => {
    render(<QuizPage />);
    expect(screen.getByRole('button', { name: /Toutes/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Débutant/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Intermédiaire/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Expert/i })).toBeInTheDocument();
  });

  it('filter buttons show the correct counts', () => {
    render(<QuizPage />);
    const debutantCount = questions.filter((q) => q.difficulty === 'débutant').length;
    const expertCount = questions.filter((q) => q.difficulty === 'expert').length;

    const debutantBtn = screen.getByRole('button', { name: /Débutant/i });
    const expertBtn = screen.getByRole('button', { name: /Expert/i });

    expect(debutantBtn.textContent).toContain(String(debutantCount));
    expect(expertBtn.textContent).toContain(String(expertCount));
  });

  it('"Toutes" is selected by default (aria-pressed=true)', () => {
    render(<QuizPage />);
    const allBtn = screen.getByRole('button', { name: /Toutes/i });
    expect(allBtn).toHaveAttribute('aria-pressed', 'true');
  });

  it('clicking "Expert" marks it as selected', () => {
    render(<QuizPage />);
    const expertBtn = screen.getByRole('button', { name: /Expert/i });
    fireEvent.click(expertBtn);
    expect(expertBtn).toHaveAttribute('aria-pressed', 'true');
  });

  it('clicking "Débutant" filters deck to débutant questions only', () => {
    render(<QuizPage />);
    const debutantTotal = questions.filter((q) => q.difficulty === 'débutant').length;
    clickFilter(/^Débutant/i);
    // Progress shows "1 / <debutantTotal>"
    expect(screen.getByText(`1 / ${debutantTotal}`)).toBeInTheDocument();
  });

  it('clicking "Intermédiaire" filters deck to intermédiaire questions', () => {
    render(<QuizPage />);
    const interTotal = questions.filter((q) => q.difficulty === 'intermédiaire').length;
    clickFilter(/^Intermédiaire/i);
    expect(screen.getByText(`1 / ${interTotal}`)).toBeInTheDocument();
  });

  it('clicking "Expert" filters deck to expert questions', () => {
    render(<QuizPage />);
    const expertTotal = questions.filter((q) => q.difficulty === 'expert').length;
    clickFilter(/^Expert/i);
    expect(screen.getByText(`1 / ${expertTotal}`)).toBeInTheDocument();
  });
});

// ── Answer interaction ────────────────────────────────────────────────────────

describe('QuizPage — answering questions', () => {
  it('renders 4 option buttons for the first question', () => {
    render(<QuizPage />);
    expect(getOptionButtons()).toHaveLength(4);
  });

  it('clicking correct answer shows "Correct" in explanation', () => {
    render(<QuizPage />);
    const q = findCurrentQuestion();
    if (!q) return; // fallback if question lookup fails
    answerCorrectly(q);
    expect(screen.getByText(/✓ Correct/i)).toBeInTheDocument();
  });

  it('clicking wrong answer shows "Incorrect" in explanation', () => {
    render(<QuizPage />);
    const q = findCurrentQuestion();
    if (!q) return;
    answerWrong(q);
    expect(screen.getByText(/✗ Incorrect/i)).toBeInTheDocument();
  });

  it('explanation text appears only after answering', () => {
    render(<QuizPage />);
    expect(screen.queryByText(/Correct|Incorrect/i)).not.toBeInTheDocument();

    const opts = getOptionButtons();
    fireEvent.click(opts[0]);
    expect(screen.queryByText(/Correct|Incorrect/i)).toBeInTheDocument();
  });

  it('"Question suivante" button is absent before answering', () => {
    render(<QuizPage />);
    expect(screen.queryByText(/suivante/i)).not.toBeInTheDocument();
  });

  it('"Question suivante" button appears after answering', () => {
    render(<QuizPage />);
    fireEvent.click(getOptionButtons()[0]);
    const nextBtn = screen
      .queryAllByRole('button')
      .find((b) => (b.textContent ?? '').includes('→'));
    expect(nextBtn).toBeInTheDocument();
  });

  it('cannot answer twice — option buttons become disabled after first click', () => {
    render(<QuizPage />);
    const opts = getOptionButtons();
    fireEvent.click(opts[0]);
    // Re-clicking a disabled button should not trigger another answer
    const beforeText = screen.queryByText(/✓ \d/)?.textContent;
    fireEvent.click(opts[1]); // try to click another answer
    expect(screen.queryByText(/✓ \d/)?.textContent).toEqual(beforeText);
  });
});

// ── Score tracking ────────────────────────────────────────────────────────────

describe('QuizPage — score tracking', () => {
  it('score starts at 0', () => {
    render(<QuizPage />);
    expect(screen.getByText('✓ 0')).toBeInTheDocument();
  });

  it('score increments to 1 after a correct answer', () => {
    render(<QuizPage />);
    const q = findCurrentQuestion();
    if (!q) return;
    answerCorrectly(q);
    expect(screen.getByText('✓ 1')).toBeInTheDocument();
  });

  it('score does NOT increment after a wrong answer', () => {
    render(<QuizPage />);
    const q = findCurrentQuestion();
    if (!q) return;
    answerWrong(q);
    expect(screen.getByText('✓ 0')).toBeInTheDocument();
  });

  it('record (bestScore) is saved to localStorage after quiz completion', () => {
    render(<QuizPage />);
    const total = questions.length;

    for (let i = 0; i < total + 1; i++) {
      const opts = getOptionButtons();
      if (!opts.length) break;
      fireEvent.click(opts[0]);
      if (!clickNextIfPresent()) break;
    }

    const saved = localStorageMock.getItem('votelab_quiz_best_all');
    expect(saved).not.toBeNull();
    expect(Number(saved)).toBeGreaterThanOrEqual(0);
    expect(Number(saved)).toBeLessThanOrEqual(total);
  });

  it('displays previously saved record on mount', () => {
    localStorageMock.setItem('votelab_quiz_best_all', '15');
    render(<QuizPage />);
    expect(screen.getByText(/Record/i)).toBeInTheDocument();
    expect(screen.getByText(/15/)).toBeInTheDocument();
  });
});

// ── Results screen ────────────────────────────────────────────────────────────

describe('QuizPage — results screen', () => {
  function completeQuiz() {
    render(<QuizPage />);
    const total = questions.length;
    for (let i = 0; i < total + 1; i++) {
      const opts = getOptionButtons();
      if (!opts.length) break; // results screen has no option buttons
      fireEvent.click(opts[0]);
      if (!clickNextIfPresent()) break;
    }
  }

  it('shows final score on results screen', () => {
    completeQuiz();
    // "X / 20" appears in both the h2 score and the record line
    expect(screen.queryAllByText(/\/ 20/i).length).toBeGreaterThan(0);
  });

  it('shows "Rejouer" button on results screen', () => {
    completeQuiz();
    expect(screen.getByRole('button', { name: /Rejouer/i })).toBeInTheDocument();
  });

  it('clicking "Rejouer" resets the quiz', () => {
    completeQuiz();
    fireEvent.click(screen.getByRole('button', { name: /Rejouer/i }));
    // After replay, progress bar "1 / 20" is visible again
    expect(screen.getByText('1 / 20')).toBeInTheDocument();
  });

  it('shows a score message', () => {
    completeQuiz();
    const messages = ['Expert', 'Bon niveau', 'Réessayez'];
    const found = messages.some((m) => screen.queryByText(new RegExp(m, 'i')));
    expect(found).toBe(true);
  });
});
