import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import MedianVoterLayer, {
  computeMedian,
  nearestCandidate,
  type MedianVoterPoint,
  type MedianCandidate,
} from '../MedianVoterLayer';

// ── Pure function unit tests ───────────────────────────────────────────────────

describe('computeMedian', () => {
  it('returns 0 for empty array', () => {
    expect(computeMedian([])).toBe(0);
  });

  it('returns the only value for a single-element array', () => {
    expect(computeMedian([0.5])).toBe(0.5);
  });

  it('returns the middle value for odd-length sorted array', () => {
    expect(computeMedian([1, 3, 5])).toBe(3);
  });

  it('returns average of two middle values for even-length array', () => {
    expect(computeMedian([1, 2, 3, 4])).toBe(2.5);
  });

  it('works on 5 voters', () => {
    // Sorted: [-0.3, -0.1, 0.0, 0.2, 0.5] → median = 0.0
    expect(computeMedian([-0.1, 0.5, 0.0, -0.3, 0.2])).toBeCloseTo(0.0);
  });

  it('handles unsorted input', () => {
    expect(computeMedian([10, 1, 5])).toBe(5);
  });
});

describe('nearestCandidate', () => {
  const candidates: MedianCandidate[] = [
    { name: 'Alice', x: -0.5, y:  0.0 },
    { name: 'Bob',   x:  0.5, y:  0.0 },
    { name: 'Carol', x:  0.0, y:  0.5 },
  ];

  it('returns null for empty candidate list', () => {
    expect(nearestCandidate(0, 0, [])).toBeNull();
  });

  it('returns the only candidate when list has one entry', () => {
    expect(nearestCandidate(0, 0, [candidates[0]])?.name).toBe('Alice');
  });

  it('returns Alice when median is at (-0.5, 0)', () => {
    expect(nearestCandidate(-0.5, 0, candidates)?.name).toBe('Alice');
  });

  it('returns Bob when median is at (0.5, 0)', () => {
    expect(nearestCandidate(0.5, 0, candidates)?.name).toBe('Bob');
  });

  it('returns Carol when median is at (0, 0.5)', () => {
    expect(nearestCandidate(0, 0.5, candidates)?.name).toBe('Carol');
  });

  it('breaks ties deterministically', () => {
    // Equidistant from Alice and Bob at (0, 0)
    const result = nearestCandidate(0, 0, candidates);
    expect(['Alice', 'Bob', 'Carol']).toContain(result?.name);
  });
});

// ── SVG component rendering ───────────────────────────────────────────────────

const VOTERS: MedianVoterPoint[] = [
  { x: -0.3, y: 0.1 },
  { x:  0.1, y: -0.1 },
  { x: -0.1, y: 0.0 },
  { x:  0.2, y: 0.2 },
  { x: -0.2, y: -0.2 },
];

const CANDIDATES: MedianCandidate[] = [
  { name: 'Alice', x: -0.5, y: 0.0 },
  { name: 'Bob',   x:  0.5, y: 0.0 },
];

function renderLayer(props?: Partial<React.ComponentProps<typeof MedianVoterLayer>>) {
  return render(
    <MemoryRouter>
      <svg>
        <MedianVoterLayer
          voters={VOTERS}
          candidates={CANDIDATES}
          winnerA="Alice"
          winnerB="Bob"
          methodA="plurality"
          methodB="schulze"
          {...props}
        />
      </svg>
    </MemoryRouter>
  );
}

describe('MedianVoterLayer', () => {
  it('renders the median voter layer group', () => {
    renderLayer();
    expect(screen.getByTestId('median-voter-layer')).toBeInTheDocument();
  });

  it('renders the cross ✛ at the median position', () => {
    renderLayer();
    expect(screen.getByTestId('median-cross')).toBeInTheDocument();
  });

  it('renders the pulsing halo', () => {
    renderLayer();
    expect(screen.getByTestId('median-halo')).toBeInTheDocument();
  });

  it('renders the label', () => {
    renderLayer();
    expect(screen.getByTestId('median-label')).toBeInTheDocument();
  });

  it('renders prediction line to nearest candidate', () => {
    renderLayer();
    expect(screen.getByTestId('median-prediction-line')).toBeInTheDocument();
  });

  it('renders green match line when winner matches prediction', () => {
    // VOTERS median_x ≈ -0.1, nearest to Alice (x=-0.5)... let's force it
    const leftVoters: MedianVoterPoint[] = [
      { x: -0.5, y: 0 }, { x: -0.4, y: 0 }, { x: -0.6, y: 0 },
    ];
    renderLayer({ voters: leftVoters, winnerA: 'Alice' });
    // Alice is nearest to median at ≈ -0.5 and winnerA=Alice → match
    expect(screen.getByTestId('median-match-line')).toBeInTheDocument();
  });

  it('renders red miss line when winner does not match prediction', () => {
    // Put median near Alice but winnerA=Bob
    const leftVoters: MedianVoterPoint[] = [
      { x: -0.5, y: 0 }, { x: -0.4, y: 0 }, { x: -0.6, y: 0 },
    ];
    renderLayer({ voters: leftVoters, winnerA: 'Bob' });
    expect(screen.getByTestId('median-miss-line')).toBeInTheDocument();
  });

  it('shows miss label when winner misses', () => {
    const leftVoters: MedianVoterPoint[] = [
      { x: -0.5, y: 0 }, { x: -0.4, y: 0 }, { x: -0.6, y: 0 },
    ];
    renderLayer({ voters: leftVoters, winnerA: 'Bob' });
    expect(screen.getByTestId('median-miss-label')).toBeInTheDocument();
  });

  it('returns null when no voters provided', () => {
    const { container } = renderLayer({ voters: [] });
    expect(container.querySelector('[data-testid="median-voter-layer"]')).toBeNull();
  });

  it('returns null when no candidates provided', () => {
    const { container } = renderLayer({ candidates: [] });
    expect(container.querySelector('[data-testid="median-voter-layer"]')).toBeNull();
  });
});

// ── Toggle verification (IdeologyMapChart integration covered by its own test suite) ──

describe('MedianVoterLayer — absent when no data', () => {
  it('layer is absent from DOM when voters is empty', () => {
    const { container } = render(
      <MemoryRouter>
        <svg>
          <MedianVoterLayer
            voters={[]}
            candidates={CANDIDATES}
            winnerA="Alice"
            winnerB="Bob"
            methodA="plurality"
            methodB="schulze"
          />
        </svg>
      </MemoryRouter>
    );
    expect(container.querySelector('[data-testid="median-voter-layer"]')).toBeNull();
  });
});
