import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import {
  AnimationBroadcastProvider,
  useAnimationBroadcast,
  AnimationFrame,
} from './AnimationBroadcastContext';
import { useLabStore } from '../stores/useLabStore';

const FRAME: AnimationFrame = {
  method:        'irv',
  step:          2,
  totalSteps:    3,
  eliminated:    'Bob',
  eliminatedSet: ['Alice', 'Bob'],
  transfers:     { Charlie: 0.6, Dave: 0.4 },
  currentWinner: null,
  final:         false,
};

const TestConsumer: React.FC = () => {
  const { frame, publish, clear } = useAnimationBroadcast();
  return (
    <div>
      <span data-testid="method">{frame?.method ?? 'none'}</span>
      <span data-testid="step">{frame?.step ?? 0}</span>
      <span data-testid="eliminated">{frame?.eliminated ?? '-'}</span>
      <span data-testid="elim-set">{(frame?.eliminatedSet ?? []).join(',')}</span>
      <span data-testid="transfers">
        {Object.entries(frame?.transfers ?? {})
          .map(([k, v]) => `${k}:${v}`)
          .join('|')}
      </span>
      <button data-testid="pub" onClick={() => publish(FRAME)}>publish</button>
      <button data-testid="clear" onClick={() => clear()}>clear</button>
      <button data-testid="pub-null" onClick={() => publish(null)}>publish null</button>
    </div>
  );
};

describe('AnimationBroadcastContext', () => {
  beforeEach(() => {
    useLabStore.setState({ frame: null });
  });

  it('starts with no frame', () => {
    render(
      <AnimationBroadcastProvider>
        <TestConsumer />
      </AnimationBroadcastProvider>
    );
    expect(screen.getByTestId('method')).toHaveTextContent('none');
    expect(screen.getByTestId('step')).toHaveTextContent('0');
  });

  it('publishes a frame visible to consumers', () => {
    render(
      <AnimationBroadcastProvider>
        <TestConsumer />
      </AnimationBroadcastProvider>
    );
    act(() => { fireEvent.click(screen.getByTestId('pub')); });
    expect(screen.getByTestId('method')).toHaveTextContent('irv');
    expect(screen.getByTestId('step')).toHaveTextContent('2');
    expect(screen.getByTestId('eliminated')).toHaveTextContent('Bob');
    expect(screen.getByTestId('elim-set')).toHaveTextContent('Alice,Bob');
    expect(screen.getByTestId('transfers')).toHaveTextContent('Charlie:0.6|Dave:0.4');
  });

  it('clear() removes the published frame', () => {
    render(
      <AnimationBroadcastProvider>
        <TestConsumer />
      </AnimationBroadcastProvider>
    );
    act(() => { fireEvent.click(screen.getByTestId('pub')); });
    expect(screen.getByTestId('method')).toHaveTextContent('irv');
    act(() => { fireEvent.click(screen.getByTestId('clear')); });
    expect(screen.getByTestId('method')).toHaveTextContent('none');
  });

  it('publish(null) clears the frame', () => {
    render(
      <AnimationBroadcastProvider>
        <TestConsumer />
      </AnimationBroadcastProvider>
    );
    act(() => { fireEvent.click(screen.getByTestId('pub')); });
    act(() => { fireEvent.click(screen.getByTestId('pub-null')); });
    expect(screen.getByTestId('method')).toHaveTextContent('none');
  });

  it('works without a provider (store-backed, no crash)', () => {
    // useAnimationBroadcast now reads useLabStore, so no provider is required.
    render(<TestConsumer />);
    expect(screen.getByTestId('method')).toHaveTextContent('none');
    act(() => { fireEvent.click(screen.getByTestId('pub')); });
    expect(screen.getByTestId('method')).toHaveTextContent('irv');
  });
});
