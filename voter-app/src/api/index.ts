/**
 * voter-app/src/api/ — generated API contract.
 *
 * `types.gen.ts` is produced by `npm run gen:api` from the backend's
 * Pydantic schemas (via flask_voter_app/scripts/gen_openapi.py +
 * openapi-typescript). DO NOT edit it by hand.
 *
 * Convenience re-exports below give human-friendly aliases so panels
 * don't have to spell out `components['schemas']['SimulateRequest']`
 * every time.
 *
 * Workflow when the backend contract changes:
 *   cd flask_voter_app && python scripts/gen_openapi.py
 *   cd ../voter-app    && npm run gen:api
 *   git diff src/api/types.gen.ts   # review what changed
 *   # TypeScript compiler will surface every mismatch in the rest of the codebase
 */
import type { components, operations } from './types.gen';

// ── Convenience aliases for request/response bodies ────────────────────────

export type SimulateRequest             = components['schemas']['SimulateRequest'];
export type SimulateResponse            = components['schemas']['SimulateResponse'];

export type CombinedEffectsRequest      = components['schemas']['CombinedEffectsRequest'];
export type CombinedEffectsResponse     = components['schemas']['CombinedEffectsResponse'];

export type CampaignSensitivityRequest  = components['schemas']['CampaignSensitivityRequest'];
export type CampaignSensitivityResponse = components['schemas']['CampaignSensitivityResponse'];

export type AbstentionRequest           = components['schemas']['AbstentionRequest'];
export type AbstentionResponse          = components['schemas']['AbstentionResponse'];

export type CoalitionRequest            = components['schemas']['CoalitionRequest'];
export type CoalitionResponse           = components['schemas']['CoalitionResponse'];

// ── Shared primitives ──────────────────────────────────────────────────────

export type CandidateSpec               = components['schemas']['CandidateSpec'];
export type CandidateSnapshot           = components['schemas']['CandidateSnapshot'];
export type VoterSnapshot               = components['schemas']['VoterSnapshot'];
export type MethodResult                = components['schemas']['MethodResult'];
export type BlankVoteConfig             = components['schemas']['BlankVoteConfig'];
export type CampaignConfig              = components['schemas']['CampaignConfig'];
export type ContagionConfig             = components['schemas']['ContagionConfig'];
export type InformationModelConfig      = components['schemas']['InformationModelConfig'];

// ── Re-export the raw shapes too, in case a panel needs paths/operations ──

export type { components, operations };
