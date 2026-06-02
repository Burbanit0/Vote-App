import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import SensitivityTab from '../SensitivityTab';

vi.mock('../../../services/simulationCompareApi', () => ({
  getSensitivityAnalysis: vi.fn(),
}));

const mockSensitivityData = {
  results: [
    { value: 500, winners_by_method: { plurality: 'Alice' }, regret_by_method: { plurality: 0.1 } },
    { value: 1000, winners_by_method: { plurality: 'Bob' }, regret_by_method: { plurality: 0.2 } },
  ],
};

const baseConfig = {
  numVoters: 500,
  candidates: ['Alice', 'Bob'],
  ideology_distribution: 'centrist',
};

describe('SensitivityTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders parameter select and run button', () => {
    render(<SensitivityTab baseConfig={baseConfig} />);
    expect(screen.getByRole('button', { name: /Run Sensitivity/ })).toBeInTheDocument();
    expect(screen.getByText('Variable')).toBeInTheDocument();
  });

  it('calls getSensitivityAnalysis on button click', async () => {
    const { getSensitivityAnalysis } = (await import('../../../services/simulationCompareApi'));
    (getSensitivityAnalysis as jest.Mock).mockResolvedValue(mockSensitivityData);
    render(<SensitivityTab baseConfig={baseConfig} />);
    const button = screen.getByRole('button', { name: /Run Sensitivity/ });
    fireEvent.click(button);
    await waitFor(() => {
      expect(getSensitivityAnalysis).toHaveBeenCalled();
    });
  });

  it('shows loading state during analysis', async () => {
    const { getSensitivityAnalysis } = (await import('../../../services/simulationCompareApi'));
    (getSensitivityAnalysis as jest.Mock).mockReturnValue(new Promise(() => {}));
    render(<SensitivityTab baseConfig={baseConfig} />);
    fireEvent.click(screen.getByRole('button', { name: /Run Sensitivity/ }));
    expect(screen.getByText(/Running/)).toBeInTheDocument();
  });
});
