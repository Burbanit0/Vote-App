/**
 * api/hooks.ts — the typed data-fetching surface for the whole app (Phase 5).
 *
 * `$api` is the openapi-react-query wrapper over the typed openapi-fetch client.
 * It exposes fully-typed TanStack Query hooks keyed by (method, path):
 *
 *   // GET (auto-fetch, cached, deduped):
 *   const { data, isLoading, error } = $api.useQuery('get', '/api/v1/methods');
 *
 *   // POST (imperative "run on click" — the dominant panel pattern):
 *   const sim = $api.useMutation('post', '/api/v2/election/abstention');
 *   sim.mutate({ body: { num_voters, candidates, ... } });
 *   // sim.data / sim.isPending / sim.error
 *
 * Bodies + params are type-checked against the generated schema. Responses are
 * typed for endpoints that declare a response_model; passthrough-Dict routes
 * return `Record<string, never>`/unknown — cast to the panel's hand-written
 * interface at the call site until response_models are added backend-side.
 */
import createQueryHooks from 'openapi-react-query';
import { apiClient } from './client';

export const $api = createQueryHooks(apiClient);
