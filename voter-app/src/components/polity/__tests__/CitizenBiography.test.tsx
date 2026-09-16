import React from 'react';
import type { Mock } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import PolityPage from '../../../pages/PolityPage';
import { makeTestQueryClient } from '../../../test/queryWrapper';
import { makeSearchSpy, servePolity, type PolityResponses } from '../../../test/polityApi';

vi.mock('../../../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), PATCH: vi.fn() },
}));
const { apiClient } = (await import('../../../api/client')) as unknown as {
  apiClient: { GET: Mock };
};

const spy = makeSearchSpy();
const param = (name: string) => new URLSearchParams(spy.search()).get(name);

const entry = (tick: number, event_type: string, extra: Record<string, unknown> = {}) => ({
  tick,
  event_type,
  role: 'actor',
  motif: null,
  motif_label: null,
  rationale: null,
  details: {},
  ...extra,
});

const biography = (id: number) => ({
  key: 'aaaa',
  citizen_id: id,
  sections: {
    roles: [entry(0, 'elected'), entry(9, 'recalled')],
    candidacies: [
      entry(0, 'candidacy_considered', {
        motif: 203,
        motif_label: 'AMBITION_THRESHOLD_MET',
        rationale: 'I can win.',
      }),
    ],
    votes: [
      entry(0, 'vote_cast', { motif: 999, motif_label: 'SOMETHING_NEW' }),
      entry(4, 'vote_cast', { motif: 998, motif_label: null }),
    ],
    pressure_acts: [],
    petitions: [entry(4, 'petition_signed', { role: 'listed' })],
    other: [
      entry(6, 'brand_new_event', {
        role: 'target',
        motif: 402,
        motif_label: 'ECONOMIC_SHOCK_REACTION',
      }),
    ],
  },
  received: [
    { tick: 0, event_type: 'vote_cast', code: 0, count: 31 },
    { tick: 3, event_type: 'pressure_action', code: 3, count: 5 },
    { tick: 3, event_type: 'pressure_action', code: 9, count: 1 },
    { tick: 5, event_type: 'petition_signed', code: null, count: 2 },
  ],
  census: [
    { year: 0, role: 'electeur', office: 'aucun', party: 1 },
    { year: 1, role: 'elu', office: 'president', party: null },
    { year: 2, role: 'mystere', office: 'autre', party: 1 },
  ],
});

function renderAt(url: string, responses: PolityResponses = { citizen: biography }) {
  servePolity(apiClient.GET, responses);
  render(
    <QueryClientProvider client={makeTestQueryClient()}>
      <MemoryRouter initialEntries={[url]}>
        <PolityPage />
        <spy.SearchSpy />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('CitizenBiography', () => {
  beforeEach(() => {
    apiClient.GET.mockReset();
  });

  it('fetches nothing while nobody is selected', async () => {
    renderAt('/polity');
    await screen.findByTestId('polity-run-facts');
    expect(screen.queryByTestId('polity-biography')).not.toBeInTheDocument();
    expect(apiClient.GET.mock.calls.map(([path]) => path)).not.toContain(
      '/api/v2/polity/runs/{run_key}/citizens/{citizen_id}'
    );
  });

  it('tells a selected citizen’s story with translated motives and a census', async () => {
    renderAt('/polity?citizen=2');
    const panel = await screen.findByTestId('polity-biography');
    expect(within(panel).getByRole('heading', { name: 'Citizen 2' })).toBeInTheDocument();
    await screen.findByTestId('biography-census');

    const census = screen.getByTestId('biography-census');
    expect(census).toHaveTextContent('0electornone1');
    expect(census).toHaveTextContent('1electedpresident—');
    expect(census).toHaveTextContent('2mystereautre1');

    expect(screen.getByTestId('biography-section-roles')).toHaveTextContent('Roles and office 2');
    expect(screen.getByTestId('biography-section-roles')).toHaveTextContent('president recalled');
    const candidacy = within(screen.getByTestId('biography-section-candidacies')).getByTestId(
      'biography-entry'
    );
    expect(candidacy).toHaveTextContent('candidacy considered');
    expect(candidacy).toHaveTextContent('motive: ambition high enough');
    expect(candidacy).toHaveTextContent('I can win.');
    expect(screen.getByTestId('biography-section-votes')).toHaveTextContent(
      'motive: SOMETHING_NEW'
    );
    expect(screen.getByTestId('biography-section-votes')).toHaveTextContent('motive: 998');
    expect(screen.getByTestId('biography-section-pressure_acts')).toHaveTextContent(
      'Nothing in this run.'
    );
    expect(screen.getByTestId('biography-section-petitions')).toHaveTextContent(
      'petition signed(named)'
    );
    expect(screen.getByTestId('biography-section-other')).toHaveTextContent(
      'brand_new_event(targeted)motive: reacting to the economic shock'
    );

    const received = screen.getByTestId('biography-received');
    expect(received).toHaveTextContent('31 × ballot (ranked no. 1)');
    expect(received).toHaveTextContent('5 × mobilizes');
    expect(received).toHaveTextContent('1 × pressure act');
    expect(received).toHaveTextContent('2 × petition signed');
  });

  it('moves the player from a tick chip and closes back to nobody selected', async () => {
    renderAt('/polity?citizen=2');
    await screen.findByTestId('biography-census');
    fireEvent.click(screen.getAllByRole('button', { name: 'Go to tick 9' })[0]);
    await waitFor(() => expect(param('tick')).toBe('9'));
    fireEvent.click(screen.getByTestId('polity-biography-close'));
    await waitFor(() => expect(param('citizen')).toBeNull());
    expect(screen.queryByTestId('polity-biography')).not.toBeInTheDocument();
  });

  it('says when nobody acted about the citizen', async () => {
    renderAt('/polity?citizen=1', { citizen: (id) => ({ ...biography(id), received: [] }) });
    expect(await screen.findByTestId('biography-received')).toHaveTextContent(
      'Nobody acted about them.'
    );
  });

  it('reports a biography that cannot be loaded', async () => {
    renderAt('/polity?citizen=3', { failCitizen: true });
    expect(await screen.findByTestId('polity-biography-error')).toHaveTextContent(
      'citizen not found'
    );
  });
});
