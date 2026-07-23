import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

vi.mock('../../hooks/useMetaTags', () => ({ useMetaTags: () => {} }));

import { MemoryRouter } from 'react-router';
import DecouvrirPage from '../DecouvrirPage';

// Tests run in English (jsdom); assert EN strings.
const renderPage = () =>
  render(
    <MemoryRouter>
      <DecouvrirPage />
    </MemoryRouter>
  );

const winnerText = () => screen.getByTestId('discover-winner').textContent;

describe('DecouvrirPage', () => {
  it('renders the four beats', () => {
    renderPage();
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      /more than one way to vote/i
    );
    expect(screen.getByText(/Twelve friends, one restaurant/i)).toBeInTheDocument();
    expect(screen.getByText(/Three broad ways to express a choice/i)).toBeInTheDocument();
    expect(screen.getByText(/watch it on a real electorate/i)).toBeInTheDocument();
  });

  it('the same ballots elect a different winner under each rule (live engine)', () => {
    renderPage();
    // Default rule is plurality → Pizza (the centre-squeeze first choice).
    expect(winnerText()).toMatch(/Pizza/);

    fireEvent.click(screen.getByRole('tab', { name: /Two-round/i }));
    expect(winnerText()).toMatch(/Sushi/);

    fireEvent.click(screen.getByRole('tab', { name: /Approval/i }));
    expect(winnerText()).toMatch(/Thaï/);

    fireEvent.click(screen.getByRole('tab', { name: /Condorcet/i }));
    expect(winnerText()).toMatch(/Thaï/);
  });

  it('the approval threshold slides the winner: favourite = Pizza, top two = Thaï, all = Tie', () => {
    renderPage();
    fireEvent.click(screen.getByRole('tab', { name: /Approval/i }));
    expect(winnerText()).toMatch(/Thaï/); // default: approve top two

    fireEvent.click(screen.getByRole('button', { name: 'their favourite' }));
    expect(winnerText()).toMatch(/Pizza/); // approve one = plurality

    fireEvent.click(screen.getByRole('button', { name: 'all of them' }));
    expect(winnerText()).toMatch(/Tie/); // approve everyone = deadlock
  });

  it('links onward to the first story and the instrument', () => {
    renderPage();
    expect(screen.getByRole('link', { name: /spoiler effect/i })).toHaveAttribute(
      'href',
      '/playground?story=spoiler'
    );
    expect(screen.getByRole('link', { name: /Open the instrument/i })).toHaveAttribute(
      'href',
      '/playground'
    );
  });
});
