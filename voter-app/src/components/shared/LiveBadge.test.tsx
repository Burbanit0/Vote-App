import React from 'react';
import { render, screen } from '@testing-library/react';
import LiveBadge from './LiveBadge';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

describe('LiveBadge', () => {
  it('renders the badge text when loading is true', () => {
    render(<LiveBadge loading />);
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText('simulation.recalculating')).toBeInTheDocument();
  });

  it('renders nothing when loading is false', () => {
    const { container } = render(<LiveBadge loading={false} />);
    expect(container.firstChild).toBeNull();
  });

  it('applies className prop when provided', () => {
    render(<LiveBadge loading className="my-class" />);
    expect(screen.getByRole('status')).toHaveClass('my-class');
  });

  it('toggles visibility when loading changes', () => {
    const { rerender } = render(<LiveBadge loading />);
    expect(screen.getByRole('status')).toBeInTheDocument();

    rerender(<LiveBadge loading={false} />);
    expect(screen.queryByRole('status')).toBeNull();
  });
});
