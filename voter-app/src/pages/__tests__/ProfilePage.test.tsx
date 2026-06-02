import React from 'react';
import { render, screen } from '@testing-library/react';
import ProfilePage from '../ProfilePage';

vi.mock('../../components/User/Profile', () => {
  return { default: function MockProfile() {
    return <div data-testid="profile-component">Profile</div>;
  } };
});

describe('ProfilePage', () => {
  it('renders the Profile component', () => {
    render(<ProfilePage />);
    expect(screen.getByTestId('profile-component')).toBeInTheDocument();
  });
});
