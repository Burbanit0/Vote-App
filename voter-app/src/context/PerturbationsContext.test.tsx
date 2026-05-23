import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { PerturbationsProvider, usePerturbations } from './PerturbationsContext';

const LS_KEY = 'votelab_pinned_perturbations';

const TestConsumer: React.FC = () => {
  const { pinned, pinPerturbation, unpinPerturbation, clearPinned, isPinned } = usePerturbations();
  return (
    <div>
      <span data-testid="count">{pinned.length}</span>
      <span data-testid="labels">{pinned.map((p) => p.label).join('|')}</span>
      <span data-testid="is-abst">{isPinned('abstention') ? 'yes' : 'no'}</span>
      <button
        data-testid="pin-abst"
        onClick={() =>
          pinPerturbation({
            type:    'abstention',
            icon:    '🗳',
            label:   'Abstention 30%',
            summary: 'Winner stable',
          })
        }
      >
        pin
      </button>
      <button
        data-testid="pin-abst-v2"
        onClick={() =>
          pinPerturbation({
            type:    'abstention',
            icon:    '🗳',
            label:   'Abstention 50%',
            summary: 'Winner changed',
            methodsChanged: 3,
            winnersByMethod: { plurality: 'A', irv: 'B' },
          })
        }
      >
        pin v2
      </button>
      <button data-testid="unpin-abst" onClick={() => unpinPerturbation('abstention')}>
        unpin
      </button>
      <button data-testid="clear" onClick={() => clearPinned()}>
        clear
      </button>
    </div>
  );
};

describe('PerturbationsContext', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('starts empty when no localStorage entry', () => {
    render(
      <PerturbationsProvider>
        <TestConsumer />
      </PerturbationsProvider>
    );
    expect(screen.getByTestId('count')).toHaveTextContent('0');
    expect(screen.getByTestId('is-abst')).toHaveTextContent('no');
  });

  it('pins a perturbation and exposes it via isPinned', () => {
    render(
      <PerturbationsProvider>
        <TestConsumer />
      </PerturbationsProvider>
    );
    act(() => { fireEvent.click(screen.getByTestId('pin-abst')); });
    expect(screen.getByTestId('count')).toHaveTextContent('1');
    expect(screen.getByTestId('labels')).toHaveTextContent('Abstention 30%');
    expect(screen.getByTestId('is-abst')).toHaveTextContent('yes');
  });

  it('upserts by type — re-pinning the same type replaces, not duplicates', () => {
    render(
      <PerturbationsProvider>
        <TestConsumer />
      </PerturbationsProvider>
    );
    act(() => { fireEvent.click(screen.getByTestId('pin-abst')); });
    act(() => { fireEvent.click(screen.getByTestId('pin-abst-v2')); });
    expect(screen.getByTestId('count')).toHaveTextContent('1');
    expect(screen.getByTestId('labels')).toHaveTextContent('Abstention 50%');
  });

  it('unpins by type', () => {
    render(
      <PerturbationsProvider>
        <TestConsumer />
      </PerturbationsProvider>
    );
    act(() => { fireEvent.click(screen.getByTestId('pin-abst')); });
    act(() => { fireEvent.click(screen.getByTestId('unpin-abst')); });
    expect(screen.getByTestId('count')).toHaveTextContent('0');
  });

  it('clears all pinned perturbations', () => {
    render(
      <PerturbationsProvider>
        <TestConsumer />
      </PerturbationsProvider>
    );
    act(() => { fireEvent.click(screen.getByTestId('pin-abst')); });
    act(() => { fireEvent.click(screen.getByTestId('clear')); });
    expect(screen.getByTestId('count')).toHaveTextContent('0');
  });

  it('persists pinned perturbations to localStorage', () => {
    render(
      <PerturbationsProvider>
        <TestConsumer />
      </PerturbationsProvider>
    );
    act(() => { fireEvent.click(screen.getByTestId('pin-abst')); });
    const raw = localStorage.getItem(LS_KEY);
    expect(raw).not.toBeNull();
    const parsed = JSON.parse(raw!);
    expect(parsed).toHaveLength(1);
    expect(parsed[0].type).toBe('abstention');
    expect(parsed[0].label).toBe('Abstention 30%');
  });

  it('restores pinned perturbations from localStorage on mount', () => {
    localStorage.setItem(
      LS_KEY,
      JSON.stringify([
        {
          id:       'abstention-123',
          type:     'abstention',
          icon:     '🗳',
          label:    'Restored',
          summary:  'From storage',
          pinnedAt: 123,
        },
      ])
    );
    render(
      <PerturbationsProvider>
        <TestConsumer />
      </PerturbationsProvider>
    );
    expect(screen.getByTestId('count')).toHaveTextContent('1');
    expect(screen.getByTestId('labels')).toHaveTextContent('Restored');
  });

  it('ignores malformed localStorage payloads', () => {
    localStorage.setItem(LS_KEY, 'not-json{');
    render(
      <PerturbationsProvider>
        <TestConsumer />
      </PerturbationsProvider>
    );
    expect(screen.getByTestId('count')).toHaveTextContent('0');
  });

  it('drops entries missing required fields when restoring', () => {
    localStorage.setItem(
      LS_KEY,
      JSON.stringify([
        { type: 'abstention', label: 'ok', summary: 's', pinnedAt: 1, icon: '🗳', id: 'a' },
        { foo: 'bar' },
        null,
      ])
    );
    render(
      <PerturbationsProvider>
        <TestConsumer />
      </PerturbationsProvider>
    );
    expect(screen.getByTestId('count')).toHaveTextContent('1');
  });

  it('returns inert fallback when used outside provider (no crash)', () => {
    render(<TestConsumer />);
    expect(screen.getByTestId('count')).toHaveTextContent('0');
    // pinning a no-op should not throw
    act(() => { fireEvent.click(screen.getByTestId('pin-abst')); });
    expect(screen.getByTestId('count')).toHaveTextContent('0');
  });
});
