import * as React from 'react';
import { cn } from '@/lib/utils';

/**
 * Bootstrap-compatible grid primitives (Container / Row / Col) reimplemented on
 * Tailwind, so migrated pages keep `<Row><Col md={6}>…` markup unchanged.
 *
 * Faithful to Bootstrap's 12-column flex grid:
 *  - Row = `display:flex; flex-wrap:wrap` with negative horizontal gutters.
 *  - Col = `flex:0 0 auto; width: n/12` (responsive via xs/sm/md/lg/xl), or
 *    `flex:1` when unsized, or `width:auto` for the "auto" value.
 *  - Gutters come from a context (Row sets it from its `g-{n}` className, default
 *    1.5rem) and are applied as half-padding on each Col + negative Row margin.
 *
 * box-sizing:border-box is supplied globally by the still-imported Bootstrap
 * reboot (and by Tailwind preflight once Bootstrap is removed), so the width +
 * padding math stays exact.
 */

// ── Gutter context (rem per side) ───────────────────────────────────────────
const GutterContext = React.createContext<number>(0.75);

// Bootstrap spacer scale (total gutter) → per-side rem
const GUTTER_TOTAL: Record<string, number> = {
  '0': 0,
  '1': 0.25,
  '2': 0.5,
  '3': 1,
  '4': 1.5,
  '5': 3,
};

const GUTTER_RE = /\bg[xy]?-([0-5])\b/g;

// ── Container ───────────────────────────────────────────────────────────────
export interface ContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  fluid?: boolean;
}

export const Container = React.forwardRef<HTMLDivElement, ContainerProps>(
  ({ className, fluid, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('w-full px-3', fluid ? '' : 'mx-auto max-w-screen-xl', className)}
      {...props}
    />
  )
);
Container.displayName = 'Container';

// ── Row ─────────────────────────────────────────────────────────────────────
export type RowProps = React.HTMLAttributes<HTMLDivElement>;

export const Row = React.forwardRef<HTMLDivElement, RowProps>(
  ({ className, style, ...props }, ref) => {
    // Derive per-side gutter from the first g-{n} class (default 1.5rem total).
    let total = 1.5;
    if (className) {
      const m = [...className.matchAll(GUTTER_RE)];
      if (m.length) total = GUTTER_TOTAL[m[m.length - 1][1]] ?? 1.5;
    }
    const half = total / 2;
    return (
      <GutterContext.Provider value={half}>
        <div
          ref={ref}
          className={cn('flex flex-wrap', className)}
          style={{ marginLeft: `-${half}rem`, marginRight: `-${half}rem`, ...style }}
          {...props}
        />
      </GutterContext.Provider>
    );
  }
);
Row.displayName = 'Row';

// ── Col ─────────────────────────────────────────────────────────────────────
type ColSize = number | `${number}` | 'auto' | boolean;

export interface ColProps extends React.HTMLAttributes<HTMLDivElement> {
  xs?: ColSize;
  sm?: ColSize;
  md?: ColSize;
  lg?: ColSize;
  xl?: ColSize;
}

/**
 * Width classes for each breakpoint × 1..12 (plus "auto"), written as literals
 * so Tailwind's source scanner emits them — it cannot see class names that are
 * assembled at runtime. (12 maps to w-full since Tailwind has no w-12/12.)
 */
const W = {
  xs: [
    'w-1/12',
    'w-2/12',
    'w-3/12',
    'w-4/12',
    'w-5/12',
    'w-6/12',
    'w-7/12',
    'w-8/12',
    'w-9/12',
    'w-10/12',
    'w-11/12',
    'w-full',
  ],
  sm: [
    'sm:w-1/12',
    'sm:w-2/12',
    'sm:w-3/12',
    'sm:w-4/12',
    'sm:w-5/12',
    'sm:w-6/12',
    'sm:w-7/12',
    'sm:w-8/12',
    'sm:w-9/12',
    'sm:w-10/12',
    'sm:w-11/12',
    'sm:w-full',
  ],
  md: [
    'md:w-1/12',
    'md:w-2/12',
    'md:w-3/12',
    'md:w-4/12',
    'md:w-5/12',
    'md:w-6/12',
    'md:w-7/12',
    'md:w-8/12',
    'md:w-9/12',
    'md:w-10/12',
    'md:w-11/12',
    'md:w-full',
  ],
  lg: [
    'lg:w-1/12',
    'lg:w-2/12',
    'lg:w-3/12',
    'lg:w-4/12',
    'lg:w-5/12',
    'lg:w-6/12',
    'lg:w-7/12',
    'lg:w-8/12',
    'lg:w-9/12',
    'lg:w-10/12',
    'lg:w-11/12',
    'lg:w-full',
  ],
  xl: [
    'xl:w-1/12',
    'xl:w-2/12',
    'xl:w-3/12',
    'xl:w-4/12',
    'xl:w-5/12',
    'xl:w-6/12',
    'xl:w-7/12',
    'xl:w-8/12',
    'xl:w-9/12',
    'xl:w-10/12',
    'xl:w-11/12',
    'xl:w-full',
  ],
} as const;
const W_AUTO: Record<string, string> = {
  xs: 'w-auto',
  sm: 'sm:w-auto',
  md: 'md:w-auto',
  lg: 'lg:w-auto',
  xl: 'xl:w-auto',
};
const W_FLEX: Record<string, string> = {
  xs: 'flex-1',
  sm: 'sm:flex-1',
  md: 'md:flex-1',
  lg: 'lg:flex-1',
  xl: 'xl:flex-1',
};

function sizeClass(bp: keyof typeof W, v: ColSize): string {
  if (v === 'auto') return W_AUTO[bp];
  if (typeof v === 'boolean') return W_FLEX[bp]; // boolean true → equal-width flex
  const n = typeof v === 'number' ? v : parseInt(v, 10);
  return W[bp][Math.min(Math.max(n, 1), 12) - 1];
}

export const Col = React.forwardRef<HTMLDivElement, ColProps>(
  ({ className, style, xs, sm, md, lg, xl, ...props }, ref) => {
    const half = React.useContext(GutterContext);
    const entries: Array<[string, ColSize | undefined]> = [
      ['xs', xs],
      ['sm', sm],
      ['md', md],
      ['lg', lg],
      ['xl', xl],
    ];
    const widthClasses: string[] = [];
    let sized = false;
    for (const [bp, v] of entries) {
      if (v === undefined) continue;
      sized = true;
      widthClasses.push(sizeClass(bp as keyof typeof W, v));
    }
    // Unsized → equal-width flex column. Sized → fixed-basis, no grow/shrink.
    const flexClass = sized ? 'grow-0 shrink-0' : 'flex-1';
    return (
      <div
        ref={ref}
        className={cn(flexClass, ...widthClasses, className)}
        style={{ paddingLeft: `${half}rem`, paddingRight: `${half}rem`, ...style }}
        {...props}
      />
    );
  }
);
Col.displayName = 'Col';
