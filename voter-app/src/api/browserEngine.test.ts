import { createBrowserFetch, TIMEOUT_MS } from './browserEngine';

/** A stand-in for the engine worker: records what it is sent, answers when told. */
class FakeWorker {
  static started: FakeWorker[] = [];
  sent: { id: number; method: string; path: string; query: string; body: string }[] = [];
  terminated = false;
  onmessage: ((e: MessageEvent) => void) | null = null;
  constructor() {
    FakeWorker.started.push(this);
  }
  postMessage(message: FakeWorker['sent'][number]) {
    this.sent.push(message);
  }
  terminate() {
    this.terminated = true;
  }
  reply(id: number, status: number, body: unknown) {
    this.onmessage?.({ data: { id, status, body: JSON.stringify(body) } } as MessageEvent);
  }
}

const browserFetch = () => createBrowserFetch(() => new FakeWorker() as unknown as Worker);

beforeEach(() => {
  FakeWorker.started = [];
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('createBrowserFetch', () => {
  it('answers /api/v2 from the worker, as the server would', async () => {
    const answer = browserFetch()(
      new Request('http://localhost/api/v2/election/stv?x=1', {
        method: 'POST',
        body: '{"num_seats":2}',
      })
    );
    await vi.waitFor(() => expect(FakeWorker.started[0]?.sent).toHaveLength(1));
    const [worker] = FakeWorker.started;
    expect(worker.sent[0]).toEqual({
      id: 1,
      method: 'POST',
      path: '/api/v2/election/stv',
      query: 'x=1',
      body: '{"num_seats":2}',
    });
    worker.reply(1, 422, { detail: 'nope' });
    const response = await answer;
    expect(response.status).toBe(422);
    expect(await response.json()).toEqual({ detail: 'nope' });
  });

  it('leaves every other request to the network', async () => {
    const network = vi.fn(async () => new Response('ok'));
    vi.stubGlobal('fetch', network);
    const response = await browserFetch()(new Request('http://localhost/engine.zip'));
    expect(await response.text()).toBe('ok');
    expect(network).toHaveBeenCalledOnce();
    expect(FakeWorker.started).toHaveLength(0);
  });

  it("past the server's timeout, gives every waiting request its 503 and starts afresh", async () => {
    vi.useFakeTimers();
    const fetchFromBrowser = browserFetch();
    const long = fetchFromBrowser(
      new Request('http://localhost/api/v2/simulations/monte-carlo', { method: 'POST', body: '{}' })
    );
    const queued = fetchFromBrowser(
      new Request('http://localhost/api/v2/election/stv', { method: 'POST', body: '{}' })
    );
    await vi.waitFor(() => expect(FakeWorker.started[0]?.sent).toHaveLength(2));
    vi.advanceTimersByTime(TIMEOUT_MS);
    for (const response of await Promise.all([long, queued])) {
      expect(response.status).toBe(503);
      expect(await response.json()).toEqual({ detail: 'Request took too long to process' });
    }
    expect(FakeWorker.started[0].terminated).toBe(true);
    // A late reply from the stopped worker changes nothing; the next request gets a new one.
    FakeWorker.started[0].reply(1, 200, {});
    void fetchFromBrowser(
      new Request('http://localhost/api/v2/election/stv', { method: 'POST', body: '{}' })
    );
    await vi.waitFor(() => expect(FakeWorker.started).toHaveLength(2));
  });
});
