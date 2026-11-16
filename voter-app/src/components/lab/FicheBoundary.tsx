// One fiche throwing must not take the Laboratoire with it: the app-wide ErrorBoundary
// replaces the whole page, so a single broken fiche cost the reader the rail, the catalogue
// and the other column. This one sits around a fiche's body only — the header, the rail and
// the second column stay up, and Retry remounts just this fiche.
import React, { Component, ErrorInfo, ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';

const Fallback: React.FC<{ onRetry: () => void }> = ({ onRetry }) => {
  const { t } = useTranslation('playground');
  return (
    <div role="alert" data-testid="fiche-error" className="rounded border border-border p-4">
      <p className="font-semibold text-destructive">{t('lab.ficheError.title')}</p>
      <p className="mt-1 text-sm text-muted-foreground">{t('lab.ficheError.body')}</p>
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

class FicheBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[FicheBoundary]', error, info);
  }

  render() {
    return this.state.failed ? (
      <Fallback onRetry={() => this.setState({ failed: false })} />
    ) : (
      this.props.children
    );
  }
}

export default FicheBoundary;
