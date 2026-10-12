/**
 * The engine in the visitor's browser (PLAN_BEYOND_CI W6, option A; EXP-023).
 *
 * The static build (`npm run build:static`, VITE_ENGINE=browser) has no server: every
 * /api/v2 request goes to a Web Worker (workers/engine.worker.ts) that runs the backend's
 * own routers in Pyodide (fast_api_voter/api/browser.py) and answers as the server would.
 */
export const ENGINE_IN_BROWSER = process.env.VITE_ENGINE === 'browser';

/** The server's own worker timeout and 503 (api/core/worker_dispatch.py). */
export const TIMEOUT_MS = 180_000;
const TIMED_OUT = JSON.stringify({ detail: 'Request took too long to process' });

interface Reply {
  id: number;
  status: number;
  body: string;
}

/** A `fetch` for the API client that answers /api/v2 from the worker `makeWorker` starts. */
export function createBrowserFetch(
  makeWorker: () => Worker
): (request: Request) => Promise<Response> {
  let worker: Worker | undefined;
  let seq = 0;
  const pending = new Map<
    number,
    { resolve: (r: Response) => void; timer: ReturnType<typeof setTimeout> }
  >();

  const answer = ({ id, status, body }: Reply) => {
    const waiting = pending.get(id);
    if (!waiting) return;
    clearTimeout(waiting.timer);
    pending.delete(id);
    waiting.resolve(
      new Response(body, { status, headers: { 'Content-Type': 'application/json' } })
    );
  };

  // The worker answers one request at a time. Past the server's timeout, it is stopped,
  // the request and those queued behind it get the server's 503, and the next request
  // starts a fresh one.
  const giveUp = () => {
    worker?.terminate();
    worker = undefined;
    for (const id of [...pending.keys()]) answer({ id, status: 503, body: TIMED_OUT });
  };

  return async (request: Request) => {
    const url = new URL(request.url);
    if (!url.pathname.startsWith('/api/v2/')) return fetch(request);
    if (!worker) {
      worker = makeWorker();
      worker.onmessage = (e: MessageEvent<Reply>) => answer(e.data);
    }
    const message = {
      id: ++seq,
      method: request.method,
      path: url.pathname,
      query: url.search.slice(1),
      body: await request.text(),
    };
    return new Promise<Response>((resolve) => {
      pending.set(message.id, { resolve, timer: setTimeout(giveUp, TIMEOUT_MS) });
      worker!.postMessage(message);
    });
  };
}
