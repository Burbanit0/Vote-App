import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';
import { listScenarios, saveScenario, getScenario, deleteScenario } from './scenariosApi';

const mockAxios = new MockAdapter(axios);
const BASE = 'http://localhost:4433';
const mockToken = 'test-jwt-token';

beforeEach(() => {
  mockAxios.reset();
  localStorage.clear();
  localStorage.setItem('user', JSON.stringify({ access_token: mockToken }));
});

describe('scenariosApi', () => {
  describe('listScenarios', () => {
    it('returns a list of scenarios', async () => {
      const scenarios = [
        { id: 1, name: 'Test 1', created_at: '2024-01-01T00:00:00Z', config: {} },
        { id: 2, name: 'Test 2', created_at: '2024-01-02T00:00:00Z', config: {} },
      ];
      mockAxios.onGet(`${BASE}/api/v2/scenarios`).reply(200, scenarios);
      const result = await listScenarios();
      expect(result).toEqual(scenarios);
    });
  });

  describe('saveScenario', () => {
    it('creates a scenario with given config', async () => {
      const created = { id: 1, name: 'My Scenario', config: { num_voters: 100 }, results: null };
      mockAxios.onPost(`${BASE}/api/v2/scenarios`).reply(200, created);
      const result = await saveScenario('My Scenario', { num_voters: 100 });
      expect(result).toEqual(created);
    });
  });

  describe('getScenario', () => {
    it('returns a scenario by id', async () => {
      const detail = { id: 1, name: 'Test', config: {}, results: null, created_at: '2024-01-01T00:00:00Z' };
      mockAxios.onGet(`${BASE}/api/v2/scenarios/1`).reply(200, detail);
      const result = await getScenario(1);
      expect(result).toEqual(detail);
    });
  });

  describe('deleteScenario', () => {
    it('deletes a scenario successfully', async () => {
      mockAxios.onDelete(`${BASE}/api/v2/scenarios/1`).reply(204);
      await expect(deleteScenario(1)).resolves.toBeUndefined();
    });
  });
});
