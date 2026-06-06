import React from 'react';
import { render, screen } from '@testing-library/react';
import UserProfilePage from '../UserProfilePage';

vi.mock('../../components/User/UserProfile', () => ({
  default: () => <div data-testid="user-profile" />,
}));

describe('UserProfilePage', () => {
  it('renders UserProfile component', () => {
    render(<UserProfilePage />);
    expect(screen.getByTestId('user-profile')).toBeInTheDocument();
  });
});
