/**
 * voter-app/src/api/ — generated API contract.
 *
 * `types.gen.ts` is produced by `npm run gen:api` from the FastAPI backend's
 * OpenAPI schema (dumped offline by fast_api_voter/scripts/gen_openapi.py from
 * the Pydantic models, then fed to openapi-typescript). DO NOT edit it by hand.
 *
 * Convenience re-exports below give human-friendly aliases so panels
 * don't have to spell out `components['schemas']['SimulateRequest']`
 * every time. (Response aliases exist only for endpoints whose FastAPI route
 * declares a `response_model`; passthrough-Dict routes have no response schema.)
 *
 * Workflow when the backend contract changes:
 *   cd fast_api_voter && python scripts/gen_openapi.py
 *   cd ../voter-app    && npm run gen:api
 *   git diff src/api/types.gen.ts   # review what changed
 *   # TypeScript compiler will surface every mismatch in the rest of the codebase
 */
import type { components, operations } from './types.gen';

// ── Convenience aliases for request/response bodies ────────────────────────

export type SimulateRequest = components['schemas']['SimulateRequest'];
export type SimulateResponse = components['schemas']['SimulateResponse'];

export type CombinedEffectsRequest = components['schemas']['CombinedEffectsRequest'];
export type CombinedEffectsResponse = components['schemas']['CombinedEffectsResponse'];

export type CampaignSensitivityRequest = components['schemas']['CampaignSensitivityRequest'];
export type CampaignSensitivityResponse = components['schemas']['CampaignSensitivityResponse'];

export type AbstentionRequest = components['schemas']['AbstentionRequest'];
export type AbstentionResponse = components['schemas']['AbstentionResponse'];

export type CoalitionRequest = components['schemas']['CoalitionRequest'];
export type CoalitionResponse = components['schemas']['CoalitionResponse'];

export type HotellingResponse = components['schemas']['HotellingResponse'];
export type AdaptiveResponse = components['schemas']['AdaptiveResponse'];
export type DistrictsResponse = components['schemas']['DistrictsResponse'];
export type PartyDynamicsResponse = components['schemas']['PartyDynamicsResponse'];
export type HistoricalReplayResponse = components['schemas']['HistoricalReplayResponse'];
export type CampaignResponse = components['schemas']['CampaignResponse'];
export type SenParadoxResponse = components['schemas']['SenParadoxResponse'];

// ── Shared primitives ──────────────────────────────────────────────────────

export type CandidateSpec = components['schemas']['CandidateSpec'];
export type CandidateSnapshot = components['schemas']['CandidateSnapshot'];
export type VoterSnapshot = components['schemas']['VoterSnapshot'];
export type MethodResult = components['schemas']['MethodResult'];
export type BlankVoteConfig = components['schemas']['BlankVoteConfig'];
export type CampaignConfig = components['schemas']['CampaignConfig'];
export type ContagionConfig = components['schemas']['ContagionConfig'];
export type InformationModelConfig = components['schemas']['InformationModelConfig'];

// ── Re-export the raw shapes too, in case a panel needs paths/operations ──

export type { components, operations };
