import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router';
import HomePage from './HomePage';

// HomePage uses useNavigate, so it must be wrapped in a router.
const renderWithRouter = (ui: React.ReactElement) =>
  render(<MemoryRouter>{ui}</MemoryRouter>);

describe('HomePage', () => {
  it('renders the main title', () => {
    renderWithRouter(<HomePage />);
    expect(screen.getByText('Voting Methods Sandbox')).toBeInTheDocument();
  });

  it('renders the subtitle', () => {
    renderWithRouter(<HomePage />);
    expect(
      screen.getByText(/research tool for studying/i)
    ).toBeInTheDocument();
  });

  it('renders the 3 feature cards', () => {
    renderWithRouter(<HomePage />);
    expect(screen.getByText('15 Voting Methods')).toBeInTheDocument();
    expect(screen.getByText('Strategic Voting')).toBeInTheDocument();
    expect(screen.getByText('Scenario Analysis')).toBeInTheDocument();
  });

  it('renders the navigation buttons', () => {
    renderWithRouter(<HomePage />);
    expect(screen.getByText('Run Simulation')).toBeInTheDocument();
    expect(screen.getByText('Compare Methods')).toBeInTheDocument();
  });
});
