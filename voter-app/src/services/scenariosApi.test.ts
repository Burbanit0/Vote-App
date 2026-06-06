import { listScenarios, saveScenario, getScenario, deleteScenario } from './scenariosApi';

vi.mock('../api/client', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiDelete: vi.fn(),
}));
const { apiGet, apiPost, apiDelete } = (await import('../api/client')) as unknown as {
  apiGet: jest.Mock;
  apiPost: jest.Mock;
  apiDelete: jest.Mock;
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe('scenariosApi', () => {
  describe('listScenarios', () => {
    it('returns a list of scenarios', async () => {
      const scenarios = [
        { id: 1, name: 'Test 1', created_at: '2024-01-01T00:00:00Z', config: {} },
        { id: 2, name: 'Test 2', created_at: '2024-01-02T00:00:00Z', config: {} },
      ];
      apiGet.mockResolvedValueOnce(scenarios);
      const result = await listScenarios();
      expect(result).toEqual(scenarios);
      expect(apiGet).toHaveBeenCalledWith('/api/v2/scenarios');
    });
  });

  describe('saveScenario', () => {
    it('creates a scenario with given config', async () => {
      const created = { id: 1, name: 'My Scenario', config: { num_voters: 100 }, results: null };
      apiPost.mockResolvedValueOnce(created);
      const result = await saveScenario('My Scenario', { num_voters: 100 });
      expect(result).toEqual(created);
      expect(apiPost).toHaveBeenCalledWith(
        '/api/v2/scenarios',
        expect.objectContaining({ name: 'My Scenario' })
      );
    });
  });

  describe('getScenario', () => {
    it('returns a scenario by id', async () => {
      const detail = {
        id: 1,
        name: 'Test',
        config: {},
        results: null,
        created_at: '2024-01-01T00:00:00Z',
      };
      apiGet.mockResolvedValueOnce(detail);
      const result = await getScenario(1);
      expect(result).toEqual(detail);
      expect(apiGet).toHaveBeenCalledWith('/api/v2/scenarios/1');
    });
  });

  describe('deleteScenario', () => {
    it('deletes a scenario successfully', async () => {
      apiDelete.mockResolvedValueOnce(undefined);
      await expect(deleteScenario(1)).resolves.toBeUndefined();
      expect(apiDelete).toHaveBeenCalledWith('/api/v2/scenarios/1');
    });
  });
});
