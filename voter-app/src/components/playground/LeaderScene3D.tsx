import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { NamedPt, Pt } from '../../lib/playgroundVoting';

// LeaderScene3D — a dependency-free orbital 3-D view of the leader electorate.
// Points live in the domain cube [-1,1]³; a yaw/pitch camera (dragged with the
// mouse/touch) rotates them, an orthographic projection draws them to SVG with
// depth cueing (nearer = larger, more opaque, drawn last). The scene is a view:
// candidates are edited on the x–y map + z sliders. The "you" marker is the exception —
// dragging it moves it across the screen plane at its current depth (the one reading of
// a 2-D pointer in 3-D that isn't ambiguous), and the z slider sets the depth.

const SVG = 480;
const CX = SVG / 2;
const CY = SVG / 2;
const SCALE = 150;

interface R3 {
  x: number;
  y: number;
  z: number;
}

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

/** Inverse of `rotate`: the domain point that a camera-space point comes from. */
function unrotate(r: R3, yaw: number, pitch: number): R3 {
  const cp = Math.cos(pitch);
  const sp = Math.sin(pitch);
  const y = r.y * cp + r.z * sp;
  const zr = -r.y * sp + r.z * cp;
  const cy = Math.cos(yaw);
  const sy = Math.sin(yaw);
  return { x: r.x * cy - zr * sy, y, z: r.x * sy + zr * cy };
}

const clamp1 = (v: number): number => Math.max(-1, Math.min(1, v));

/** A client position in the SVG's own units (the square viewBox is centred when letterboxed). */
function svgPoint(svg: SVGSVGElement, clientX: number, clientY: number): { x: number; y: number } {
  const box = svg.getBoundingClientRect();
  // 1 unit per px until the SVG is laid out (it has no size yet), rather than dividing by 0.
  const k = Math.min(box.width, box.height) / SVG || 1;
  return {
    x: (clientX - box.left - (box.width - SVG * k) / 2) / k,
    y: (clientY - box.top - (box.height - SVG * k) / 2) / k,
  };
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
    if (d < bd) {
      bd = d;
      best = i;
    }
  });
  return best;
}

const CUBE: [number, number, number][] = [
  [-1, -1, -1],
  [1, -1, -1],
  [1, 1, -1],
  [-1, 1, -1],
  [-1, -1, 1],
  [1, -1, 1],
  [1, 1, 1],
  [-1, 1, 1],
];
const CUBE_EDGES: [number, number][] = [
  [0, 1],
  [1, 2],
  [2, 3],
  [3, 0],
  [4, 5],
  [5, 6],
  [6, 7],
  [7, 4],
  [0, 4],
  [1, 5],
  [2, 6],
  [3, 7],
];

/** The orbit camera. The host may own it (a ref) so it survives the scene unmounting. */
export interface SceneCamera {
  yaw: number;
  pitch: number;
  spin: boolean;
}

const initialCamera = (): SceneCamera => ({
  yaw: 0.6,
  pitch: 0.35,
  // Don't auto-rotate for users who asked for less motion (the orbit is an
  // infinite animation); they can still start it from the toggle.
  spin: !window.matchMedia?.('(prefers-reduced-motion: reduce)').matches,
});

export interface LeaderScene3DProps {
  voters: Pt[];
  candidates: NamedPt[];
  palette: string[];
  axisLabels?: string[];
  /** Optional "you" marker (the sincere-vote module). */
  you?: Pt | null;
  /** Makes "you" draggable: called with the new position as the marker is dragged across
   *  the screen plane (its depth along the view is kept). Without it, the marker is fixed. */
  onMoveYou?: (x: number, y: number, z: number) => void;
  /** Optional host-owned camera: read on mount, written on every change, so the
   *  viewpoint is kept when the scene is unmounted and mounted again. */
  cameraRef?: React.MutableRefObject<SceneCamera | null>;
  /** Index of the candidate the active rule elects (ringed); null/undefined = none. */
  winner?: number | null;
  /** Index of the Condorcet winner (criteria lens); null/undefined = none. */
  condorcet?: number | null;
  /** Id of a text that describes the scene (the host's hidden summary, which names the winner). */
  describedBy?: string;
}

const LeaderScene3D: React.FC<LeaderScene3DProps> = ({
  voters,
  candidates,
  palette,
  axisLabels = ['x', 'y', 'z'],
  you,
  onMoveYou,
  cameraRef,
  winner,
  condorcet,
  describedBy,
}) => {
  const { t } = useTranslation('playground');
  const svgRef = useRef<SVGSVGElement>(null);
  const ownCamera = useRef<SceneCamera | null>(null);
  const camera = cameraRef ?? ownCamera;
  const saved = (camera.current ??= initialCamera());
  const [yaw, setYaw] = useState(saved.yaw);
  const [pitch, setPitch] = useState(saved.pitch);
  const [spin, setSpin] = useState(saved.spin);
  useEffect(() => {
    // Mutate in place: this runs every spin frame.
    Object.assign(saved, { yaw, pitch, spin });
  }, [saved, yaw, pitch, spin]);
  const drag = useRef<{ x: number; y: number } | null>(null);
  // Dragging "you": where the pointer grabbed the marker (SVG units), the depth it keeps, and the
  // camera it was grabbed under (a spin frame that lands after the press must not shift it).
  const dragYou = useRef<{
    dx: number;
    dy: number;
    z: number;
    yaw: number;
    pitch: number;
    move: (x: number, y: number, z: number) => void;
  } | null>(null);

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
      const grab = dragYou.current;
      if (grab) {
        // The SVG is mounted for as long as a drag that started on it can run.
        const at = svgPoint(svgRef.current as SVGSVGElement, cx, cy);
        // Same view depth, new screen position → back to domain coordinates.
        const p = unrotate(
          { x: (at.x - grab.dx - CX) / SCALE, y: (CY - (at.y - grab.dy)) / SCALE, z: grab.z },
          grab.yaw,
          grab.pitch
        );
        grab.move(clamp1(p.x), clamp1(p.y), clamp1(p.z));
        return;
      }
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
    const onMM = (e: MouseEvent) => {
      // A release outside the window never reaches us: without a button held, the drag is over.
      if (dragYou.current && e.buttons === 0) dragYou.current = null;
      move(e.clientX, e.clientY);
    };
    const onUp = () => {
      drag.current = null;
      dragYou.current = null;
    };
    const onTM = (e: TouchEvent) => {
      if ((!drag.current && !dragYou.current) || !e.touches[0]) return;
      e.preventDefault();
      move(e.touches[0].clientX, e.touches[0].clientY);
    };
    const svg = svgRef.current;
    window.addEventListener('mousemove', onMM);
    window.addEventListener('mouseup', onUp);
    svg?.addEventListener('touchmove', onTM, { passive: false });
    svg?.addEventListener('touchend', onUp);
    svg?.addEventListener('touchcancel', onUp);
    return () => {
      window.removeEventListener('mousemove', onMM);
      window.removeEventListener('mouseup', onUp);
      svg?.removeEventListener('touchmove', onTM);
      svg?.removeEventListener('touchend', onUp);
      svg?.removeEventListener('touchcancel', onUp);
    };
  }, []);

  const startDrag = (cx: number, cy: number) => {
    drag.current = { x: cx, y: cy };
    setSpin(false);
  };

  // Nearest candidate doesn't depend on the camera: compute it when the electorate
  // changes, not on every orbit frame.
  const parties = useMemo(
    () => voters.map((v) => nearestCandidate(v, candidates)),
    [voters, candidates]
  );

  // Project everything, then paint far→near.
  const cubePts = CUBE.map((c) => rotate({ x: c[0], y: c[1], z: c[2] }, yaw, pitch));
  const voterDots = voters
    .map((v, k) => ({ r: rotate(v, yaw, pitch), party: parties[k] }))
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
  const youR = you ? rotate(you, yaw, pitch) : null;

  // Grab "you": remember where on the marker the pointer landed so it doesn't jump. The
  // press also reaches the SVG's own handler, which freezes the camera (so the screen plane
  // stays put) — and `move` serves a "you" drag before it would orbit.
  const startDragYou = (move: NonNullable<typeof onMoveYou>, cx: number, cy: number) => {
    const at = svgPoint(svgRef.current as SVGSVGElement, cx, cy);
    const here = youR as R3; // only called from the marker, which renders when youR is set
    dragYou.current = { dx: at.x - sx(here), dy: at.y - sy(here), z: here.z, yaw, pitch, move };
    setSpin(false);
  };

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>
          {onMoveYou && you ? `${t('scene.drag')} · ${t('scene.dragYou')}` : t('scene.drag')}
        </span>
        <button
          type="button"
          data-testid="scene-spin"
          className="rounded border border-border px-1.5 py-0.5 hover:bg-accent"
          onClick={() => setSpin((s) => !s)}
        >
          {spin ? t('scene.pauseSpin') : t('scene.playSpin')}
        </button>
      </div>
      <svg
        ref={svgRef}
        data-testid="scene-3d"
        viewBox={`0 0 ${SVG} ${SVG}`}
        width="100%"
        role="img"
        aria-label={t('scene.aria')}
        aria-describedby={describedBy}
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
              x1={sx(cubePts[a])}
              y1={sy(cubePts[a])}
              x2={sx(cubePts[b])}
              y2={sy(cubePts[b])}
              stroke="var(--bs-border-color, #999)"
              strokeWidth={0.75}
            />
          ))}
        </g>

        {/* Axes */}
        {axisEnds.map((e, k) => (
          <g key={k}>
            <line
              x1={sx(origin)}
              y1={sy(origin)}
              x2={sx(e)}
              y2={sy(e)}
              stroke="#94a3b8"
              strokeWidth={1}
            />
            <text x={sx(e)} y={sy(e)} fontSize={10} fill="#94a3b8">
              {axisLabels[k] ?? ['x', 'y', 'z'][k]}
            </text>
          </g>
        ))}

        {/* Voters (coloured by nearest candidate, depth-cued) */}
        <g>
          {voterDots.map((d, k) => {
            const t = depth01(d.r.z);
            return (
              <circle
                key={k}
                cx={sx(d.r)}
                cy={sy(d.r)}
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
            const near = depth01(d.r.z);
            const rad = 6 + near * 5;
            const isWinner = d.i === winner;
            const isCondorcet = d.i === condorcet;
            return (
              <g key={d.i} data-testid={`scene-candidate-${d.i}`}>
                {isCondorcet && (
                  <circle
                    data-testid="scene-condorcet"
                    cx={sx(d.r)}
                    cy={sy(d.r)}
                    r={rad + (isWinner ? 9 : 5)}
                    fill="none"
                    stroke="#0f766e"
                    strokeWidth={2}
                    strokeDasharray="3 2"
                  />
                )}
                {isWinner && (
                  <circle
                    data-testid="scene-winner"
                    cx={sx(d.r)}
                    cy={sy(d.r)}
                    r={rad + 4}
                    fill="none"
                    stroke="#d97706"
                    strokeWidth={2.5}
                  />
                )}
                <circle
                  cx={sx(d.r)}
                  cy={sy(d.r)}
                  r={rad}
                  fill={palette[d.i % palette.length]}
                  stroke="#fff"
                  strokeWidth={1.5}
                />
                <text
                  x={sx(d.r)}
                  y={sy(d.r) - 10 - near * 4}
                  textAnchor="middle"
                  fontSize={11}
                  fontWeight={600}
                  fill="currentColor"
                >
                  {d.name}
                </text>
                {(isWinner || isCondorcet) && (
                  <text
                    x={sx(d.r)}
                    y={sy(d.r) + rad + (isWinner && isCondorcet ? 26 : 17)}
                    textAnchor="middle"
                    fontSize={10}
                    fontWeight={700}
                    fill={isWinner ? '#d97706' : '#0f766e'}
                    // A halo in the card colour keeps the tag legible over the voter dots.
                    className="stroke-card"
                    strokeWidth={3}
                    paintOrder="stroke"
                    strokeLinejoin="round"
                  >
                    {[isWinner && t('scene.winner'), isCondorcet && t('canvas.condorcetMarker')]
                      .filter(Boolean)
                      .join(' · ')}
                  </text>
                )}
              </g>
            );
          })}
        </g>

        {/* "You" marker (sincere-vote module) — draggable across the screen plane when the
            host gives onMoveYou; the z slider sets its depth. */}
        {youR && (
          <g
            data-testid="you-marker-3d"
            style={onMoveYou ? { cursor: 'grab' } : undefined}
            onMouseDown={
              onMoveYou
                ? // The primary button only: a right-click opens a menu and never sends a mouseup.
                  (e) => e.button === 0 && startDragYou(onMoveYou, e.clientX, e.clientY)
                : undefined
            }
            onTouchStart={
              onMoveYou
                ? (e) =>
                    e.touches[0] &&
                    startDragYou(onMoveYou, e.touches[0].clientX, e.touches[0].clientY)
                : undefined
            }
          >
            {(() => {
              const cx = sx(youR);
              const cy = sy(youR);
              const tdepth = depth01(youR.z);
              const s = 5 + tdepth * 4;
              return (
                <>
                  {/* A wider invisible target than the diamond, so it is easy to grab. */}
                  {onMoveYou && <circle cx={cx} cy={cy} r={16} fill="transparent" />}
                  <rect
                    x={cx - s}
                    y={cy - s}
                    width={s * 2}
                    height={s * 2}
                    transform={`rotate(45 ${cx} ${cy})`}
                    fill="#0f172a"
                    stroke="#fff"
                    strokeWidth={1.5}
                  />
                  <text
                    x={cx}
                    y={cy - 11 - tdepth * 4}
                    textAnchor="middle"
                    fontSize={11}
                    fontWeight={700}
                    fill="currentColor"
                  >
                    {t('canvas.youMarker')}
                  </text>
                </>
              );
            })()}
          </g>
        )}
      </svg>
    </div>
  );
};

export default LeaderScene3D;
