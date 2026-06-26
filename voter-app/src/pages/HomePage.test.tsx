import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router';
import HomePage from './HomePage';
import { ElectionProvider } from '../stores/useElectionStore';

// The redesigned homepage makes no API calls — the hero instrument is a
// self-contained, deterministic demo. OnboardingTour mounts inert (run=false).

function renderHome() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <ElectionProvider>
        <HomePage />
      </ElectionProvider>
    </MemoryRouter>
  );
}

describe('HomePage', () => {
  it('lands the thesis and the open-instrument CTA', () => {
    renderHome();
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/method decides/i);
    expect(screen.getByRole('button', { name: /Open the instrument/i })).toBeInTheDocument();
  });

  it('the hero instrument flips the winner when the rule changes (same ballots)', () => {
    renderHome();
    // Plurality (default): the left splits → Bob wins with a minority.
    expect(screen.getByTestId('hero-winner')).toHaveTextContent('Bob');
    // Two-round runoff: the left rallies → Alice.
    fireEvent.click(screen.getByTestId('hero-rule-runoff'));
    expect(screen.getByTestId('hero-winner')).toHaveTextContent('Alice');
    // Approval: broadly approved → Carol.
    fireEvent.click(screen.getByTestId('hero-rule-approval'));
    expect(screen.getByTestId('hero-winner')).toHaveTextContent('Carol');
  });

  it('previews the five-moment journey, all linking to the playground', () => {
    renderHome();
    expect(screen.getByText('Electorate')).toBeInTheDocument();
    expect(screen.getByText('Verdict')).toBeInTheDocument();
    const toPlayground = screen
      .getAllByRole('link')
      .filter((a) => a.getAttribute('href') === '/playground');
    expect(toPlayground.length).toBeGreaterThanOrEqual(5);
  });
});
