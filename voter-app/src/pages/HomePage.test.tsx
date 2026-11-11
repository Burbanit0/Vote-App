import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter, Route, Routes } from 'react-router';
import HomePage from './HomePage';
import { ElectionProvider } from '../stores/useElectionStore';
import { STORIES } from '../lib/stories';

// The homepage makes no API calls: the hero, the count and the box are self-contained,
// deterministic demos (lib/home/).

function renderHome() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <ElectionProvider>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/playground" element={<p>playground</p>} />
        </Routes>
      </ElectionProvider>
    </MemoryRouter>
  );
}

describe('HomePage', () => {
  it('lands the thesis and offers the instrument at the top and at the end', () => {
    renderHome();
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/method decides/i);
    expect(screen.getAllByRole('button', { name: /Open the instrument/i })).toHaveLength(2);
  });

  it('opens the instrument from the last call', () => {
    renderHome();
    fireEvent.click(screen.getAllByRole('button', { name: /Open the instrument/i })[1]);
    expect(screen.getByText('playground')).toBeInTheDocument();
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

  it('walks the five moments, each linking to the playground', () => {
    renderHome();
    expect(screen.getByText('Electorate')).toBeInTheDocument();
    expect(screen.getAllByText('Verdict').length).toBeGreaterThanOrEqual(1);
    const toPlayground = screen
      .getAllByRole('link')
      .filter((a) => a.getAttribute('href') === '/playground');
    expect(toPlayground.length).toBeGreaterThanOrEqual(5);
  });

  it('lists every guided story, each opening its run', () => {
    renderHome();
    const stories = screen
      .getAllByRole('link')
      .filter((a) => a.getAttribute('href')?.startsWith('/playground?story='));
    expect(stories).toHaveLength(STORIES.length);
  });

  it('echoes the tally sheet’s rule in the strip of every method', () => {
    renderHome();
    const active = () => document.querySelector('[data-method][aria-current]');
    expect(active()).toHaveAttribute('data-method', 'plurality');
    fireEvent.click(screen.getByTestId('hero-rule-approval'));
    expect(active()).toHaveAttribute('data-method', 'approval');
  });

  it('keeps the footer’s road to Polity', () => {
    renderHome();
    expect(screen.getByTestId('home-foot-polity')).toHaveAttribute('href', '/polity');
  });
});
