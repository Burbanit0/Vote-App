/// <reference types="vitest/globals" />
// Back-compat shim for the Jest→Vitest migration (Phase 6).
// The reference above makes the Vitest globals (`vi`, `describe`, `it`,
// `expect`, `beforeEach`, …) type-visible without importing them, mirroring
// `test.globals: true` in vitest.config.ts.
//
// Runtime `jest.*` calls in tests were converted to `vi.*` (Vitest exposes
// `vi`/`describe`/`it`/`expect` as globals via `test.globals: true`). A handful
// of tests still use `jest.Mock` / `jest.MockedFunction` as TYPES in casts; this
// declares a global `jest` namespace mapping those to the Vitest equivalents so
// `tsc` stays green without touching every file.
declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace jest {
    // Permissive (like the old `@types/jest` bare `jest.Mock`): a callable with
    // the mock methods AND a loose `.mock` accessor, so existing casts such as
    // `as jest.Mock` and `someMock.mock.calls.find(...)` keep type-checking
    // without the stricter call-args typing Vitest's `Mock<T>` would impose.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    type Mock<_T = any> = import('vitest').Mock<(...args: any[]) => any> & {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      mock: { calls: any[]; results: any[]; instances: any[] };
    };
    type MockedFunction<T extends (...args: any[]) => any> =
      import('vitest').MockedFunction<T>;
  }
}

export {};
