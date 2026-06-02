import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import ElectorateConfig from '../ElectorateConfig';

vi.mock('recharts', () => ({
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
  const onChange = vi.fn();

  it('renders voter count slider', () => {
    render(<ElectorateConfig config={defaultConfig} onChange={onChange} />);
    expect(screen.getByText(/500/)).toBeInTheDocument();
  });

  it('renders ideology presets', () => {
    render(<ElectorateConfig config={defaultConfig} onChange={onChange} />);
    expect(screen.getByText('Centrist')).toBeInTheDocument();
    expect(screen.getByText('Polarized')).toBeInTheDocument();
    expect(screen.getByText('Random')).toBeInTheDocument();
  });

  it('renders expert presets in expert mode', () => {
    render(<ElectorateConfig config={defaultConfig} onChange={onChange} expertMode />);
    expect(screen.getByText('Left-leaning majority')).toBeInTheDocument();
    expect(screen.getByText('Right-leaning majority')).toBeInTheDocument();
  });

  it('calls onChange when clicking a preset', () => {
    const onChange = vi.fn();
    render(<ElectorateConfig config={defaultConfig} onChange={onChange} />);
    fireEvent.click(screen.getByText('Polarized'));
    expect(onChange).toHaveBeenCalledWith({ ideologyPreset: 'polarized' });
  });

  it('shows dissatisfaction in expert mode', () => {
    render(<ElectorateConfig config={defaultConfig} onChange={onChange} expertMode />);
    expect(screen.getByText(/General dissatisfaction rate/)).toBeInTheDocument();
  });

  it('shows dissatisfaction label for low values', () => {
    render(<ElectorateConfig config={{ ...defaultConfig, dissatisfactionRate: 0.1 }} onChange={onChange} expertMode />);
    expect(screen.getByText(/Electorate satisfied/)).toBeInTheDocument();
  });

  it('shows dissatisfaction label for high values', () => {
    render(<ElectorateConfig config={{ ...defaultConfig, dissatisfactionRate: 0.8 }} onChange={onChange} expertMode />);
    expect(screen.getByText(/Representation crisis/)).toBeInTheDocument();
  });
});
