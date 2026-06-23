import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

const runProfileSimulate = vi.fn();
vi.mock('../../../services/profileApi', () => ({
  runProfileSimulate: (...a: unknown[]) => runProfileSimulate(...a),
}));

import StrategicModule from '../StrategicModule';
import { DEFAULT_CONFIG, DEFAULT_PLAYGROUND } from '../../../stores/useElectionStore';

beforeEach(() => {
  runProfileSimulate.mockReset().mockResolvedValue({
    methods: {
      plurality: { winner: 'A', strategic_vulnerability: 0.32 },
      irv: { winner: 'A', strategic_vulnerability: 0.08 },
      condorcet: { winner: 'A', strategic_vulnerability: 0.04 },
    },
  });
});

function setup() {
  render(<StrategicModule config={DEFAULT_CONFIG} playground={DEFAULT_PLAYGROUND} />);
}

describe('StrategicModule (on-demand)', () => {
  it('computes only on demand and opts into the strategic pass', async () => {
    setup();
    // Nothing computed until asked.
    expect(screen.queryByTestId('strategic-rows')).not.toBeInTheDocument();
    expect(runProfileSimulate).not.toHaveBeenCalled();
    fireEvent.click(screen.getByTestId('strategic-run'));
    await waitFor(() => expect(screen.getByTestId('strategic-rows')).toBeInTheDocument());
    // The opt-in flag (3rd arg) is true.
    expect(runProfileSimulate.mock.calls[0][2]).toBe(true);
  });

  it('lists methods most-resistant first with their manipulability %', async () => {
    setup();
    fireEvent.click(screen.getByTestId('strategic-run'));
    await waitFor(() => expect(screen.getByTestId('strategic-rows')).toBeInTheDocument());
    const rows = screen.getByTestId('strategic-rows');
    expect(rows).toHaveTextContent('4 %'); // condorcet, lowest → first
    expect(rows).toHaveTextContent('32 %'); // plurality, highest → last
    // Ascending order: the first rendered row is the most resistant (condorcet).
    const labels = Array.from(rows.querySelectorAll('span')).map((s) => s.textContent);
    expect(labels[0]).toContain('Condorcet');
  });
});
