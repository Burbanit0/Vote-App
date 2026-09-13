import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { Alert } from '../alert';

describe('Alert (shadcn/ui)', () => {
  it('renders its content with the danger variant classes', () => {
    render(<Alert variant="danger">Something went wrong</Alert>);
    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent('Something went wrong');
    expect(alert.className).toContain('border-red-300');
  });

  it('shows a translated, accessible close button when dismissible and calls onClose', () => {
    const onClose = vi.fn();
    render(
      <Alert dismissible onClose={onClose}>
        Dismiss me
      </Alert>
    );
    const closeButton = screen.getByLabelText(/Close/);
    fireEvent.click(closeButton);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('renders no close button when not dismissible', () => {
    render(<Alert>Static</Alert>);
    expect(screen.queryByLabelText(/Close/)).not.toBeInTheDocument();
  });
});
