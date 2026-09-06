vi.mock('../../api/client', () => ({ apiPost: vi.fn() }));

import { runIssueVoting, runOstrogorskiDemo } from '../issuesApi';
import { apiPost } from '../../api/client';
import { DEFAULT_CONFIG, DEFAULT_PLAYGROUND } from '../../stores/useElectionStore';

const apiPostMock = apiPost as unknown as ReturnType<typeof vi.fn>;

beforeEach(() => {
  apiPostMock.mockReset();
});

describe('runIssueVoting', () => {
  it('posts a spatial-mode request derived from the shared electorate', async () => {
    const result = { mode: 'spatial', parties: [], issues: [], divergent_count: 0 };
    apiPostMock.mockResolvedValueOnce(result);

    const out = await runIssueVoting(DEFAULT_CONFIG, 3, DEFAULT_PLAYGROUND);

    expect(out).toBe(result);
    expect(apiPostMock).toHaveBeenCalledWith(
      '/api/v2/election/issue-voting',
      expect.objectContaining({
        mode: 'spatial',
        num_issues: 3,
        num_voters: DEFAULT_CONFIG.num_voters,
        electorate: null,
      })
    );
  });

  it('sends a null electorate when no playground state is given', async () => {
    apiPostMock.mockResolvedValueOnce({});
    await runIssueVoting(DEFAULT_CONFIG, 2);
    expect(apiPostMock).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ electorate: null })
    );
  });
});

describe('runOstrogorskiDemo', () => {
  it('posts the fixed handcrafted 2-party, 3-issue paradox profile', async () => {
    const result = { mode: 'handcrafted', ostrogorski_paradox: true };
    apiPostMock.mockResolvedValueOnce(result);

    const out = await runOstrogorskiDemo();

    expect(out).toBe(result);
    expect(apiPostMock).toHaveBeenCalledWith(
      '/api/v2/election/issue-voting',
      expect.objectContaining({
        mode: 'handcrafted',
        party_names: ['A', 'B'],
      })
    );
    const [, body] = apiPostMock.mock.calls[0];
    expect(body.party_platforms).toHaveLength(2);
    expect(body.voter_stances).toHaveLength(5);
  });
});
