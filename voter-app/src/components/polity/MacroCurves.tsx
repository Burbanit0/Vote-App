import React, { Suspense, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Spinner } from '@/components/ui/spinner';
import Collapsible from '../playground/Collapsible';
import { lazyWithPreload } from '../../lib/lazyWithPreload';

// Recharts stays out of the Polity page's first paint (ADR-005): the curves'
// chunk is fetched when the toggle is hovered or focused, and mounted only once
// the panel is opened.
const MacroCurvesPanel = lazyWithPreload(() => import('./MacroCurvesPanel'));

const MacroCurves: React.FC = () => {
  const { t } = useTranslation('polity');
  const [open, setOpen] = useState(false);
  return (
    <Collapsible
      title={t('macro.title')}
      subtitle={t('macro.subtitle')}
      testid="polity-macro"
      onOpenChange={setOpen}
      onPrefetch={() => void MacroCurvesPanel.preload()}
    >
      {open && (
        <Suspense
          fallback={
            <p
              role="status"
              className="flex items-center gap-2 px-3 py-2 text-xs text-muted-foreground"
            >
              <Spinner size="sm" />
              {t('macro.loading')}
            </p>
          }
        >
          <MacroCurvesPanel />
        </Suspense>
      )}
    </Collapsible>
  );
};

export default MacroCurves;
