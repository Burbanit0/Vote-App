/**
 * The engine in the visitor's browser (PLAN_BEYOND_CI W6, option A; EXP-023).
 *
 * The static build (`npm run build:static`, VITE_ENGINE=browser) has no server: every
 * /api/v2 request goes to a Web Worker (workers/engine.worker.ts) that runs the backend's
 * own routers in Pyodide (fast_api_voter/api/browser.py) and answers as the server would.
 */
export const ENGINE_IN_BROWSER = process.env.VITE_ENGINE === 'browser';

/**
 * How long one request may compute: the server's limit (WORKER_TIMEOUT_SECONDS in
 * api/core/worker_dispatch.py), counted as there only while the request runs, not while
 * it waits behind others or while the engine downloads and starts.
 */
export const TIMEOUT_MS = 180_000;
const TIMED_OUT = JSON.stringify({ detail: 'Request took too long to process' });
/** Routes only a server can answer: Polity's run explorer reads run files from its disk. */
const SERVER_ONLY = ['/api/v2/polity/'];

/**
 * From the worker: `started` when it begins a request, then the answer; `fatal` when the
 * engine could not start, so that worker is dropped and the next request starts a new one.
 */
export interface Reply {
  id: number;
  started?: boolean;
  status?: number;
  body?: string;
  fatal?: boolean;
}

interface Waiting {
  resolve: (response: Response) => void;
  started: boolean;
  timer?: ReturnType<typeof setTimeout>;
}

const json = (status: number, body: string) =>
  new Response(body, { status, headers: { 'Content-Type': 'application/json' } });

/** A `fetch` for the API client that answers /api/v2 from the worker `makeWorker` starts. */
export function createBrowserFetch(
  makeWorker: () => Worker
): (request: Request) => Promise<Response> {
  let worker: Worker | undefined;
  let seq = 0;
  const pending = new Map<number, Waiting>();

  const answer = (id: number, status: number, body: string) => {
    const waiting = pending.get(id);
    if (!waiting) return;
    clearTimeout(waiting.timer);
    pending.delete(id);
    waiting.resolve(json(status, body));
  };

  // Stop the worker and answer everything it still owed: past the timeout, the server's
  // 503; when the engine could not start, the worker's own 503.
  const stop = (status: number, body: string) => {
    worker?.terminate();
    worker = undefined;
    for (const id of [...pending.keys()]) answer(id, status, body);
  };

  const onReply = ({ id, started, status = 500, body = '{}', fatal }: Reply) => {
    if (fatal) return stop(status, body);
    if (!started) return answer(id, status, body);
    // The worker may begin a request just as the page cancels it: nothing waits for it then.
    const waiting = pending.get(id);
    if (!waiting) return;
    waiting.started = true;
    waiting.timer = setTimeout(() => stop(503, TIMED_OUT), TIMEOUT_MS);
  };

  return async (request: Request) => {
    const url = new URL(request.url);
    if (!url.pathname.startsWith('/api/v2/')) return fetch(request);
    if (SERVER_ONLY.some((prefix) => url.pathname.startsWith(prefix))) {
      return json(404, JSON.stringify({ detail: 'Not Found' }));
    }
    request.signal.throwIfAborted();
    const message = {
      id: ++seq,
      method: request.method,
      path: url.pathname,
      query: url.search.slice(1),
      body: await request.text(),
    };
    if (!worker) {
      worker = makeWorker();
      worker.onmessage = (e: MessageEvent<Reply>) => onReply(e.data);
    }
    const target = worker;
    return new Promise<Response>((resolve, reject) => {
      const waiting: Waiting = { resolve, started: false };
      pending.set(message.id, waiting);
      // A cancelled request (react-query aborts on unmount or a new key): still queued,
      // the worker skips it; already running, its answer is dropped, and its timeout
      // still stops a computation that would never end.
      request.signal.addEventListener(
        'abort',
        () => {
          waiting.resolve = () => {};
          if (!waiting.started) {
            pending.delete(message.id);
            target.postMessage({ cancel: message.id });
          }
          reject(request.signal.reason);
        },
        { once: true }
      );
      target.postMessage(message);
    });
  };
}
