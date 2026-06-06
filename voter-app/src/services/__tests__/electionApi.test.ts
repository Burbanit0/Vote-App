import { toSimulatePayload } from '../electionApi';
import type { ElectionConfig } from '../../stores/useElectionStore';

describe('toSimulatePayload', () => {
  const base: ElectionConfig = {
    candidates: [
      { name: 'A', x: -0.5, y: 0 },
      { name: 'B', x: 0.5, y: 0 },
    ],
    num_voters: 300,
    ideology: 'random',
    seed: 42,
    blank_vote: {
      enabled: false,
      rule: 'symbolic',
      contagion: { enabled: false, beta: 0.15, gamma: 0.1, network: 'random' },
    },
    information_model: {
      enabled: false,
      media_bias: {},
      voter_segments: { low_info: 0.3, medium_info: 0.5, high_info: 0.2 },
    },
    campaign: { enabled: false, num_days: 30, polling_effect: 0.3 },
  };

  it('strips UI-only metadata (description / phenomenon) the /simulate schema forbids', () => {
    const withMeta = { ...base, description: 'Le paradoxe…', phenomenon: 'Condorcet' };
    const payload = toSimulatePayload(withMeta);
    expect(payload).not.toHaveProperty('description');
    expect(payload).not.toHaveProperty('phenomenon');
  });

  it('keeps exactly the 7 contract fields', () => {
    expect(Object.keys(toSimulatePayload(base)).sort()).toEqual(
      [
        'blank_vote',
        'campaign',
        'candidates',
        'ideology',
        'information_model',
        'num_voters',
        'seed',
      ].sort()
    );
  });
});
