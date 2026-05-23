import React from 'react';
import { render, screen, act, waitFor } from '@testing-library/react';
import { useApi, useApiAction } from './useApi';

interface TestProps<A> {
  fetcher: (args: A) => Promise<unknown>;
  args:    A | null;
  deps?:   unknown[];
  manual?: boolean;
}

function Harness<A>({ fetcher, args, deps = [], manual }: TestProps<A>) {
  const { data, loading, error, refetch } = useApi(fetcher, args, deps, { manual });
  return (
    <div>
      <span data-testid="loading">{loading ? 'yes' : 'no'}</span>
      <span data-testid="error">{error ?? '-'}</span>
      <span data-testid="data">{JSON.stringify(data)}</span>
      <button data-testid="refetch" onClick={() => refetch()}>refetch</button>
    </div>
  );
}

describe('useApi', () => {
  it('runs the fetcher on mount and exposes data', async () => {
    const fetcher = jest.fn().mockResolvedValue({ winner: 'Alice' });
    render(<Harness fetcher={fetcher} args={{ seed: 42 }} />);

    await waitFor(() =>
      expect(screen.getByTestId('data').textContent).toBe('{"winner":"Alice"}')
    );
    expect(screen.getByTestId('loading')).toHaveTextContent('no');
    expect(screen.getByTestId('error')).toHaveTextContent('-');
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it('does NOT fetch when args is null', async () => {
    const fetcher = jest.fn().mockResolvedValue({ winner: 'Alice' });
    render(<Harness fetcher={fetcher} args={null} />);
    // Give the effect a chance to fire (it shouldn't)
    await new Promise((r) => setTimeout(r, 50));
    expect(fetcher).not.toHaveBeenCalled();
    expect(screen.getByTestId('data')).toHaveTextContent('null');
  });

  it('exposes error.message on failure', async () => {
    const fetcher = jest.fn().mockRejectedValue(new Error('boom'));
    render(<Harness fetcher={fetcher} args={{ seed: 1 }} />);

    await waitFor(() => expect(screen.getByTestId('error')).toHaveTextContent('boom'));
    expect(screen.getByTestId('loading')).toHaveTextContent('no');
  });

  it('unwraps axios-style err.response.data.error', async () => {
    const fetcher = jest.fn().mockRejectedValue({
      response: { data: { error: 'Bad seed' } },
    });
    render(<Harness fetcher={fetcher} args={{ seed: 1 }} />);
    await waitFor(() => expect(screen.getByTestId('error')).toHaveTextContent('Bad seed'));
  });

  it('refetches when refetch() is called', async () => {
    const fetcher = jest.fn()
      .mockResolvedValueOnce({ n: 1 })
      .mockResolvedValueOnce({ n: 2 });
    render(<Harness fetcher={fetcher} args={{ seed: 1 }} />);

    await waitFor(() => expect(screen.getByTestId('data')).toHaveTextContent('{"n":1}'));
    act(() => { screen.getByTestId('refetch').click(); });
    await waitFor(() => expect(screen.getByTestId('data')).toHaveTextContent('{"n":2}'));
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it('manual mode does not fire on mount, only after refetch()', async () => {
    const fetcher = jest.fn().mockResolvedValue({ ok: true });
    render(<Harness fetcher={fetcher} args={{ seed: 1 }} manual />);

    await new Promise((r) => setTimeout(r, 30));
    expect(fetcher).not.toHaveBeenCalled();

    act(() => { screen.getByTestId('refetch').click(); });
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));
  });

  // ── useApiAction ──────────────────────────────────────────────────────────

  function ActionHarness({ fetcher }: { fetcher: (a: { x: number }) => Promise<unknown> }) {
    const { data, loading, error, run, reset } = useApiAction(fetcher);
    return (
      <div>
        <span data-testid="loading">{loading ? 'yes' : 'no'}</span>
        <span data-testid="error">{error ?? '-'}</span>
        <span data-testid="data">{JSON.stringify(data)}</span>
        <button data-testid="run" onClick={() => run({ x: 1 })}>run</button>
        <button data-testid="reset" onClick={() => reset()}>reset</button>
      </div>
    );
  }

  describe('useApiAction', () => {
    it('does not auto-fetch on mount', async () => {
      const fetcher = jest.fn().mockResolvedValue({ ok: true });
      render(<ActionHarness fetcher={fetcher} />);
      await new Promise((r) => setTimeout(r, 30));
      expect(fetcher).not.toHaveBeenCalled();
    });

    it('runs the fetcher on run() and exposes data', async () => {
      const fetcher = jest.fn().mockResolvedValue({ winner: 'Alice' });
      render(<ActionHarness fetcher={fetcher} />);
      act(() => { screen.getByTestId('run').click(); });
      await waitFor(() =>
        expect(screen.getByTestId('data').textContent).toBe('{"winner":"Alice"}')
      );
      expect(fetcher).toHaveBeenCalledWith({ x: 1 });
      expect(screen.getByTestId('loading')).toHaveTextContent('no');
    });

    it('surfaces fetcher errors', async () => {
      const fetcher = jest.fn().mockRejectedValue(new Error('boom'));
      render(<ActionHarness fetcher={fetcher} />);
      act(() => { screen.getByTestId('run').click(); });
      await waitFor(() => expect(screen.getByTestId('error')).toHaveTextContent('boom'));
    });

    it('reset() clears data/error/loading', async () => {
      const fetcher = jest.fn().mockResolvedValue({ winner: 'A' });
      render(<ActionHarness fetcher={fetcher} />);
      act(() => { screen.getByTestId('run').click(); });
      await waitFor(() => expect(screen.getByTestId('data').textContent).toBe('{"winner":"A"}'));
      act(() => { screen.getByTestId('reset').click(); });
      expect(screen.getByTestId('data')).toHaveTextContent('null');
      expect(screen.getByTestId('error')).toHaveTextContent('-');
    });

    it('drops stale responses if run() is called again before the first resolves', async () => {
      let resolveFirst: (v: unknown) => void = () => {};
      const fetcher = jest.fn<Promise<unknown>, [{ x: number }]>()
        .mockImplementationOnce(() => new Promise((r) => { resolveFirst = r; }))
        .mockResolvedValueOnce({ n: 2 });
      render(<ActionHarness fetcher={fetcher} />);
      act(() => { screen.getByTestId('run').click(); });
      act(() => { screen.getByTestId('run').click(); });
      await waitFor(() => expect(screen.getByTestId('data').textContent).toBe('{"n":2}'));
      act(() => { resolveFirst({ n: 'stale' }); });
      await new Promise((r) => setTimeout(r, 30));
      expect(screen.getByTestId('data')).toHaveTextContent('{"n":2}');
    });
  });

  it('drops stale responses when deps change mid-flight', async () => {
    let resolveFirst: (v: unknown) => void = () => {};
    const fetcher = jest.fn()
      .mockImplementationOnce(() => new Promise((r) => { resolveFirst = r; }))
      .mockResolvedValueOnce({ n: 2 });

    const { rerender } = render(<Harness fetcher={fetcher} args={{ seed: 1 }} deps={[1]} />);
    // Fire second request before first resolves
    rerender(<Harness fetcher={fetcher} args={{ seed: 2 }} deps={[2]} />);

    await waitFor(() => expect(screen.getByTestId('data')).toHaveTextContent('{"n":2}'));
    // Resolve the first (stale) — should be ignored
    act(() => { resolveFirst({ n: 'stale' }); });
    await new Promise((r) => setTimeout(r, 30));
    expect(screen.getByTestId('data')).toHaveTextContent('{"n":2}');
  });
});
