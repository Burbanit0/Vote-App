import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

import LeaderScene3D, { type SceneCamera } from '../LeaderScene3D';
import { sampleVoters, type NamedPt } from '../../../lib/playgroundVoting';

const CANDS: NamedPt[] = [
  { name: 'A', x: -0.5, y: 0, z: -0.4 },
  { name: 'B', x: 0.5, y: 0.2, z: 0.6 },
  { name: 'C', x: 0.0, y: -0.3, z: 0.1 },
];
const PALETTE = ['#2563eb', '#dc2626', '#16a34a'];

function setup() {
  render(
    <LeaderScene3D voters={sampleVoters(60, 7, 'random', 3)} candidates={CANDS} palette={PALETTE} />
  );
}

describe('LeaderScene3D', () => {
  it('renders the scene with every candidate and a voter cloud', () => {
    setup();
    expect(screen.getByTestId('scene-3d')).toBeInTheDocument();
    expect(screen.getByTestId('scene-candidate-0')).toBeInTheDocument();
    expect(screen.getByTestId('scene-candidate-2')).toBeInTheDocument();
    // The voter cloud is drawn (many small circles in the scene).
    expect(screen.getByTestId('scene-3d').querySelectorAll('circle').length).toBeGreaterThan(60);
  });

  it('dragging orbits the camera (projected positions change)', () => {
    setup();
    fireEvent.click(screen.getByTestId('scene-spin')); // pause auto-spin first
    const cx = () =>
      screen.getByTestId('scene-candidate-1').querySelector('circle')!.getAttribute('cx');
    const before = cx();
    fireEvent.mouseDown(screen.getByTestId('scene-3d'), { clientX: 100, clientY: 100 });
    fireEvent.mouseMove(window, { clientX: 300, clientY: 200 });
    expect(cx()).not.toBe(before);
  });

  it('the rotation toggle pauses auto-spin', () => {
    setup();
    // Auto-spin is on by default → the button offers to pause.
    expect(screen.getByTestId('scene-spin')).toHaveTextContent('rotation');
    fireEvent.click(screen.getByTestId('scene-spin'));
    expect(screen.getByTestId('scene-spin')).toHaveTextContent('▶');
  });

  it('rings the elected candidate and moves the ring when the winner changes', () => {
    const voters = sampleVoters(60, 7, 'random', 3);
    const { rerender } = render(
      <LeaderScene3D voters={voters} candidates={CANDS} palette={PALETTE} winner={0} />
    );
    const host = () => screen.getByTestId('scene-winner').parentElement;
    expect(host()).toBe(screen.getByTestId('scene-candidate-0'));
    expect(host()).toHaveTextContent('Winner');
    rerender(<LeaderScene3D voters={voters} candidates={CANDS} palette={PALETTE} winner={2} />);
    expect(host()).toBe(screen.getByTestId('scene-candidate-2'));
    rerender(<LeaderScene3D voters={voters} candidates={CANDS} palette={PALETTE} winner={null} />);
    expect(screen.queryByTestId('scene-winner')).not.toBeInTheDocument();
  });

  it('marks the Condorcet winner, alongside the winner when they coincide', () => {
    const voters = sampleVoters(60, 7, 'random', 3);
    render(
      <LeaderScene3D
        voters={voters}
        candidates={CANDS}
        palette={PALETTE}
        winner={1}
        condorcet={1}
      />
    );
    const group = screen.getByTestId('scene-candidate-1');
    expect(group).toContainElement(screen.getByTestId('scene-condorcet'));
    expect(group).toContainElement(screen.getByTestId('scene-winner'));
    expect(group).toHaveTextContent('Winner · Condorcet');
  });

  it('marks a Condorcet winner the rule did not elect as a ring of its own, without the winner tag', () => {
    render(
      <LeaderScene3D
        voters={sampleVoters(60, 7, 'random', 3)}
        candidates={CANDS}
        palette={PALETTE}
        winner={0}
        condorcet={2}
      />
    );
    const group = screen.getByTestId('scene-candidate-2');
    expect(group).toContainElement(screen.getByTestId('scene-condorcet'));
    expect(group).toHaveTextContent('Condorcet');
    expect(group).not.toHaveTextContent('Winner');
    expect(screen.getByTestId('scene-candidate-0')).toContainElement(
      screen.getByTestId('scene-winner')
    );
  });

  describe('dragging "you"', () => {
    const YOU = { x: 0.2, y: -0.1, z: 0.3 };
    // The SVG's drawn size in jsdom is zero; give it the viewBox's own (480 px, so 1 px = 1 unit).
    const sizeSvg = (width = 480, height = 480) =>
      vi.spyOn(screen.getByTestId('scene-3d'), 'getBoundingClientRect').mockReturnValue({
        left: 0,
        top: 0,
        width,
        height,
        right: width,
        bottom: height,
        x: 0,
        y: 0,
        toJSON: () => ({}),
      });
    const mount = (
      onMoveYou?: (x: number, y: number, z: number) => void,
      sized = true,
      box: [number, number] = [480, 480]
    ) => {
      const cameraRef = { current: null as SceneCamera | null };
      render(
        <LeaderScene3D
          voters={sampleVoters(40, 7, 'random', 3)}
          candidates={CANDS}
          palette={PALETTE}
          you={YOU}
          onMoveYou={onMoveYou}
          cameraRef={cameraRef}
        />
      );
      fireEvent.click(screen.getByTestId('scene-spin')); // a still camera
      if (sized) sizeSvg(...box);
      return cameraRef;
    };
    // Where a domain point lands in camera space (mirrors the scene's own projection).
    const view = (p: { x: number; y: number; z: number }, cam: SceneCamera) => {
      const { yaw, pitch } = cam;
      const x = p.x * Math.cos(yaw) + p.z * Math.sin(yaw);
      const zr = -p.x * Math.sin(yaw) + p.z * Math.cos(yaw);
      return {
        x,
        y: p.y * Math.cos(pitch) - zr * Math.sin(pitch),
        z: p.y * Math.sin(pitch) + zr * Math.cos(pitch),
      };
    };
    const centre = () => {
      const r = screen.getByTestId('you-marker-3d').querySelector('rect')!;
      return { x: Number(r.getAttribute('x')) + 5, y: Number(r.getAttribute('y')) + 5 };
    };

    it('moves across the screen plane and keeps its depth', () => {
      const onMoveYou = vi.fn();
      const cameraRef = mount(onMoveYou);
      const cam = { ...cameraRef.current! };
      const before = view(YOU, cam);
      const at = centre();
      // Grab the diamond, then drag 30 px right and 15 px down.
      fireEvent.mouseDown(screen.getByTestId('you-marker-3d'), { clientX: at.x, clientY: at.y });
      fireEvent.mouseMove(window, { buttons: 1, clientX: at.x + 30, clientY: at.y + 15 });
      fireEvent.mouseUp(window);
      expect(onMoveYou).toHaveBeenCalled();
      const [x, y, z] = onMoveYou.mock.calls.at(-1)!;
      const after = view({ x, y, z }, cam);
      expect(after.x).toBeCloseTo(before.x + 30 / 150, 1);
      expect(after.y).toBeCloseTo(before.y - 15 / 150, 1);
      expect(after.z).toBeCloseTo(before.z, 1);
    });

    it('converts pixels to SVG units when the SVG is drawn larger than its viewBox', () => {
      const onMoveYou = vi.fn();
      // 960 x 600 px: the square viewBox is scaled by min(960, 600) / 480 = 1.25 and centred
      // (180 px of margin each side), as `xMidYMid meet` does with `maxHeight: 70vh`.
      const cameraRef = mount(onMoveYou, true, [960, 600]);
      const cam = { ...cameraRef.current! };
      const before = view(YOU, cam);
      const at = centre();
      const start = { x: 180 + at.x * 1.25, y: at.y * 1.25 };
      fireEvent.mouseDown(screen.getByTestId('you-marker-3d'), {
        clientX: start.x,
        clientY: start.y,
      });
      // 75 px right and 50 px up = 60 and 40 SVG units; unscaled it would read 75 and 50.
      fireEvent.mouseMove(window, { buttons: 1, clientX: start.x + 75, clientY: start.y - 50 });
      const [x, y, z] = onMoveYou.mock.calls.at(-1)!;
      const after = view({ x, y, z }, cam);
      expect(after.x).toBeCloseTo(before.x + 60 / 150, 1);
      expect(after.y).toBeCloseTo(before.y + 40 / 150, 1);
    });

    it('does not orbit the camera while it is dragged', () => {
      const cameraRef = mount(vi.fn());
      const { yaw, pitch } = cameraRef.current!;
      const at = centre();
      fireEvent.mouseDown(screen.getByTestId('you-marker-3d'), { clientX: at.x, clientY: at.y });
      fireEvent.mouseMove(window, { buttons: 1, clientX: at.x + 60, clientY: at.y + 40 });
      fireEvent.mouseUp(window);
      expect(cameraRef.current).toMatchObject({ yaw, pitch });
    });

    it('stays inside the domain cube', () => {
      const onMoveYou = vi.fn();
      mount(onMoveYou);
      const at = centre();
      fireEvent.mouseDown(screen.getByTestId('you-marker-3d'), { clientX: at.x, clientY: at.y });
      fireEvent.mouseMove(window, { buttons: 1, clientX: at.x + 4000, clientY: at.y - 4000 });
      for (const v of onMoveYou.mock.calls.at(-1)!) expect(Math.abs(v)).toBeLessThanOrEqual(1);
    });

    it('still works before the SVG is laid out, at one pixel per unit', () => {
      const onMoveYou = vi.fn();
      mount(onMoveYou, false);
      fireEvent.mouseDown(screen.getByTestId('you-marker-3d'), { clientX: 240, clientY: 240 });
      fireEvent.mouseMove(window, { buttons: 1, clientX: 270, clientY: 240 });
      const [x, y, z] = onMoveYou.mock.calls.at(-1)!;
      expect([x, y, z].every(Number.isFinite)).toBe(true);
    });

    it('stops following the pointer once released', () => {
      const onMoveYou = vi.fn();
      mount(onMoveYou);
      const at = centre();
      fireEvent.mouseDown(screen.getByTestId('you-marker-3d'), { clientX: at.x, clientY: at.y });
      fireEvent.mouseUp(window);
      fireEvent.mouseMove(window, { buttons: 1, clientX: at.x + 50, clientY: at.y });
      expect(onMoveYou).not.toHaveBeenCalled();
    });

    it('follows a finger the same way', () => {
      const onMoveYou = vi.fn();
      mount(onMoveYou);
      const at = centre();
      const marker = screen.getByTestId('you-marker-3d');
      fireEvent.touchStart(marker, { touches: [{ clientX: at.x, clientY: at.y }] });
      fireEvent.touchMove(screen.getByTestId('scene-3d'), {
        touches: [{ clientX: at.x + 30, clientY: at.y }],
      });
      expect(onMoveYou).toHaveBeenCalledTimes(1);
      fireEvent.touchEnd(screen.getByTestId('scene-3d'));
    });

    it('ignores a touch move that is not a drag, or has no finger', () => {
      const onMoveYou = vi.fn();
      mount(onMoveYou);
      const svg = screen.getByTestId('scene-3d');
      fireEvent.touchMove(svg, { touches: [{ clientX: 300, clientY: 240 }] }); // no drag yet
      const at = centre();
      fireEvent.touchStart(screen.getByTestId('you-marker-3d'), {
        touches: [{ clientX: at.x, clientY: at.y }],
      });
      fireEvent.touchMove(svg, { touches: [] }); // a drag, but no finger
      expect(onMoveYou).not.toHaveBeenCalled();
      fireEvent.touchEnd(svg);
    });

    it('ends the drag when the button was released outside the window', () => {
      const onMoveYou = vi.fn();
      mount(onMoveYou);
      const at = centre();
      fireEvent.mouseDown(screen.getByTestId('you-marker-3d'), { clientX: at.x, clientY: at.y });
      fireEvent.mouseMove(window, { buttons: 1, clientX: at.x + 10, clientY: at.y });
      expect(onMoveYou).toHaveBeenCalledTimes(1);
      // The mouseup never arrived; the next move reports no button held.
      fireEvent.mouseMove(window, { buttons: 0, clientX: at.x + 60, clientY: at.y });
      fireEvent.mouseMove(window, { buttons: 1, clientX: at.x + 90, clientY: at.y });
      expect(onMoveYou).toHaveBeenCalledTimes(1);
    });

    it('ends the drag when the touch is cancelled', () => {
      const onMoveYou = vi.fn();
      mount(onMoveYou);
      const at = centre();
      const svg = screen.getByTestId('scene-3d');
      fireEvent.touchStart(screen.getByTestId('you-marker-3d'), {
        touches: [{ clientX: at.x, clientY: at.y }],
      });
      fireEvent.touchCancel(svg);
      fireEvent.touchMove(svg, { touches: [{ clientX: at.x + 40, clientY: at.y }] });
      expect(onMoveYou).not.toHaveBeenCalled();
    });

    it('ignores a right-click: it opens a menu and never sends a mouseup', () => {
      const onMoveYou = vi.fn();
      mount(onMoveYou);
      const at = centre();
      fireEvent.mouseDown(screen.getByTestId('you-marker-3d'), {
        button: 2,
        clientX: at.x,
        clientY: at.y,
      });
      fireEvent.mouseMove(window, { buttons: 2, clientX: at.x + 40, clientY: at.y });
      expect(onMoveYou).not.toHaveBeenCalled();
    });

    it('is not moved by a camera frame that lands after the press', () => {
      const onMoveYou = vi.fn();
      const cameraRef = mount(onMoveYou);
      const at = centre();
      fireEvent.mouseDown(screen.getByTestId('you-marker-3d'), { clientX: at.x, clientY: at.y });
      // A spin frame advancing the camera between the press and the first move (what the
      // asynchronous setSpin(false) leaves possible): the pointer has not moved, so neither has "you".
      cameraRef.current!.yaw += 0.4;
      fireEvent.mouseMove(window, { buttons: 1, clientX: at.x, clientY: at.y });
      const [x, y, z] = onMoveYou.mock.calls.at(-1)!;
      expect(x).toBeCloseTo(YOU.x, 5);
      expect(y).toBeCloseTo(YOU.y, 5);
      expect(z).toBeCloseTo(YOU.z, 5);
    });

    it('is fixed when the host gives no handler: the drag orbits the camera instead', () => {
      const cameraRef = mount();
      const { yaw } = cameraRef.current!;
      const at = centre();
      expect(screen.getByTestId('scene-3d')).not.toHaveTextContent('Drag the diamond');
      fireEvent.mouseDown(screen.getByTestId('you-marker-3d'), { clientX: at.x, clientY: at.y });
      fireEvent.mouseMove(window, { buttons: 1, clientX: at.x + 40, clientY: at.y });
      fireEvent.mouseUp(window);
      expect(cameraRef.current!.yaw).not.toBeCloseTo(yaw, 3);
    });
  });

  it('follows the electorate and the candidates when they change', () => {
    const near = (name: string): NamedPt =>
      name === 'A' ? { name, x: -0.9, y: 0, z: 0 } : { name, x: 0.9, y: 0, z: 0 };
    const voter = [{ x: -0.8, y: 0, z: 0 }];
    const fill = () => screen.getByTestId('scene-3d').querySelector('circle')!.getAttribute('fill');
    const { rerender } = render(
      <LeaderScene3D voters={voter} candidates={[near('A'), near('B')]} palette={PALETTE} />
    );
    expect(fill()).toBe(PALETTE[0]); // nearest to A
    // The candidates swap sides: the same voter is now nearest to the second one.
    rerender(
      <LeaderScene3D voters={voter} candidates={[near('B'), near('A')]} palette={PALETTE} />
    );
    expect(fill()).toBe(PALETTE[1]);
    // More voters → more dots.
    const before = screen.getByTestId('scene-3d').querySelectorAll('circle').length;
    rerender(
      <LeaderScene3D
        voters={[...voter, { x: 0.5, y: 0.5, z: 0.5 }, { x: 0, y: -0.5, z: 0.2 }]}
        candidates={[near('B'), near('A')]}
        palette={PALETTE}
      />
    );
    expect(screen.getByTestId('scene-3d').querySelectorAll('circle')).toHaveLength(before + 2);
  });
});
