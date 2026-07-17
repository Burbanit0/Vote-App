import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

import RealElectionPanel from '../RealElectionPanel';

describe('RealElectionPanel', () => {
  it('opens on Burlington — three methods, three winners', () => {
    render(<RealElectionPanel />);
    const panel = screen.getByTestId('real-election-panel');
    expect(panel).toHaveTextContent('Burlington VT — 2009 mayor');
    expect(screen.getByTestId('real-election-headline')).toHaveTextContent('3');
    expect(panel).toHaveTextContent('Wright');
    expect(panel).toHaveTextContent('Kiss');
    expect(panel).toHaveTextContent('Montroll');
  });

  it('switches ballot box to Alaska — the Condorcet failure', () => {
    render(<RealElectionPanel />);
    fireEvent.click(screen.getByTestId('real-election-ak-2022-special'));
    const panel = screen.getByTestId('real-election-panel');
    // IRV crowns Peltola; Begich beats both rivals head-to-head yet goes out first.
    expect(panel).toHaveTextContent('Peltola');
    expect(panel).toHaveTextContent('Begich');
    expect(screen.getByTestId('real-election-headline')).toHaveTextContent('2');
    // The provenance is on screen, not just in the code.
    expect(panel).toHaveTextContent('arXiv:2303.00108');
  });

  it('marks the selected ballot box for assistive tech', () => {
    render(<RealElectionPanel />);
    const ak = screen.getByTestId('real-election-ak-2022-special');
    expect(ak).toHaveAttribute('aria-checked', 'false');
    fireEvent.click(ak);
    expect(ak).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByTestId('real-election-btv-2009')).toHaveAttribute('aria-checked', 'false');
  });
});
