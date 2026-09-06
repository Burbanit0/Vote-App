import {
  runComparisonSimulation,
  runStrategicImpactAnalysis,
  getCondorcetMatrix,
  getSensitivityAnalysis,
  getBandwagonAnalysis,
  getArrowCriteria,
  getMultiwinner,
  getMonteCarlo,
  getIdeologyMap,
  getVoteSteps,
  getBlankHistory,
  getRealElections,
  analyzeRealElection,
  runConstitutionalScenario,
  runScenario,
} from './simulationCompareApi';

vi.mock('../api/client', () => ({ apiPost: vi.fn(), apiGet: vi.fn() }));
const { apiPost, apiGet } = (await import('../api/client')) as unknown as {
  apiPost: jest.Mock;
  apiGet: jest.Mock;
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe('simulationCompareApi', () => {
  describe('runComparisonSimulation', () => {
    it('returns comparison results with methods keys', async () => {
      const response = {
        condorcet_winner: 'Alice',
        methods: {
          plurality: {
            winner: 'Alice',
            bayesian_regret: 0.1,
            condorcet_consistent: true,
            majority_satisfaction: 0.8,
            strategic_vulnerability: 0.2,
          },
          irv: {
            winner: 'Alice',
            bayesian_regret: 0.05,
            condorcet_consistent: true,
            majority_satisfaction: 0.9,
            strategic_vulnerability: 0.1,
          },
        },
      };
      apiPost.mockResolvedValueOnce(response);
      const result = await runComparisonSimulation({ num_voters: 100 });
      expect(result).toEqual(response);
      expect(result.methods).toHaveProperty('plurality');
      expect(result.methods).toHaveProperty('irv');
      expect(apiPost).toHaveBeenCalledWith('/api/v2/simulations/compare', expect.any(Object));
    });
  });

  describe('runStrategicImpactAnalysis', () => {
    it('returns strategic impact data', async () => {
      const response = {
        results: [
          { strategic_pct: 0, methods: { plurality: 0.1, irv: 0.05 } },
          { strategic_pct: 50, methods: { plurality: 0.3, irv: 0.15 } },
        ],
      };
      apiPost.mockResolvedValueOnce(response);
      const result = await runStrategicImpactAnalysis({ strategic_percentages: [0, 50] });
      expect(result).toHaveLength(2);
      expect(result[0]).toHaveProperty('strategic_pct', 0);
      expect(result[1]).toHaveProperty('strategic_pct', 50);
    });
  });

  describe('getCondorcetMatrix', () => {
    it('returns condorcet matrix', async () => {
      const matrix = {
        candidates: ['Alice', 'Bob'],
        matrix: {
          Alice: { Bob: { pct_a: 60, pct_b: 40, winner: 'Alice' } },
          Bob: { Alice: { pct_a: 40, pct_b: 60, winner: 'Alice' } },
        },
        condorcet_winner: 'Alice',
        condorcet_cycles: [],
      };
      apiPost.mockResolvedValueOnce(matrix);
      const result = await getCondorcetMatrix({ candidates: ['Alice', 'Bob'] });
      expect(result).toEqual(matrix);
      expect(result.condorcet_winner).toBe('Alice');
      expect(result.matrix.Alice.Bob.winner).toBe('Alice');
    });

    it('logs and rethrows on a backend error', async () => {
      const err = new Error('boom');
      apiPost.mockRejectedValueOnce(err);
      const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
      await expect(getCondorcetMatrix({ candidates: ['Alice'] })).rejects.toBe(err);
      expect(spy).toHaveBeenCalledWith('Failed to get Condorcet matrix', err);
      spy.mockRestore();
    });
  });

  describe('getSensitivityAnalysis', () => {
    it('posts to /sensitivity and resolves the result', async () => {
      const response = { variable: 'num_voters', values: [100, 200], results: [] };
      apiPost.mockResolvedValueOnce(response);
      const result = await getSensitivityAnalysis({
        base_config: {},
        variable: 'num_voters',
        values: [100, 200],
      });
      expect(result).toEqual(response);
      expect(apiPost).toHaveBeenCalledWith('/api/v2/simulations/sensitivity', expect.any(Object));
    });
  });

  describe('getBandwagonAnalysis', () => {
    it('posts to /bandwagon and resolves the result', async () => {
      const response = { rounds: [], convergence_round: null };
      apiPost.mockResolvedValueOnce(response);
      const result = await getBandwagonAnalysis({ num_rounds: 5 });
      expect(result).toEqual(response);
      expect(apiPost).toHaveBeenCalledWith('/api/v2/simulations/bandwagon', expect.any(Object));
    });
  });

  describe('getArrowCriteria', () => {
    it('posts to /arrow-criteria and resolves the result', async () => {
      const response = { methods: {}, summary: {} };
      apiPost.mockResolvedValueOnce(response);
      const result = await getArrowCriteria({ num_voters: 100 });
      expect(result).toEqual(response);
      expect(apiPost).toHaveBeenCalledWith(
        '/api/v2/simulations/arrow-criteria',
        expect.any(Object)
      );
    });
  });

  describe('getMultiwinner', () => {
    it('posts to /multiwinner and resolves the result', async () => {
      const response = { comparison: {} };
      apiPost.mockResolvedValueOnce(response);
      const result = await getMultiwinner({ party_votes: { A: 100 }, num_seats: 5 });
      expect(result).toEqual(response);
      expect(apiPost).toHaveBeenCalledWith('/api/v2/simulations/multiwinner', expect.any(Object));
    });
  });

  describe('getMonteCarlo', () => {
    it('posts to /monte-carlo and resolves the result', async () => {
      const response = { num_runs: 100, methods: {} };
      apiPost.mockResolvedValueOnce(response);
      const result = await getMonteCarlo({ num_runs: 100 });
      expect(result).toEqual(response);
      expect(apiPost).toHaveBeenCalledWith('/api/v2/simulations/monte-carlo', expect.any(Object));
    });
  });

  describe('getIdeologyMap', () => {
    it('posts to /ideology-map and resolves the result', async () => {
      const response = { voters: [], candidates: [], method_a: 'plurality', method_b: 'schulze' };
      apiPost.mockResolvedValueOnce(response);
      const result = await getIdeologyMap({
        num_voters: 200,
        candidates: [],
        ideology: 'random',
        seed: 1,
        method_a: 'plurality',
        method_b: 'schulze',
      });
      expect(result).toEqual(response);
      expect(apiPost).toHaveBeenCalledWith('/api/v2/simulations/ideology-map', expect.any(Object));
    });
  });

  describe('getVoteSteps', () => {
    it('posts to /vote-steps and resolves the result (no try/catch wrapper)', async () => {
      const response = { method: 'irv' };
      apiPost.mockResolvedValueOnce(response);
      const result = await getVoteSteps({
        method: 'irv',
        num_voters: 100,
        candidates: ['A', 'B'],
        ideology: 'random',
        seed: 1,
      });
      expect(result).toEqual(response);
      expect(apiPost).toHaveBeenCalledWith('/api/v2/simulations/vote-steps', expect.any(Object));
    });
  });

  describe('getBlankHistory', () => {
    it('gets /blank-history with the country as a query param', async () => {
      const response = { country: 'FR', display_name: 'France', note: '', series: [] };
      apiGet.mockResolvedValueOnce(response);
      const result = await getBlankHistory('FR');
      expect(result).toEqual(response);
      expect(apiGet).toHaveBeenCalledWith('/api/v2/simulations/blank-history', { country: 'FR' });
    });
  });

  describe('getRealElections', () => {
    it('gets the real-elections list', async () => {
      const response = [{ key: 'fr2002', name: 'France 2002', year: 2002, country: 'FR' }];
      apiGet.mockResolvedValueOnce(response);
      const result = await getRealElections();
      expect(result).toEqual(response);
      expect(apiGet).toHaveBeenCalledWith('/api/v2/simulations/real-elections');
    });
  });

  describe('analyzeRealElection', () => {
    it('defaults num_voters/blank_vote and posts the election name', async () => {
      const response = { election: {}, methods: {} };
      apiPost.mockResolvedValueOnce(response);
      const result = await analyzeRealElection('france2002');
      expect(result).toEqual(response);
      expect(apiPost).toHaveBeenCalledWith('/api/v2/simulations/real-election', {
        election_name: 'france2002',
        num_voters: 1000,
        blank_vote: false,
      });
    });
  });

  describe('runConstitutionalScenario', () => {
    it('posts to /constitutional-scenario and resolves the result', async () => {
      const response = { scenario_type: 'new_election', conclusion: 'ok' };
      apiPost.mockResolvedValueOnce(response);
      const result = await runConstitutionalScenario({
        initial_election: {
          candidates: [],
          electorate: { num_voters: 100, ideology_preset: 'random', dissatisfaction_rate: 0 },
          blank_rule: 'symbolic',
        },
        blank_triggered: false,
        scenario_type: 'new_election',
        params: {},
      });
      expect(result).toEqual(response);
      expect(apiPost).toHaveBeenCalledWith(
        '/api/v2/simulations/constitutional-scenario',
        expect.any(Object)
      );
    });
  });

  describe('runScenario', () => {
    it('posts to /scenario and resolves the result', async () => {
      const response = {
        without_blank: { condorcet_winner: null, methods: {} },
        with_blank: { condorcet_winner: null, blank_pct: 0, methods: {} },
      };
      apiPost.mockResolvedValueOnce(response);
      const result = await runScenario({
        candidates: [],
        electorate: { num_voters: 100, ideology_preset: 'random', dissatisfaction_rate: 0 },
        blank_rule: 'symbolic',
        methods: ['plurality'],
      });
      expect(result).toEqual(response);
      expect(apiPost).toHaveBeenCalledWith('/api/v2/simulations/scenario', expect.any(Object));
    });
  });

  // Every function above except getVoteSteps/getBlankHistory wraps apiPost/apiGet
  // in try { … } catch (error) { console.error(…); throw error; } — one table
  // covers that repeated shape for all of them, rather than one near-identical
  // `it()` per function.
  describe('error handling — every try/catch wrapper logs and rethrows', () => {
    const err = new Error('boom');

    const cases: [string, string, () => Promise<unknown>][] = [
      ['Failed to run comparison simulation', 'apiPost', () => runComparisonSimulation({})],
      ['Failed to run strategic impact analysis', 'apiPost', () => runStrategicImpactAnalysis({})],
      [
        'Failed to run sensitivity analysis',
        'apiPost',
        () => getSensitivityAnalysis({ base_config: {}, variable: 'num_voters', values: [1] }),
      ],
      ['Failed to run bandwagon simulation', 'apiPost', () => getBandwagonAnalysis({})],
      ['Failed to run Arrow criteria check', 'apiPost', () => getArrowCriteria({})],
      [
        'Failed to run multi-winner analysis',
        'apiPost',
        () => getMultiwinner({ party_votes: {}, num_seats: 1 }),
      ],
      ['Failed to run Monte Carlo simulation', 'apiPost', () => getMonteCarlo({})],
      [
        'Failed to fetch ideology map',
        'apiPost',
        () =>
          getIdeologyMap({
            num_voters: 100,
            candidates: [],
            ideology: 'random',
            seed: 1,
            method_a: 'plurality',
            method_b: 'schulze',
          }),
      ],
      ['Failed to fetch real elections list', 'apiGet', () => getRealElections()],
      ['Failed to analyse real election', 'apiPost', () => analyzeRealElection('france2002')],
      [
        'Failed to run constitutional scenario',
        'apiPost',
        () =>
          runConstitutionalScenario({
            initial_election: {
              candidates: [],
              electorate: { num_voters: 100, ideology_preset: 'random', dissatisfaction_rate: 0 },
              blank_rule: 'symbolic',
            },
            blank_triggered: false,
            scenario_type: 'new_election',
            params: {},
          }),
      ],
      [
        'Failed to run scenario',
        'apiPost',
        () =>
          runScenario({
            candidates: [],
            electorate: { num_voters: 100, ideology_preset: 'random', dissatisfaction_rate: 0 },
            blank_rule: 'symbolic',
            methods: ['plurality'],
          }),
      ],
    ];

    it.each(cases)('%s', async (message, mockName, call) => {
      const mock = mockName === 'apiGet' ? apiGet : apiPost;
      mock.mockRejectedValueOnce(err);
      const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
      await expect(call()).rejects.toBe(err);
      expect(spy).toHaveBeenCalledWith(message, err);
      spy.mockRestore();
    });
  });
});
