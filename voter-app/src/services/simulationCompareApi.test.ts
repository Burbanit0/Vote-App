import {
  runComparisonSimulation,
  runStrategicImpactAnalysis,
  getCondorcetMatrix,
} from './simulationCompareApi';

jest.mock('../api/client', () => ({ apiPost: jest.fn(), apiGet: jest.fn() }));
const { apiPost } = jest.requireMock('../api/client') as { apiPost: jest.Mock };

beforeEach(() => {
  jest.clearAllMocks();
});

describe('simulationCompareApi', () => {
  describe('runComparisonSimulation', () => {
    it('returns comparison results with methods keys', async () => {
      const response = {
        condorcet_winner: 'Alice',
        methods: {
          plurality: { winner: 'Alice', bayesian_regret: 0.1, condorcet_consistent: true, majority_satisfaction: 0.8, strategic_vulnerability: 0.2 },
          irv: { winner: 'Alice', bayesian_regret: 0.05, condorcet_consistent: true, majority_satisfaction: 0.9, strategic_vulnerability: 0.1 },
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
  });
});
