import * as React from 'react';

import { cn } from '@/lib/utils';

// Canonical shadcn/ui Table (Phase 6), reduced to the part this app uses.
// The shadcn copy-in also ships TableHeader/Body/Footer/Head/Row/Cell wrappers;
// all 36 consumers render plain <thead>/<tbody>/<tr>/<td> inside <Table>, so the
// six wrappers were 60 of this file's 76 lines and were referenced by nothing —
// not even by Table itself. Copy them back from shadcn if a consumer ever wants
// them; unused scaffolding is not an API.
const Table = React.forwardRef<HTMLTableElement, React.HTMLAttributes<HTMLTableElement>>(
  ({ className, ...props }, ref) => (
    <div className="relative w-full overflow-auto">
      <table ref={ref} className={cn('w-full caption-bottom text-sm', className)} {...props} />
    </div>
  )
);
Table.displayName = 'Table';

export { Table };
