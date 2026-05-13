import React from 'react';
import { render, screen } from '@testing-library/react';
import UserProfilePage from '../UserProfilePage';

jest.mock('../../components/User/UserProfile', () => () => <div data-testid="user-profile" />);

describe('UserProfilePage', () => {
  it('renders UserProfile component', () => {
    render(<UserProfilePage />);
    expect(screen.getByTestId('user-profile')).toBeInTheDocument();
  });
});
