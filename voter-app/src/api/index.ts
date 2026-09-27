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
import type { components } from './types.gen';

// ── Convenience aliases for request/response bodies ────────────────────────

export type AbstentionRequest = components['schemas']['AbstentionRequest'];
export type CoalitionResponse = components['schemas']['CoalitionResponse'];
export type HotellingResponse = components['schemas']['HotellingResponse'];
export type AdaptiveResponse = components['schemas']['AdaptiveResponse'];
export type DistrictsResponse = components['schemas']['DistrictsResponse'];
export type PartyDynamicsResponse = components['schemas']['PartyDynamicsResponse'];
export type HistoricalReplayResponse = components['schemas']['HistoricalReplayResponse'];
export type SenParadoxResponse = components['schemas']['SenParadoxResponse'];

/** Method names straight from each backend request schema's Literal. */
export type IIAMethod = NonNullable<components['schemas']['IIARateRequest']['method']>;
export type ManipulationMethod = NonNullable<
  components['schemas']['ManipulationAnalysisRequest']['method']
>;
export type HotellingMethod = NonNullable<components['schemas']['HotellingRequest']['method']>;
export type PartyDynamicsMethod = NonNullable<
  components['schemas']['PartyDynamicsRequest']['method']
>;
export type PrimaryMethod = NonNullable<components['schemas']['PrimaryRequest']['primary_method']>;

/** /adaptive's method names, straight from the backend's request schema. */
export type AdaptiveMethod = NonNullable<components['schemas']['AdaptiveRequest']['method']>;
