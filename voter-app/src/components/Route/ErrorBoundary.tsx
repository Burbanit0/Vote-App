/**
 * ErrorBoundary — top-level safety net for React render errors.
 *
 * Without monitoring (no Sentry in this iteration of the project — see
 * STRATEGIC_REFACTOR_PLAN.md Phase 0), this is our only way to:
 *   1. Prevent a white screen of death when any component throws,
 *   2. Give the user a meaningful action ("retry" or "go home"),
 *   3. Let the user / a tester copy the full stack trace to send to us,
 *   4. Show the error in dev so we don't ship subtle regressions blind.
 *
 * Once an observability stack is added (Phase 7+), componentDidCatch will
 * also forward to Sentry / Glitchtip without changing the component API.
 */
import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Check, Copy, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Slip } from '@/components/ui/slip';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  info: ErrorInfo | null;
  copied: boolean;
}

class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null, info: null, copied: false };

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    this.setState({ info });
    // Console always — devtools is the primary debugging surface today.
    // When Sentry/Glitchtip arrives in Phase 7+, wire it here too:
    //   Sentry.captureException(error, { contexts: { react: info } });

    console.error('[ErrorBoundary]', error, info);
  }

  private handleRetry = (): void => {
    this.setState({ hasError: false, error: null, info: null, copied: false });
  };

  private handleGoHome = (): void => {
    // Force a full reload to /, which also clears any corrupt in-memory state.
    window.location.assign(import.meta.env.BASE_URL);
  };

  private handleCopy = async (): Promise<void> => {
    const { error, info } = this.state;
    const payload = [
      `URL: ${window.location.href}`,
      `User-Agent: ${navigator.userAgent}`,
      `Date: ${new Date().toISOString()}`,
      `Error: ${error?.name ?? 'Error'}: ${error?.message ?? '(no message)'}`,
      '',
      'Stack:',
      error?.stack ?? '(no stack)',
      '',
      'Component stack:',
      info?.componentStack ?? '(no component stack)',
    ].join('\n');
    try {
      await navigator.clipboard.writeText(payload);
      this.setState({ copied: true });
      setTimeout(() => this.setState({ copied: false }), 2000);
    } catch {
      // Clipboard API can be blocked (permissions, insecure context). Silent fall-through.
    }
  };

  render() {
    if (!this.state.hasError) return this.props.children;

    // Use process.env.NODE_ENV (replaced by Vite at build time, and provided
    // by Jest at test time) rather than import.meta.env to keep Jest happy.
    const isDev = process.env.NODE_ENV !== 'production';
    const { error, info, copied } = this.state;

    // A spoiled ballot, like the 404: a slip stamped in violet, the page's own buttons.
    return (
      <div role="alert" data-testid="error-boundary" className="mx-auto max-w-3xl px-4 py-14">
        <Slip fold={28} className="px-6 py-6 sm:px-8 sm:py-8">
          <span className="home-stamp inline-block rounded border-[2.5px] border-ballot-stamp px-2.5 pt-px pb-0.5 font-display text-[19px] leading-[1.2] font-extrabold tracking-[0.08em] text-ballot-stamp uppercase">
            Nul
          </span>
          <h2 className="mt-4 font-display text-[36px] leading-none font-extrabold sm:text-[44px]">
            Une erreur est survenue
          </h2>
          <p className="mt-3 text-base text-muted-foreground">
            La page que vous consultiez a planté. Vos données ne sont pas perdues — le projet est
            jeune, ce genre d&apos;erreur arrive. Vous pouvez :
          </p>
          <ul className="mt-2 list-disc pl-5 text-base text-muted-foreground">
            <li>
              <strong className="text-foreground">Réessayer</strong> — recharge le composant en
              place
            </li>
            <li>
              <strong className="text-foreground">Retour à l&apos;accueil</strong> — recharge
              complètement l&apos;app
            </li>
            <li>
              <strong className="text-foreground">Copier le détail</strong> — pour le coller dans
              une issue GitHub
            </li>
          </ul>

          <div className="mt-6 flex flex-wrap gap-3">
            <Button variant="primary" onClick={this.handleRetry} data-testid="error-boundary-retry">
              <RotateCcw aria-hidden className="h-4 w-4" /> Réessayer
            </Button>
            <Button variant="outline" onClick={this.handleGoHome} data-testid="error-boundary-home">
              Retour à l&apos;accueil
            </Button>
            <Button variant="outline" onClick={this.handleCopy} data-testid="error-boundary-copy">
              {copied ? (
                <Check aria-hidden className="h-4 w-4 text-ok" />
              ) : (
                <Copy aria-hidden className="h-4 w-4" />
              )}
              {copied ? 'Copié' : 'Copier le détail'}
            </Button>
          </div>

          {/* Dev-only: show the stack inline so we never ship blind */}
          {isDev && error && (
            <details open className="mt-6" data-testid="error-boundary-details">
              <summary className="cursor-pointer font-semibold text-destructive">
                Détail (visible en dev uniquement)
              </summary>
              <pre className="mt-2 overflow-x-auto rounded-lg bg-foreground p-3 text-xs break-words whitespace-pre-wrap text-background">
                {error.name}: {error.message}
                {'\n\n'}
                {error.stack}
                {info?.componentStack && '\n\nComponent stack:'}
                {info?.componentStack}
              </pre>
            </details>
          )}
        </Slip>
      </div>
    );
  }
}

export default ErrorBoundary;
