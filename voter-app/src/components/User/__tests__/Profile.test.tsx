import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import Profile from '../Profile';
import { fetchProfileData } from '../../../services';

vi.mock('../../../services', () => ({
  fetchProfileData: vi.fn(),
}));

const mockProfile = {
  id: 1,
  username: 'alice',
  first_name: 'Alice',
  last_name: 'Smith',
  role: 'User',
  is_admin: false,
};

// Default: user is logged in. Each test that needs a different value should
// override via the mock before rendering.
vi.mock('../../../stores/useAuthStore', async () => ({
  ...(await vi.importActual('../../../stores/useAuthStore')),
  useAuth: () => ({ user: { username: 'alice', role: 'User' } }),
}));

describe('Profile', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('shows loading state initially', () => {
    (fetchProfileData as jest.Mock).mockReturnValue(new Promise(() => {}));
    render(<Profile />);
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('renders profile card on success', async () => {
    (fetchProfileData as jest.Mock).mockResolvedValue(mockProfile);
    render(<Profile />);
    await waitFor(() => {
      expect(screen.getByText('alice')).toBeInTheDocument();
    });
    expect(screen.getByText(/Alice/)).toBeInTheDocument();
    expect(screen.getByText(/Smith/)).toBeInTheDocument();
  });

  it('shows error on API failure', async () => {
    (fetchProfileData as jest.Mock).mockRejectedValue(new Error('fail'));
    render(<Profile />);
    await waitFor(() => {
      expect(screen.getByText('Failed to fetch the profile')).toBeInTheDocument();
    });
  });
});
