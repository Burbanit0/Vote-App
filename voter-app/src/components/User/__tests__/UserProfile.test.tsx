import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import UserProfile from '../UserProfile';
import { fetchUserProfile } from '../../../services';

vi.mock('../../../services', () => ({
  fetchUserProfile: vi.fn(),
}));

vi.mock('react-router', () => ({
  useParams: () => ({ id: '42' }),
}));

const mockProfile = {
  id: 42,
  username: 'alice',
  first_name: 'Alice',
  last_name: 'Smith',
  role: 'User',
  is_admin: false,
};

describe('UserProfile', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('shows loading state initially', () => {
    (fetchUserProfile as jest.Mock).mockReturnValue(new Promise(() => {}));
    render(<UserProfile />);
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('renders profile data on success', async () => {
    (fetchUserProfile as jest.Mock).mockResolvedValue(mockProfile);
    render(<UserProfile />);
    await waitFor(() => {
      expect(screen.getByText('User Profile')).toBeInTheDocument();
    });
    expect(screen.getByText('alice')).toBeInTheDocument();
    expect(screen.getByText(/Alice/)).toBeInTheDocument();
    expect(screen.getByText(/Smith/)).toBeInTheDocument();
  });

  it('shows error message on failure', async () => {
    (fetchUserProfile as jest.Mock).mockRejectedValue(new Error('fail'));
    render(<UserProfile />);
    await waitFor(() => {
      expect(screen.getByText('Failed to fetch the user profile')).toBeInTheDocument();
    });
  });
});
