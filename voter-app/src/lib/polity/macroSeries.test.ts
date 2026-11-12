import { PRESSURE_KEYS, clickedTick, hasStanding, pressureRows } from './macroSeries';

const STANDINGS = [
  {
    tick: 0,
    president: null,
    legitimacy: null,
    ecart: null,
    mandate_strength: null,
    acts: [0, 0, 0, 0, 0],
  },
  {
    tick: 1,
    president: 2,
    legitimacy: 0.6,
    ecart: 0.02,
    mandate_strength: 0.7,
    approval: 0.55,
    acts: [3, 1, 0, 2, 5],
  },
  { tick: 2, acts: [1] },
];

describe('macro series', () => {
  it('tells whether any tick carries a reading, null or missing alike counting as none', () => {
    expect(hasStanding(STANDINGS)).toBe(true);
    expect(hasStanding([STANDINGS[0], STANDINGS[2]])).toBe(false);
  });

  it('spreads each tick’s pressure acts over their five kinds', () => {
    expect(PRESSURE_KEYS).toHaveLength(5);
    expect(pressureRows(STANDINGS)[1]).toEqual({
      tick: 1,
      nothing: 3,
      signPetition: 1,
      launchPetition: 0,
      mobilize: 2,
      waitForElection: 5,
    });
    expect(pressureRows(STANDINGS)[2]).toEqual({
      tick: 2,
      nothing: 1,
      signPetition: 0,
      launchPetition: 0,
      mobilize: 0,
      waitForElection: 0,
    });
  });

  it('reads a chart click as a tick', () => {
    expect(clickedTick({ activeLabel: 7 })).toBe(7);
    expect(clickedTick({ activeLabel: '3' })).toBe(3);
    expect(clickedTick({ activeLabel: 'x' })).toBeNull();
    expect(clickedTick({})).toBeNull();
    expect(clickedTick(null)).toBeNull();
  });
});
