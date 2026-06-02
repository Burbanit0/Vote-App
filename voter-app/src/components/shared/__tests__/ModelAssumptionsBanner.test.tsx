import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ModelAssumptionsBanner from '../ModelAssumptionsBanner';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key.split('.').pop() ?? key,
  }),
}));

function renderBanner() {
  return render(
    <MemoryRouter>
      <ModelAssumptionsBanner />
    </MemoryRouter>
  );
}

describe('ModelAssumptionsBanner', () => {
  it('renders the banner on mount', () => {
    renderBanner();
    expect(screen.getByTestId('assumptions-banner')).toBeInTheDocument();
  });

  it('shows toggle button', () => {
    renderBanner();
    expect(screen.getByTestId('banner-toggle')).toBeInTheDocument();
  });

  it('is collapsed by default (detail not visible)', () => {
    renderBanner();
    // When collapsed, the detail section should not be visible
    // react-bootstrap Collapse hides content but doesn't remove from DOM
    // We verify the toggle button text shows expand indicator
    const toggle = screen.getByTestId('banner-toggle');
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
  });

  it('expands when toggle is clicked', () => {
    renderBanner();
    const toggle = screen.getByTestId('banner-toggle');
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
  });

  it('collapses again when toggle is clicked twice', () => {
    renderBanner();
    const toggle = screen.getByTestId('banner-toggle');
    fireEvent.click(toggle);
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
  });

  it('renders detail section with assumption badges after expand', () => {
    renderBanner();
    fireEvent.click(screen.getByTestId('banner-toggle'));
    expect(screen.getByTestId('banner-detail')).toBeInTheDocument();
  });

  it('renders link to theory page', () => {
    renderBanner();
    fireEvent.click(screen.getByTestId('banner-toggle'));
    const link = screen.getByRole('link');
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute('href', '/theory');
  });
});
