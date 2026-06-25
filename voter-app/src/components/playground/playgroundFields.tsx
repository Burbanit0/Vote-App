import * as React from 'react';

// Small field primitives shared by the moment panels (native, Tailwind-styled).

export const Field: React.FC<{ label: string; htmlFor?: string; children: React.ReactNode }> = ({
  label,
  htmlFor,
  children,
}) => (
  <div className="flex flex-col gap-1">
    <label htmlFor={htmlFor} className="text-xs font-medium text-muted-foreground">
      {label}
    </label>
    {children}
  </div>
);

export const selectCls =
  'w-full rounded-md border border-input bg-background px-2 py-1.5 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';

export const AnchorFallback: React.FC = () => (
  <p className="p-2 text-xs text-muted-foreground">Chargement…</p>
);
