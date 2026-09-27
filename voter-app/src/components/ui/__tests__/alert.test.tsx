import React from 'react';
import { render, screen } from '@testing-library/react';
import { Alert } from '../alert';

describe('Alert (shadcn/ui)', () => {
  it('renders its content with the danger variant classes', () => {
    render(<Alert variant="danger">Something went wrong</Alert>);
    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent('Something went wrong');
    expect(alert.className).toContain('border-red-300');
  });

  it('is an alert landmark whatever the variant', () => {
    // `dismissible`/`onClose` used to live here too, with a close button; no
    // caller ever passed them, so the only thing rendering that button was the
    // test that asserted it.
    render(<Alert variant="info">Heads up</Alert>);
    expect(screen.getByRole('alert')).toHaveTextContent('Heads up');
  });
});
