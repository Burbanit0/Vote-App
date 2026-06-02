import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import UpdatePrompt from '../UpdatePrompt';

let mockNeedRefresh = false;
const mockUpdateServiceWorker = vi.fn();

vi.mock('virtual:pwa-register/react', () => ({
  useRegisterSW: () => ({
    needRefresh: [mockNeedRefresh],
    updateServiceWorker: mockUpdateServiceWorker,
  }),
}));

beforeEach(() => {
  mockNeedRefresh = false;
  vi.clearAllMocks();
});

describe('UpdatePrompt', () => {
  it('renders nothing when no update is available', () => {
    const { container } = render(<UpdatePrompt />);
    expect(container.innerHTML).toBe('');
  });

  it('shows toast when update is available', () => {
    mockNeedRefresh = true;
    render(<UpdatePrompt />);
    expect(screen.getByText(/Vote Lab a été mis à jour/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Recharger/ })).toBeInTheDocument();
  });

  it('calls updateServiceWorker on Recharger click', () => {
    mockNeedRefresh = true;
    render(<UpdatePrompt />);
    fireEvent.click(screen.getByRole('button', { name: /Recharger/ }));
    expect(mockUpdateServiceWorker).toHaveBeenCalledWith(true);
  });


});
