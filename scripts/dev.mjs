#!/usr/bin/env node
// dev.mjs — launch the backend (FastAPI/uvicorn) AND the frontend (Vite) with a
// single command. Zero dependencies (Node built-ins only), so `npm run dev`
// works without any extra install. Output from both is line-prefixed and
// colour-coded; Ctrl+C (or either process exiting) shuts both down cleanly,
// killing the whole process tree on Windows so no uvicorn reloader / Vite child
// is left orphaned.
//
// Backend → uvicorn api.main:app on :4434 (the socket.io ASGI wrapper), with
//           --reload, run from fast_api_voter/.
// Frontend → vite (npm start) from voter-app/, which defaults its API to :4434.

import { spawn } from 'node:child_process';
import process from 'node:process';

const RESET = '\x1b[0m';
const isWin = process.platform === 'win32';

// Each command is a single static string run through the shell (no args array,
// so Node doesn't warn about unescaped shell args — there is no user input here).
const procs = [
  {
    name: 'backend',
    color: '\x1b[36m', // cyan
    command: 'python -m uvicorn api.main:app --port 4434 --reload',
    cwd: 'fast_api_voter',
  },
  {
    name: 'frontend',
    color: '\x1b[32m', // green
    command: 'npm start',
    cwd: 'voter-app',
  },
];

const children = [];
let shuttingDown = false;

function killChild(child) {
  if (child.exitCode !== null || child.signalCode !== null) return;
  if (isWin) {
    // /T kills the whole tree (uvicorn's reloader, Vite's esbuild, …); /F forces.
    spawn('taskkill', ['/pid', String(child.pid), '/T', '/F'], { stdio: 'ignore' });
  } else {
    try {
      child.kill('SIGTERM');
    } catch {
      /* already gone */
    }
  }
}

function shutdown(code = 0) {
  if (shuttingDown) return;
  shuttingDown = true;
  for (const c of children) killChild(c);
  setTimeout(() => process.exit(code), 400);
}

for (const p of procs) {
  const prefix = `${p.color}[${p.name}]${RESET} `;
  const child = spawn(p.command, { cwd: p.cwd, shell: true, env: process.env });
  children.push(child);

  const pipe = (stream, out) => {
    let buf = '';
    stream.setEncoding('utf8');
    stream.on('data', (chunk) => {
      buf += chunk;
      const lines = buf.split('\n');
      buf = lines.pop() ?? '';
      for (const line of lines) out.write(prefix + line + '\n');
    });
    stream.on('end', () => {
      if (buf) out.write(prefix + buf + '\n');
    });
  };
  pipe(child.stdout, process.stdout);
  pipe(child.stderr, process.stderr);

  child.on('error', (err) => {
    process.stdout.write(`${prefix}failed to start (${p.command}): ${err.message}\n`);
    shutdown(1);
  });
  child.on('exit', (code, signal) => {
    if (!shuttingDown) {
      process.stdout.write(`${prefix}exited (${signal ?? code}); stopping the other process…\n`);
    }
    shutdown(code ?? 0);
  });
}

process.on('SIGINT', () => shutdown(0));
process.on('SIGTERM', () => shutdown(0));

process.stdout.write(
  `\x1b[1mVote-App dev\x1b[0m — backend :4434 + frontend (Vite). Press Ctrl+C to stop both.\n`
);
