import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { afterEach, describe, expect, it } from 'vitest';
import MethodStrip from '../MethodStrip';
import { METHOD_WINNERS } from '@/lib/home/methods';
import { fakeMedia } from '../../../test/frames';

const realMatchMedia = window.matchMedia;
afterEach(() => {
  window.matchMedia = realMatchMedia;
});

const item = (rule: string) => document.querySelector(`[data-method="${rule}"]`) as HTMLElement;
const slip = (rule: string) => item(rule).querySelector('button')!;
const caption = () => screen.getByTestId('home-methods').querySelector('p')!;
const list = () => screen.getByRole('list', { name: /each slip/i });

describe('MethodStrip', () => {
  it('lays out one slip per method, each named for screen readers', () => {
    render(<MethodStrip active="plurality" play />);
    expect(screen.getAllByRole('button')).toHaveLength(METHOD_WINNERS.length);
    expect(screen.getByRole('button', { name: 'Borda elects Carol.' })).toBeInTheDocument();
    expect(screen.getByText('24')).toBeInTheDocument();
  });

  it('marks the rule picked on the tally sheet as current, and names it', () => {
    const { rerender } = render(<MethodStrip active="plurality" play />);
    expect(item('plurality')).toHaveAttribute('aria-current', 'true');
    expect(caption()).toHaveTextContent('elects Bob. Each slip is a counting method');
    rerender(<MethodStrip active="runoff" play={false} />);
    expect(item('plurality')).not.toHaveAttribute('aria-current');
    expect(item('two_round')).toHaveAttribute('aria-current', 'true');
    expect(caption()).toHaveTextContent('elects Alice.');
  });

  it('names the method under the mouse, then goes back to the picked rule', () => {
    render(<MethodStrip active="approval" play />);
    fireEvent.pointerEnter(slip('kemeny'), { pointerType: 'mouse' });
    expect(caption()).toHaveTextContent('Kemeny-Young elects Carol.');
    expect(caption()).not.toHaveTextContent('Each slip');
    fireEvent.pointerLeave(list(), { pointerType: 'mouse' });
    expect(caption()).toHaveTextContent('Each slip');
  });

  it('names a tapped slip, and a finger lifting off does not take it back', () => {
    render(<MethodStrip active="plurality" play />);
    fireEvent.pointerEnter(slip('borda'), { pointerType: 'touch' });
    expect(caption()).toHaveTextContent('Each slip');
    fireEvent.click(slip('borda'));
    fireEvent.pointerLeave(list(), { pointerType: 'touch' });
    expect(caption()).toHaveTextContent('Borda elects Carol.');
  });

  it('is one tab stop the arrow keys move along, naming each slip as it goes', () => {
    render(<MethodStrip active="plurality" play />);
    const first = slip(METHOD_WINNERS[0].rule);
    const second = slip(METHOD_WINNERS[1].rule);
    const last = slip(METHOD_WINNERS[METHOD_WINNERS.length - 1].rule);
    expect(first).toHaveAttribute('tabindex', '0');
    expect(second).toHaveAttribute('tabindex', '-1');
    first.focus();
    fireEvent.keyDown(first, { key: 'ArrowRight' });
    expect(second).toHaveFocus();
    expect(second).toHaveAttribute('tabindex', '0');
    expect(caption()).toHaveTextContent('Two-round runoff elects Alice.');
    fireEvent.keyDown(second, { key: 'Enter' });
    expect(second).toHaveFocus();
    fireEvent.keyDown(second, { key: 'ArrowLeft' });
    fireEvent.keyDown(first, { key: 'ArrowLeft' });
    expect(last).toHaveFocus();
    fireEvent.blur(last);
    expect(caption()).toHaveTextContent('Each slip');
  });

  it('clears away with the hero during the handover, on a desktop only', () => {
    const { unmount } = render(<MethodStrip active="plurality" play />);
    expect(screen.getByTestId('home-methods')).not.toHaveAttribute('data-handover-out');
    unmount();
    fakeMedia({ 'min-width': true });
    render(<MethodStrip active="plurality" play />);
    const strip = screen.getByTestId('home-methods');
    expect(strip).toHaveAttribute('data-handover-out');
    expect(strip.style.opacity).toContain('--handover');
  });
});
