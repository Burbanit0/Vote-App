// One fiche throwing must not take the Laboratoire with it: the app-wide ErrorBoundary
// replaces the whole page, so a single broken fiche cost the reader the rail, the catalogue
// and the other column. This one sits around a fiche's body only — the header, the rail and
// the second column stay up, and Retry remounts just this fiche.
import React, { Component, ErrorInfo, ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';

// React.lazy caches a rejected import, so remounting the fiche would throw the same error
// again: for a chunk that failed to load (flaky network, a deploy that replaced the hashed
// files), only a reload can recover.
const CHUNK_ERROR =
  /dynamically imported module|loading chunk|importing a module script|ChunkLoadError/i;
const isChunkError = (e: Error): boolean => CHUNK_ERROR.test(`${e.name} ${e.message}`);

const Fallback: React.FC<{ error: Error; onRetry: () => void }> = ({ error, onRetry }) => {
  const { t } = useTranslation('playground');
  return (
    <div role="alert" data-testid="fiche-error" className="rounded border border-border p-4">
      <p className="font-semibold text-destructive">{t('lab.ficheError.title')}</p>
      <p className="mt-1 text-sm text-muted-foreground">{t('lab.ficheError.body')}</p>
      {/* What failed, so a reader can report it (the app-wide boundary offers a copy button). */}
      <p
        data-testid="fiche-error-detail"
        className="mt-1 font-mono text-xs break-words text-muted-foreground"
      >
        {error.name}: {error.message}
      </p>
      <Button
        variant="outline"
        size="sm"
        className="mt-3 gap-1.5"
        onClick={onRetry}
        data-testid="fiche-error-retry"
      >
        <RotateCcw aria-hidden className="h-3.5 w-3.5" />
        {t('lab.ficheError.retry')}
      </Button>
    </div>
  );
};

class FicheBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state: { error: Error | null } = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[FicheBoundary]', error, info);
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;
    const retry = () =>
      isChunkError(error) ? window.location.reload() : this.setState({ error: null });
    return <Fallback error={error} onRetry={retry} />;
  }
}

export default FicheBoundary;
