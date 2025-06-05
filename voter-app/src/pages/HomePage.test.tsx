import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import HomePage from './HomePage'; // Adjust the import path as necessary

// Mock the ElectionList component
jest.mock('../components/Election/ElectionList', () => () => (
  <div data-testid="election-list">ElectionList</div>
));

describe('HomePage', () => {
  it('renders the welcome message and ElectionList component', () => {
    render(<HomePage />);

    // Check if the welcome message is rendered
    expect(screen.getByText('Welcome to the Voting System')).toBeInTheDocument();
    expect(screen.getByText('Here are the lists of the elections ongoing')).toBeInTheDocument();

    // Check if the ElectionList component is rendered
    expect(screen.getByTestId('election-list')).toBeInTheDocument();
  });
});
