import React, { useEffect, useRef, useState } from 'react';
import type { NamedPt, Pt } from '../../lib/playgroundVoting';

// LeaderScene3D — a dependency-free orbital 3-D view of the leader electorate.
// Points live in the domain cube [-1,1]³; a yaw/pitch camera (dragged with the
// mouse/touch) rotates them, an orthographic projection draws them to SVG with
// depth cueing (nearer = larger, more opaque, drawn last). Read-only: editing
// stays on the x–y map + z sliders, because depth can't be dragged unambiguously.

const SVG = 480;
const CX = SVG / 2;
const CY = SVG / 2;
const SCALE = 150;

interface R3 { x: number; y: number; z: number }

function rotate(p: Pt, yaw: number, pitch: number): R3 {
  const cy = Math.cos(yaw);
  const sy = Math.sin(yaw);
  const z0 = p.z ?? 0;
  const x = p.x * cy + z0 * sy;
  const zr = -p.x * sy + z0 * cy;
  const cp = Math.cos(pitch);
  const sp = Math.sin(pitch);
  return { x, y: p.y * cp - zr * sp, z: p.y * sp + zr * cp };
}

const sx = (r: R3): number => CX + r.x * SCALE;
const sy = (r: R3): number => CY - r.y * SCALE;
/** Depth → [0,1], 1 = nearest the viewer. */
const depth01 = (z: number): number => Math.max(0, Math.min(1, (z + 1.8) / 3.6));

function nearestCandidate(v: Pt, cands: NamedPt[]): number {
  let best = 0;
  let bd = Infinity;
  cands.forEach((c, i) => {
    const d = (v.x - c.x) ** 2 + (v.y - c.y) ** 2 + ((v.z ?? 0) - (c.z ?? 0)) ** 2;
    if (d < bd) { bd = d; best = i; }
  });
  return best;
}

const CUBE: [number, number, number][] = [
  [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
  [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1],
];
const CUBE_EDGES: [number, number][] = [
  [0, 1], [1, 2], [2, 3], [3, 0], [4, 5], [5, 6], [6, 7], [7, 4],
  [0, 4], [1, 5], [2, 6], [3, 7],
];

export interface LeaderScene3DProps {
  voters: Pt[];
  candidates: NamedPt[];
  palette: string[];
  axisLabels?: string[];
}

const LeaderScene3D: React.FC<LeaderScene3DProps> = ({
  voters,
  candidates,
  palette,
  axisLabels = ['x', 'y', 'z'],
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [yaw, setYaw] = useState(0.6);
  const [pitch, setPitch] = useState(0.35);
  const [spin, setSpin] = useState(true);
  const drag = useRef<{ x: number; y: number } | null>(null);

  // Auto-rotate until the user grabs it.
  useEffect(() => {
    if (!spin) return;
    let raf = 0;
    let last = performance.now();
    const tick = (t: number) => {
      const dt = (t - last) / 1000;
      last = t;
      setYaw((y) => y + dt * 0.4);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [spin]);

  // Pointer orbit.
  useEffect(() => {
    const move = (cx: number, cy: number) => {
      const d = drag.current;
      if (!d) return;
      // Capture the delta BEFORE updating the ref — the setState updaters run
      // later, so they must not dereference drag.current (it may be reset/null).
      const dx = cx - d.x;
      const dy = cy - d.y;
      drag.current = { x: cx, y: cy };
      setYaw((y) => y + dx * 0.01);
      setPitch((p) => Math.max(-1.4, Math.min(1.4, p + dy * 0.01)));
    };
    const onMM = (e: MouseEvent) => move(e.clientX, e.clientY);
    const onUp = () => { drag.current = null; };
    const onTM = (e: TouchEvent) => {
      if (!drag.current || !e.touches[0]) return;
      e.preventDefault();
      move(e.touches[0].clientX, e.touches[0].clientY);
    };
    const svg = svgRef.current;
    window.addEventListener('mousemove', onMM);
    window.addEventListener('mouseup', onUp);
    svg?.addEventListener('touchmove', onTM, { passive: false });
    svg?.addEventListener('touchend', onUp);
    return () => {
      window.removeEventListener('mousemove', onMM);
      window.removeEventListener('mouseup', onUp);
      svg?.removeEventListener('touchmove', onTM);
      svg?.removeEventListener('touchend', onUp);
    };
  }, []);

  const startDrag = (cx: number, cy: number) => {
    drag.current = { x: cx, y: cy };
    setSpin(false);
  };

  // Project everything, then paint far→near.
  const cubePts = CUBE.map((c) => rotate({ x: c[0], y: c[1], z: c[2] }, yaw, pitch));
  const voterDots = voters
    .map((v) => {
      const r = rotate(v, yaw, pitch);
      return { r, party: nearestCandidate(v, candidates) };
    })
    .sort((a, b) => a.r.z - b.r.z);
  const candDots = candidates
    .map((c, i) => ({ r: rotate(c, yaw, pitch), i, name: c.name }))
    .sort((a, b) => a.r.z - b.r.z);
  const axisEnds = [
    rotate({ x: 1, y: 0, z: 0 }, yaw, pitch),
    rotate({ x: 0, y: 1, z: 0 }, yaw, pitch),
    rotate({ x: 0, y: 0, z: 1 }, yaw, pitch),
  ];
  const origin = rotate({ x: 0, y: 0, z: 0 }, yaw, pitch);

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>Glissez pour pivoter</span>
        <button
          type="button"
          data-testid="scene-spin"
          className="rounded border border-border px-1.5 py-0.5 hover:bg-accent"
          onClick={() => setSpin((s) => !s)}
        >
          {spin ? '⏸ rotation' : '▶ rotation'}
        </button>
      </div>
      <svg
        ref={svgRef}
        data-testid="scene-3d"
        viewBox={`0 0 ${SVG} ${SVG}`}
        width="100%"
        role="img"
        aria-label="Vue 3D de l’électorat"
        className="touch-none select-none rounded-lg bg-card"
        style={{ maxHeight: '70vh', cursor: 'grab' }}
        onMouseDown={(e) => startDrag(e.clientX, e.clientY)}
        onTouchStart={(e) => e.touches[0] && startDrag(e.touches[0].clientX, e.touches[0].clientY)}
      >
        {/* Bounding cube */}
        <g opacity={0.25}>
          {CUBE_EDGES.map(([a, b], k) => (
            <line
              key={k}
              x1={sx(cubePts[a])} y1={sy(cubePts[a])}
              x2={sx(cubePts[b])} y2={sy(cubePts[b])}
              stroke="var(--bs-border-color, #999)" strokeWidth={0.75}
            />
          ))}
        </g>

        {/* Axes */}
        {axisEnds.map((e, k) => (
          <g key={k}>
            <line x1={sx(origin)} y1={sy(origin)} x2={sx(e)} y2={sy(e)} stroke="#94a3b8" strokeWidth={1} />
            <text x={sx(e)} y={sy(e)} fontSize={10} fill="#94a3b8">{axisLabels[k] ?? ['x', 'y', 'z'][k]}</text>
          </g>
        ))}

        {/* Voters (coloured by nearest candidate, depth-cued) */}
        <g>
          {voterDots.map((d, k) => {
            const t = depth01(d.r.z);
            return (
              <circle
                key={k}
                cx={sx(d.r)} cy={sy(d.r)}
                r={1.1 + t * 1.8}
                fill={palette[d.party % palette.length]}
                opacity={0.25 + t * 0.5}
              />
            );
          })}
        </g>

        {/* Candidates */}
        <g>
          {candDots.map((d) => {
            const t = depth01(d.r.z);
            return (
              <g key={d.i} data-testid={`scene-candidate-${d.i}`}>
                <circle cx={sx(d.r)} cy={sy(d.r)} r={6 + t * 5} fill={palette[d.i % palette.length]} stroke="#fff" strokeWidth={1.5} />
                <text x={sx(d.r)} y={sy(d.r) - 10 - t * 4} textAnchor="middle" fontSize={11} fontWeight={600} fill="currentColor">
                  {d.name}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
};

export default LeaderScene3D;
