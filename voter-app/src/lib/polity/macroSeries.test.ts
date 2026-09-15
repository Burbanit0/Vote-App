import {
  PRESSURE_KEYS,
  clickedTick,
  electionRows,
  hasStanding,
  pressureRows,
  standingRows,
} from './macroSeries';

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
    acts: [3, 1, 0, 2, 5],
  },
  { tick: 2, acts: [1] },
];

describe('macro series', () => {
  it('keeps missing readings as gaps', () => {
    expect(standingRows(STANDINGS)).toEqual([
      { tick: 0, legitimacy: null, ecart: null, mandateStrength: null },
      { tick: 1, legitimacy: 0.6, ecart: 0.02, mandateStrength: 0.7 },
      { tick: 2, legitimacy: null, ecart: null, mandateStrength: null },
    ]);
    expect(hasStanding(standingRows(STANDINGS))).toBe(true);
    expect(hasStanding(standingRows([STANDINGS[0]]))).toBe(false);
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

  it('carries each election’s turnout and blank share with its source', () => {
    expect(
      electionRows([
        {
          tick: 0,
          outcome: 'elected',
          winner: 2,
          turnout: 0.8,
          blank_share: 0.1,
          blank_source: 'ballots',
        },
        { tick: 4, outcome: 'invalidated' },
      ])
    ).toEqual([
      {
        tick: 0,
        outcome: 'elected',
        winner: 2,
        turnout: 0.8,
        blankShare: 0.1,
        blankSource: 'ballots',
      },
      {
        tick: 4,
        outcome: 'invalidated',
        winner: null,
        turnout: null,
        blankShare: null,
        blankSource: null,
      },
    ]);
  });

  it('reads a chart click as a tick', () => {
    expect(clickedTick({ activeLabel: 7 })).toBe(7);
    expect(clickedTick({ activeLabel: '3' })).toBe(3);
    expect(clickedTick({ activeLabel: 'x' })).toBeNull();
    expect(clickedTick({})).toBeNull();
    expect(clickedTick(null)).toBeNull();
  });
});
