import React, { Suspense } from 'react';
import { lazyWithPreload } from '../../lib/lazyWithPreload';
import { usePolityCtx } from './PolityController';

// The biography's chunk loads when a citizen is first selected (?citizen=).
const CitizenBiographyPanel = lazyWithPreload(() => import('./CitizenBiographyPanel'));

const CitizenBiography: React.FC = () => {
  const { runKey, citizen } = usePolityCtx();
  if (citizen === null) return null;
  return (
    <Suspense fallback={null}>
      {/* A citizen is only read from the URL once a run is shown, so the run key is set here. */}
      <CitizenBiographyPanel runKey={runKey as string} citizen={citizen} />
    </Suspense>
  );
};

export default CitizenBiography;
