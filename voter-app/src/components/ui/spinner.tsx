// The small loader, inline in a button or a line of text: one tally gate counted in a
// loop (ui/tally.tsx). It replaced the spinning lucide `Loader2`, keeping its API, so
// the ~55 call sites draw the count unchanged. A block-level wait uses `TallyLoader`.
export { TallySpinner as Spinner, type TallySpinnerProps as SpinnerProps } from './tally';
