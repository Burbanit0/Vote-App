import React from 'react';
import { render, screen } from '@testing-library/react';
import OfflineBanner from '../OfflineBanner';

function setOnline(online: boolean) {
  Object.defineProperty(navigator, 'onLine', {
    configurable: true,
    value: online,
  });
}

describe('OfflineBanner', () => {
  beforeEach(() => {
    setOnline(true);
  });

  it('renders nothing when online', () => {
    setOnline(true);
    const { container } = render(<OfflineBanner />);
    expect(container.innerHTML).toBe('');
  });

  it('renders banner text when offline', () => {
    setOnline(false);
    render(<OfflineBanner />);
    expect(
      screen.getByText(/Mode hors-ligne/)
    ).toBeInTheDocument();
  });
});
