import { describe, it, expect } from 'vitest';
import { composeElectorate, type Community } from './playgroundElectorate';

const C = (over: Partial<Community>): Community => ({
  id: over.id ?? 'c',
  label: over.label ?? 'c',
  x: over.x ?? 0,
  y: over.y ?? 0,
  z: over.z ?? 0,
  spread: over.spread ?? 0.15,
  weight: over.weight ?? 1,
  turnout: over.turnout ?? 1,
});

describe('composeElectorate', () => {
  it('is deterministic for a fixed seed', () => {
    const blocs = [C({ id: 'l', x: -0.6 }), C({ id: 'r', x: 0.6 })];
    expect(composeElectorate(blocs, 0, 200, 7)).toEqual(composeElectorate(blocs, 0, 200, 7));
  });

  it('produces a multimodal cloud — voters cluster near each bloc', () => {
    const blocs = [C({ id: 'l', x: -0.7, spread: 0.08 }), C({ id: 'r', x: 0.7, spread: 0.08 })];
    const { voters } = composeElectorate(blocs, 0, 600, 1);
    const left = voters.filter((v) => v.x < 0).length;
    const right = voters.length - left;
    // Roughly balanced two-bloc split, and the mid-band is sparse.
    expect(left).toBeGreaterThan(150);
    expect(right).toBeGreaterThan(150);
    expect(voters.filter((v) => Math.abs(v.x) < 0.2).length).toBeLessThan(voters.length * 0.2);
  });

  it('weight controls relative bloc size', () => {
    const blocs = [C({ id: 'big', x: -0.6, weight: 4 }), C({ id: 'small', x: 0.6, weight: 1 })];
    const { voters, community } = composeElectorate(blocs, 0, 1000, 3);
    const big = community.filter((c) => c === 0).length;
    expect(big).toBeGreaterThan(voters.length * 0.6); // ~80%
  });

  it('per-community turnout thins a bloc', () => {
    const full = composeElectorate([C({ id: 'a', turnout: 1 })], 0, 500, 1);
    const half = composeElectorate([C({ id: 'a', turnout: 0.5 })], 0, 500, 1);
    expect(half.voters.length).toBeLessThan(full.voters.length * 0.7);
  });

  it('correlation couples the x and y deviations', () => {
    const blocs = [C({ id: 'c', x: 0, y: 0, spread: 0.3 })];
    const corr = (rho: number) => {
      const { voters } = composeElectorate(blocs, rho, 800, 5, 2);
      const mx = voters.reduce((s, v) => s + v.x, 0) / voters.length;
      const my = voters.reduce((s, v) => s + v.y, 0) / voters.length;
      let cov = 0;
      let vx = 0;
      let vy = 0;
      for (const v of voters) {
        cov += (v.x - mx) * (v.y - my);
        vx += (v.x - mx) ** 2;
        vy += (v.y - my) ** 2;
      }
      return cov / Math.sqrt(vx * vy);
    };
    expect(corr(0.8)).toBeGreaterThan(0.5);
    expect(Math.abs(corr(0))).toBeLessThan(0.2);
  });

  it('1-D collapses y and z to 0', () => {
    const { voters } = composeElectorate([C({ id: 'a', y: 0.5 })], 0, 100, 1, 1);
    expect(voters.every((v) => v.y === 0 && (v.z ?? 0) === 0)).toBe(true);
  });

  it('never returns an empty electorate (falls back to centres)', () => {
    const { voters } = composeElectorate(
      [C({ id: 'a', turnout: 0 }), C({ id: 'b', turnout: 0 })],
      0,
      200,
      1
    );
    expect(voters.length).toBeGreaterThanOrEqual(2);
  });

  it('per-community z centres the bloc on the 3rd axis (3-D only)', () => {
    const blocs = [C({ id: 'up', z: 0.7, spread: 0.08 })];
    // In 3-D the cloud sits near z≈0.7; in 2-D z collapses to 0.
    const m3 = composeElectorate(blocs, 0, 600, 9, 3);
    const meanZ = m3.voters.reduce((s, v) => s + (v.z ?? 0), 0) / m3.voters.length;
    expect(meanZ).toBeGreaterThan(0.4);
    const m2 = composeElectorate(blocs, 0, 600, 9, 2);
    expect(m2.voters.every((v) => (v.z ?? 0) === 0)).toBe(true);
  });

  it('measurement noise widens the cloud without moving its centre', () => {
    const blocs = [C({ id: 'c', x: 0.2, spread: 0.05 })];
    const sd = (noise: number) => {
      const { voters } = composeElectorate(blocs, 0, 600, 11, 2, noise);
      const mx = voters.reduce((s, v) => s + v.x, 0) / voters.length;
      const variance = voters.reduce((s, v) => s + (v.x - mx) ** 2, 0) / voters.length;
      return { mx, sd: Math.sqrt(variance) };
    };
    const clean = sd(0);
    const noisy = sd(1);
    expect(noisy.sd).toBeGreaterThan(clean.sd * 1.5); // visibly blurred
    expect(Math.abs(noisy.mx - clean.mx)).toBeLessThan(0.1); // centre held
  });

  it('noise=0 is identical to omitting the noise argument', () => {
    const blocs = [C({ id: 'a', x: -0.3 }), C({ id: 'b', x: 0.4 })];
    expect(composeElectorate(blocs, 0.2, 300, 4, 2, 0)).toEqual(
      composeElectorate(blocs, 0.2, 300, 4, 2)
    );
  });
});
