import * as React from 'react';

import { TallySpinner, type TallySpinnerProps } from './tally';

// The small loader, inline in a button or a line of text: one tally gate counted in a
// loop (ui/tally.tsx). It replaced the spinning lucide `Loader2`, keeping its API, so
// the ~55 call sites draw the count unchanged. A block-level wait uses `TallyLoader`.
export type SpinnerProps = TallySpinnerProps;

const Spinner: React.FC<SpinnerProps> = (props) => <TallySpinner {...props} />;

export { Spinner };
