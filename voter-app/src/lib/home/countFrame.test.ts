import { describe, expect, it } from 'vitest';
import { BALLOTS, captionPose, countFrame, pileSlot, stampPoint } from './countFrame';
import { TALLY, VOTERS } from './scenario';

describe('the scrubbed count', () => {
  it('starts with every ballot still in a voter’s hand', () => {
    const f = countFrame(0);
    expect(f.ballots.every((b) => b.o === 0)).toBe(true);
    expect(f.lit.some(Boolean)).toBe(false);
    expect([f.cast, f.step, f.stamp]).toEqual([0, 0, null]);
  });

  it('has every ballot in the box after the vote', () => {
    const f = countFrame(1.05);
    expect(f.cast).toBe(VOTERS.length);
    expect(f.lit.every(Boolean)).toBe(true);
    expect(f.landed).toEqual([0, 0, 0]);
  });

  it('jolts the box while ballots hit the heap', () => {
    const jolts = [0.5, 0.6, 0.7, 0.8].map((p) => countFrame(p).jolt);
    expect(Math.max(...jolts)).toBeGreaterThan(0);
  });

  it('lands each chapter on that rule’s tally, and stamps its winner', () => {
    expect(countFrame(2.05)).toMatchObject({ landed: TALLY.plurality.counts, stamp: 'plurality' });
    expect(countFrame(3.05)).toMatchObject({ landed: TALLY.runoff.counts, stamp: 'runoff' });
    expect(countFrame(4.05)).toMatchObject({ landed: TALLY.approval.counts, stamp: 'approval' });
    expect(countFrame(5)).toMatchObject({ landed: TALLY.approval.counts, step: 5 });
  });

  it('stamps nothing between chapters', () => {
    expect(countFrame(2.75).stamp).toBeNull();
    expect(countFrame(3.75).stamp).toBeNull();
  });

  it('shows the approval disc only in the approval chapter', () => {
    expect(countFrame(3).disc).toBe(0);
    expect(countFrame(4.5).disc).toBe(1);
  });

  it('is a function of progress alone, so scrolling back retraces it', () => {
    const there = countFrame(3.4);
    countFrame(4.8);
    countFrame(0.2);
    expect(countFrame(3.4)).toEqual(there);
  });

  it('has a ballot for every approval', () => {
    const approvals = TALLY.approval.counts.reduce((a, b) => a + b, 0);
    expect(BALLOTS).toHaveLength(approvals);
  });

  it('sets tally marks in fours with a strike', () => {
    expect(pileSlot(0, 0)).toMatchObject({ r: 0, h: 14 });
    expect(pileSlot(0, 4)).toMatchObject({ r: 62, h: 46 });
    expect(pileSlot(0, 5).y).toBeLessThan(pileSlot(0, 0).y);
  });

  it('stamps just above the winning pile', () => {
    const p = stampPoint('approval');
    expect(p.y).toBeLessThan(pileSlot(TALLY.approval.winner, TALLY.approval.counts[1] - 1).y);
  });

  it('fades the captions in at their chapter', () => {
    expect(captionPose(0, 0).o).toBe(1);
    expect(captionPose(1, 0).o).toBe(0);
    expect(captionPose(1.85, 2).o).toBe(1);
    expect(captionPose(0, 3).o).toBe(0);
  });
});
