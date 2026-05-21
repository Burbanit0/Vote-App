import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import SenParadoxPanel from '../SenParadoxPanel';

jest.mock('axios', () => ({ post: jest.fn() }));
const { post: mockPost } = jest.requireMock('axios') as { post: jest.Mock };

function makeData(hasParadox = true) {
  return {
    data: {
      paradox_exists:    hasParadox,
      paradox_examples: hasParadox ? [{
        name:                "Exemple classique (Sen 1970)",
        voters_preferences:  [['z','x','y'], ['x','y','z']],
        private_spheres:     { voter_1: ['x','z'], voter_2: ['y','z'] },
        liberal_outcome:     'y',
        pareto_outcome:      'x',
        conflict:            true,
        explanation:         'Libéralisme : y ≻ x. Pareto : x ≻ y. Contradiction !',
      }] : [],
      paradox_frequency:   hasParadox ? 0.25 : 0,
      alternative_names:   { x: 'Personne 1 lit', y: 'Personne 2 lit', z: 'Personne ne lit' },
      resolution_options: [
        { name: 'Pareto prioritaire',      outcome: 'Efficacité',    cost: 'Liberté perdue',  theorist: 'Utilitarisme' },
        { name: 'Libéralisme prioritaire', outcome: 'Autonomie',     cost: 'Sous-optimal',    theorist: 'Sen' },
        { name: 'Restriction du domaine',  outcome: 'Paradoxe évité', cost: 'Qui décide ?',  theorist: 'Gaertner' },
        { name: 'Droits absolus',          outcome: 'Sphères OK',    cost: 'Définition',      theorist: 'Sugden' },
      ],
      real_world_analogy: 'Exemple du voisin.',
      pedagogical_note:   'Test note.',
    },
  };
}

function renderPanel() {
  return render(<MemoryRouter><SenParadoxPanel /></MemoryRouter>);
}

beforeEach(() => { jest.clearAllMocks(); jest.useFakeTimers(); });
afterEach(() => { jest.useRealTimers(); });

describe('SenParadoxPanel', () => {
  it('shows simulate button', () => {
    renderPanel();
    expect(screen.getByTestId('simulate-btn')).toBeInTheDocument();
  });

  it('shows seed input', () => {
    renderPanel();
    expect(screen.getByTestId('seed-input')).toBeInTheDocument();
  });

  it('shows prompt before first run', () => {
    renderPanel();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('calls axios.post on simulate click', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    expect(mockPost).toHaveBeenCalledWith(
      expect.stringContaining('/api/theory/sen-paradox'),
      expect.any(Object),
    );
    jest.runAllTimers();
  });

  it('shows paradox badge (danger) when paradox exists', async () => {
    mockPost.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => {
      const badge = screen.getByTestId('paradox-badge');
      expect(badge.className).toContain('bg-danger');
    });
    jest.runAllTimers();
  });

  it('shows no-paradox badge (success) when no paradox', async () => {
    mockPost.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => {
      const badge = screen.getByTestId('paradox-badge');
      expect(badge.className).toContain('bg-success');
    });
    jest.runAllTimers();
  });

  it('shows frequency badge', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('frequency-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('renders conflict viz SVG', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('conflict-viz-svg')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows paradox example when paradox exists', async () => {
    mockPost.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('paradox-example')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows resolution options', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => {
      expect(screen.getByTestId('resolution-0')).toBeInTheDocument();
      expect(screen.getByTestId('resolution-1')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('shows error on API failure', async () => {
    mockPost.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
