import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import DatasetExportModal from '../DatasetExportModal';

const mockFetch = vi.fn();
global.fetch = mockFetch;
global.URL.createObjectURL = vi.fn(() => 'blob:mock');
global.URL.revokeObjectURL = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
});

const csvBody = 'scenario_id,num_candidates,num_voters,method,winner\n1,4,200,plurality,Alice\n2,4,200,borda,Bob';

describe('DatasetExportModal', () => {
  it('does not render when show is false', () => {
    const { container } = render(
      <DatasetExportModal show={false} onHide={vi.fn()} />
    );
    expect(container.innerHTML).toBe('');
  });

  it('renders form controls when show is true', () => {
    render(<DatasetExportModal show={true} onHide={vi.fn()} />);
    expect(screen.getByText(/Export simulation dataset/)).toBeInTheDocument();
    expect(screen.getByText(/Number of scenarios/)).toBeInTheDocument();
    expect(screen.getByText(/Candidates/)).toBeInTheDocument();
    expect(screen.getByText(/Format/)).toBeInTheDocument();
    expect(screen.getByText(/Columns to include/)).toBeInTheDocument();
  });

  it('shows CSV and JSON format buttons (lowercase text)', () => {
    render(<DatasetExportModal show={true} onHide={vi.fn()} />);
    expect(screen.getByText('csv')).toBeInTheDocument();
    expect(screen.getByText('json')).toBeInTheDocument();
  });

  it('generates CSV and shows preview on successful fetch', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      text: () => Promise.resolve(csvBody),
    });

    render(<DatasetExportModal show={true} onHide={vi.fn()} />);

    fireEvent.click(screen.getByText(/Generate CSV/));

    await waitFor(() => {
      expect(screen.getByText(/Preview/)).toBeInTheDocument();
    });

    expect(screen.getByText(/scenario_id/)).toBeInTheDocument();
    expect(screen.getByText(/Download/)).toBeInTheDocument();
  });

  it('shows error on failed fetch', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      statusText: 'Bad Request',
      json: () => Promise.resolve({ error: 'Invalid parameters' }),
    });

    render(<DatasetExportModal show={true} onHide={vi.fn()} />);

    fireEvent.click(screen.getByText(/Generate CSV/));

    await waitFor(() => {
      expect(screen.getByText('Invalid parameters')).toBeInTheDocument();
    });
  });

  it('calls onHide when close button is clicked', () => {
    const onHide = vi.fn();
    render(<DatasetExportModal show={true} onHide={onHide} />);

    const closeButton = screen.getByLabelText(/Close/);
    fireEvent.click(closeButton);

    expect(onHide).toHaveBeenCalled();
  });

  it('generates JSON format when JSON button is clicked', async () => {
    const jsonResponse = {
      meta: { num_scenarios: 10, num_candidates: 4, num_voters: 200, seed: 42, ideology: 'random', total_rows: 2 },
      columns: ['scenario_id', 'num_candidates', 'winner'],
      rows: [
        { scenario_id: 1, num_candidates: 4, winner: 'Alice' },
        { scenario_id: 2, num_candidates: 4, winner: 'Bob' },
      ],
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(jsonResponse),
    });

    render(<DatasetExportModal show={true} onHide={vi.fn()} />);

    fireEvent.click(screen.getByText('json'));
    fireEvent.click(screen.getByText(/Generate JSON/));

    await waitFor(() => {
      expect(screen.getByText(/Preview/)).toBeInTheDocument();
    });
  });

  it('toggles column groups by clicking checkbox', () => {
    render(<DatasetExportModal show={true} onHide={vi.fn()} />);

    const blankVote = screen.getByText(/Blank vote/);
    fireEvent.click(blankVote);
  });

  it('triggers download when download button is clicked', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      text: () => Promise.resolve(csvBody),
    });

    render(<DatasetExportModal show={true} onHide={vi.fn()} />);

    fireEvent.click(screen.getByText(/Generate CSV/));

    await waitFor(() => {
      expect(screen.getByText(/Download/)).toBeInTheDocument();
    });

    const downloadButton = screen.getByText(/Download/);
    fireEvent.click(downloadButton);
  });
});
