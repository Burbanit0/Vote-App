import React from 'react';
import { render, screen } from '@testing-library/react';
import ProfilePage from '../ProfilePage';

jest.mock('../../components/User/Profile', () => {
  return function MockProfile() {
    return <div data-testid="profile-component">Profile</div>;
  };
});

describe('ProfilePage', () => {
  it('renders the Profile component', () => {
    render(<ProfilePage />);
    expect(screen.getByTestId('profile-component')).toBeInTheDocument();
  });
});
