import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import ElectorateConfig from '../ElectorateConfig';

jest.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  AreaChart: ({ children }: any) => <div>{children}</div>,
  Area: () => <div />,
  XAxis: () => <div />,
}));

describe('ElectorateConfig', () => {
  const defaultConfig = {
    numVoters: 500,
    ideologyPreset: 'centrist' as const,
    dissatisfactionRate: 0.2,
  };
  const onChange = jest.fn();

  it('renders voter count slider', () => {
    render(<ElectorateConfig config={defaultConfig} onChange={onChange} />);
    expect(screen.getByText(/500/)).toBeInTheDocument();
  });

  it('renders ideology presets', () => {
    render(<ElectorateConfig config={defaultConfig} onChange={onChange} />);
    expect(screen.getByText('Centriste')).toBeInTheDocument();
    expect(screen.getByText('Polarisée')).toBeInTheDocument();
    expect(screen.getByText('Aléatoire')).toBeInTheDocument();
  });

  it('renders expert presets in expert mode', () => {
    render(<ElectorateConfig config={defaultConfig} onChange={onChange} expertMode />);
    expect(screen.getByText('Majorité gauche')).toBeInTheDocument();
    expect(screen.getByText('Majorité droite')).toBeInTheDocument();
  });

  it('calls onChange when clicking a preset', () => {
    const onChange = jest.fn();
    render(<ElectorateConfig config={defaultConfig} onChange={onChange} />);
    fireEvent.click(screen.getByText('Polarisée'));
    expect(onChange).toHaveBeenCalledWith({ ideologyPreset: 'polarized' });
  });

  it('shows dissatisfaction in expert mode', () => {
    render(<ElectorateConfig config={defaultConfig} onChange={onChange} expertMode />);
    expect(screen.getByText(/Taux d'insatisfaction générale/)).toBeInTheDocument();
  });

  it('shows dissatisfaction label for low values', () => {
    render(<ElectorateConfig config={{ ...defaultConfig, dissatisfactionRate: 0.1 }} onChange={onChange} expertMode />);
    expect(screen.getByText(/Électorat satisfait/)).toBeInTheDocument();
  });

  it('shows dissatisfaction label for high values', () => {
    render(<ElectorateConfig config={{ ...defaultConfig, dissatisfactionRate: 0.8 }} onChange={onChange} expertMode />);
    expect(screen.getByText(/Crise de représentation/)).toBeInTheDocument();
  });
});
