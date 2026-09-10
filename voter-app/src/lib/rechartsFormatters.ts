import type { ReactNode } from 'react';

/**
 * recharts 3.x types Tooltip's `formatter` value/name as possibly
 * undefined/non-numeric (its `Formatter<TValue, TName>` covers array-valued
 * payloads generically). Every chart in this app only ever formats a
 * definite number (and optionally its series name) — this wrapper does that
 * one coercion in a single place instead of widening ~65 call sites'
 * parameter types individually. Accepting `unknown` here (rather than
 * importing recharts' internal `ValueType`/`NameType`) is what makes the
 * returned function structurally assignable to recharts' `formatter` prop
 * regardless of exactly how that type is shaped in a given version.
 */
export function numericTooltipFormatter<R extends ReactNode | [ReactNode, ReactNode]>(
  fn: (value: number, name: string) => R
): (value: unknown, name: unknown) => R {
  return (value, name) => fn(Number(value), name == null ? '' : String(name));
}
