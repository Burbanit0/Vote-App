// openapi-fetch's createClient() captures `globalThis.fetch` as a default
// parameter at call time (see node_modules/openapi-fetch/dist/index.mjs),
// and client.ts creates its `apiClient` singleton at module-eval time — a
// plain `global.fetch = mockFetch` after a static `import './client'` is
// already too late, since the import's module graph evaluates first and
// binds the real fetch. Stub the global, then re-import fresh per test via
// vi.resetModules() so the client is (re)created against the current stub.
const mockFetch = vi.fn();
global.fetch = mockFetch;

async function freshClient() {
  vi.resetModules();
  return import('./client');
}

function jsonResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('apiPost/apiGet/apiDelete', () => {
  it('resolves with the parsed body on a 2xx response', async () => {
    const { apiPost } = await freshClient();
    mockFetch.mockResolvedValueOnce(jsonResponse(200, { winner: 'Alice' }));
    const result = await apiPost<{ winner: string }>('/api/v2/simulations/compare', {});
    expect(result).toEqual({ winner: 'Alice' });
  });

  it('throws an ApiError carrying the status and detail message on a 4xx response', async () => {
    const { apiPost } = await freshClient();
    mockFetch.mockResolvedValueOnce(
      jsonResponse(422, { detail: 'num_voters must be between 10 and 1000' })
    );
    await expect(apiPost('/api/v2/simulations/bandwagon', {})).rejects.toMatchObject({
      name: 'ApiError',
      status: 422,
      message: 'num_voters must be between 10 and 1000',
    });
  });

  it('falls back to a generic message when the error body has no detail string', async () => {
    const { apiGet, ApiError } = await freshClient();
    mockFetch.mockResolvedValueOnce(jsonResponse(500, { error: 'boom' }));
    const err: unknown = await apiGet('/api/v2/simulations/real-elections').catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    const apiErr = err as InstanceType<typeof ApiError>;
    expect(apiErr.status).toBe(500);
    expect(apiErr.message).toBe('Request failed with status 500');
    expect(apiErr.body).toEqual({ error: 'boom' });
  });

  it('apiDelete throws ApiError on a non-2xx response too', async () => {
    const { apiDelete } = await freshClient();
    mockFetch.mockResolvedValueOnce(jsonResponse(404, { detail: 'not found' }));
    await expect(apiDelete('/api/v2/some-resource/1')).rejects.toMatchObject({
      status: 404,
      message: 'not found',
    });
  });
});
