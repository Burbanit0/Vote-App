import React from 'react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';

interface Props {
  loading: boolean;
  className?: string;
}

// The pulsing dot used to come with a hand-written `@keyframes` block injected
// into <head> on first render; `animate-pulse` is the same effect, and
// `motion-reduce:` honours the same preference the rest of the app's animations
// do (see src/styles/tailwind.css).

const LiveBadge: React.FC<Props> = ({ loading, className }) => {
  const { t } = useTranslation();

  if (!loading) return null;

  return (
    <span
      role="status"
      aria-label={t('simulation.recalculating')}
      className={cn(
        'inline-flex select-none items-center text-xs text-muted-foreground',
        className
      )}
    >
      <span
        aria-hidden="true"
        className="mr-1.5 inline-block size-[7px] shrink-0 animate-pulse rounded-full bg-primary align-middle motion-reduce:animate-none"
      />
      {t('simulation.recalculating')}
    </span>
  );
};

export default LiveBadge;
