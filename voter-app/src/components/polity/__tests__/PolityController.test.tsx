import React from 'react';
import type { Mock } from 'vitest';
import { act, render, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import { PolityProvider, usePolityCtx, type PolityCtx } from '../PolityController';
import { makeTestQueryClient } from '../../../test/queryWrapper';
import { makeSearchSpy, servePolity } from '../../../test/polityApi';

vi.mock('../../../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), PATCH: vi.fn() },
}));
const { apiClient } = (await import('../../../api/client')) as unknown as {
  apiClient: { GET: Mock };
};

const spy = makeSearchSpy();

function renderController(url: string, responses: Parameters<typeof servePolity>[1] = {}) {
  servePolity(apiClient.GET, responses);
  const seen: { ctx: PolityCtx | null } = { ctx: null };
  const Probe: React.FC = () => {
    seen.ctx = usePolityCtx();
    return null;
  };
  render(
    <QueryClientProvider client={makeTestQueryClient()}>
      <MemoryRouter initialEntries={[url]}>
        <PolityProvider>
          <Probe />
        </PolityProvider>
        <spy.SearchSpy />
      </MemoryRouter>
    </QueryClientProvider>
  );
  return seen;
}

describe('PolityController, before a run has loaded', () => {
  beforeEach(() => {
    apiClient.GET.mockReset();
  });

  it('has no overview, and a requested tick clamps to the start', async () => {
    const seen = renderController('/polity', { failRun: true });
    await waitFor(() => expect(seen.ctx?.runs).toBeDefined());
    await waitFor(() => expect(seen.ctx?.overviewLoading).toBe(false));
    expect(seen.ctx?.overview).toBeUndefined();
    // Nothing to clamp against yet: the last tick is unknown, so any tick lands on 0.
    act(() => seen.ctx?.setTick(7));
    await waitFor(() => expect(new URLSearchParams(spy.search()).get('tick')).toBe('0'));
  });
});
