import { createBrowserFetch, TIMEOUT_MS, type Reply } from './browserEngine';

/** Every FakeWorker started, in order. */
const workers: FakeWorker[] = [];

/** A stand-in for the engine worker: records what it is sent, answers when told. */
class FakeWorker {
  sent: Record<string, unknown>[] = [];
  terminated = false;
  onmessage: ((e: MessageEvent) => void) | null = null;
  constructor() {
    workers.push(this);
  }
  postMessage(message: Record<string, unknown>) {
    this.sent.push(message);
  }
  terminate() {
    this.terminated = true;
  }
  send(reply: Reply) {
    this.onmessage?.({ data: reply } as MessageEvent);
  }
}

const browserFetch = () => createBrowserFetch(() => new FakeWorker() as unknown as Worker);
const post = (path: string, signal?: AbortSignal) =>
  new Request(`http://localhost${path}`, { method: 'POST', body: '{}', signal });
/** Wait until the worker has been sent `n` messages. */
const sent = (n: number) => vi.waitFor(() => expect(workers[0]?.sent).toHaveLength(n));

beforeEach(() => {
  workers.length = 0;
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
    await sent(1);
    expect(workers[0].sent[0]).toEqual({
      id: 1,
      method: 'POST',
      path: '/api/v2/election/stv',
      query: 'x=1',
      body: '{"num_seats":2}',
    });
    workers[0].send({ id: 1, started: true });
    workers[0].send({ id: 1, status: 422, body: '{"detail":"nope"}' });
    const response = await answer;
    expect(response.status).toBe(422);
    expect(await response.json()).toEqual({ detail: 'nope' });
    // A reply for a request already answered changes nothing.
    workers[0].send({ id: 1, status: 200, body: '{}' });
  });

  it('leaves every other request to the network', async () => {
    const network = vi.fn(async () => new Response('ok'));
    vi.stubGlobal('fetch', network);
    const response = await browserFetch()(new Request('http://localhost/engine.zip'));
    expect(await response.text()).toBe('ok');
    expect(network).toHaveBeenCalledOnce();
    expect(workers).toHaveLength(0);
  });

  it("answers Polity's routes from their export, without starting the engine", async () => {
    const polity = vi.fn(async () => ({ status: 200, body: { runs: [] } }));
    const fetchFromBrowser = createBrowserFetch(
      () => new FakeWorker() as unknown as Worker,
      polity
    );
    const response = await fetchFromBrowser(new Request('http://localhost/api/v2/polity/runs'));
    expect(await response.json()).toEqual({ runs: [] });
    expect(polity).toHaveBeenCalledWith(new URL('http://localhost/api/v2/polity/runs'));
    expect(workers).toHaveLength(0);
  });

  it('answers 503 when the Polity export cannot be downloaded, as a server that is down', async () => {
    const fetchFromBrowser = createBrowserFetch(
      () => new FakeWorker() as unknown as Worker,
      () => Promise.reject(new Error('offline'))
    );
    const response = await fetchFromBrowser(new Request('http://localhost/api/v2/polity/runs'));
    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({ detail: 'Run files unavailable: Error: offline' });
  });

  it('counts the timeout only while a request runs, then answers all with the 503', async () => {
    vi.useFakeTimers();
    const fetchFromBrowser = browserFetch();
    const long = fetchFromBrowser(post('/api/v2/simulations/monte-carlo'));
    const queued = fetchFromBrowser(post('/api/v2/election/stv'));
    await sent(2);
    // The engine downloading and starting does not count.
    vi.advanceTimersByTime(TIMEOUT_MS * 2);
    expect(workers[0].terminated).toBe(false);
    workers[0].send({ id: 1, started: true });
    vi.advanceTimersByTime(TIMEOUT_MS);
    for (const response of await Promise.all([long, queued])) {
      expect(response.status).toBe(503);
      expect(await response.json()).toEqual({ detail: 'Request took too long to process' });
    }
    expect(workers[0].terminated).toBe(true);
    void fetchFromBrowser(post('/api/v2/election/stv'));
    await vi.waitFor(() => expect(workers).toHaveLength(2));
  });

  it('when the engine cannot start, answers what waits and replaces the worker', async () => {
    const fetchFromBrowser = browserFetch();
    const first = fetchFromBrowser(post('/api/v2/election/stv'));
    const second = fetchFromBrowser(post('/api/v2/election/stv'));
    await sent(2);
    workers[0].send({ id: 1, fatal: true, status: 503, body: '{"detail":"Engine unavailable"}' });
    expect((await first).status).toBe(503);
    expect(await (await second).json()).toEqual({ detail: 'Engine unavailable' });
    expect(workers[0].terminated).toBe(true);
    void fetchFromBrowser(post('/api/v2/election/stv'));
    await vi.waitFor(() => expect(workers).toHaveLength(2));
  });

  it('a request cancelled while queued is skipped by the worker', async () => {
    const abort = new AbortController();
    const answer = browserFetch()(post('/api/v2/election/stv', abort.signal));
    await sent(1);
    abort.abort();
    await expect(answer).rejects.toThrow();
    expect(workers[0].sent[1]).toEqual({ cancel: 1 });
  });

  it('a request the worker begins just as it is cancelled changes nothing', async () => {
    vi.useFakeTimers();
    const abort = new AbortController();
    const answer = browserFetch()(post('/api/v2/election/stv', abort.signal));
    await sent(1);
    abort.abort();
    await expect(answer).rejects.toThrow();
    // The worker had already taken it before the cancel reached it.
    workers[0].send({ id: 1, started: true });
    workers[0].send({ id: 1, status: 200, body: '{}' });
    vi.advanceTimersByTime(TIMEOUT_MS);
    expect(workers[0].terminated).toBe(false);
  });

  it('a request cancelled while running is dropped, and its timeout still stops the worker', async () => {
    vi.useFakeTimers();
    const fetchFromBrowser = browserFetch();
    const abort = new AbortController();
    const running = fetchFromBrowser(post('/api/v2/election/stv', abort.signal));
    await sent(1);
    workers[0].send({ id: 1, started: true });
    abort.abort();
    await expect(running).rejects.toThrow();
    expect(workers[0].sent).toHaveLength(1);
    vi.advanceTimersByTime(TIMEOUT_MS);
    expect(workers[0].terminated).toBe(true);
  });

  it('refuses a request already cancelled', async () => {
    const abort = new AbortController();
    abort.abort();
    await expect(browserFetch()(post('/api/v2/election/stv', abort.signal))).rejects.toThrow();
    expect(workers).toHaveLength(0);
  });
});
