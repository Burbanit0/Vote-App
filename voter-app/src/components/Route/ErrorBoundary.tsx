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

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error:    Error | null;
  info:     ErrorInfo | null;
  copied:   boolean;
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
    // eslint-disable-next-line no-console
    console.error('[ErrorBoundary]', error, info);
  }

  private handleRetry = (): void => {
    this.setState({ hasError: false, error: null, info: null, copied: false });
  };

  private handleGoHome = (): void => {
    // Force a full reload to /, which also clears any corrupt in-memory state.
    window.location.assign('/');
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

    return (
      <div
        role="alert"
        data-testid="error-boundary"
        style={{
          maxWidth:  720,
          margin:    '2rem auto',
          padding:   '1.5rem',
          border:    '1px solid #f5c2c7',
          borderRadius: 12,
          background: '#fff5f5',
          fontFamily: 'system-ui, sans-serif',
        }}
      >
        <h2 style={{ marginTop: 0, color: '#842029' }}>
          ⚠ Une erreur est survenue
        </h2>
        <p style={{ color: '#495057' }}>
          La page que vous consultiez a planté. Vos données ne sont pas perdues —
          le projet est jeune, ce genre d&apos;erreur arrive. Vous pouvez :
        </p>
        <ul style={{ color: '#495057' }}>
          <li><strong>Réessayer</strong> — recharge le composant en place</li>
          <li><strong>Retour à l&apos;accueil</strong> — recharge complètement l&apos;app</li>
          <li><strong>Copier le détail</strong> — pour le coller dans une issue GitHub</li>
        </ul>

        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: '1rem' }}>
          <button
            onClick={this.handleRetry}
            style={btn('#0d6efd')}
            data-testid="error-boundary-retry"
          >
            ↻ Réessayer
          </button>
          <button
            onClick={this.handleGoHome}
            style={btn('#6c757d')}
            data-testid="error-boundary-home"
          >
            🏠 Retour à l&apos;accueil
          </button>
          <button
            onClick={this.handleCopy}
            style={btn(copied ? '#198754' : '#495057')}
            data-testid="error-boundary-copy"
          >
            {copied ? '✓ Copié' : '📋 Copier le détail'}
          </button>
        </div>

        {/* Dev-only: show the stack inline so we never ship blind */}
        {isDev && error && (
          <details
            open
            style={{ marginTop: '1.5rem' }}
            data-testid="error-boundary-details"
          >
            <summary style={{ cursor: 'pointer', fontWeight: 600, color: '#842029' }}>
              Détail (visible en dev uniquement)
            </summary>
            <pre style={preStyle}>
              {error.name}: {error.message}
              {'\n\n'}
              {error.stack}
              {info?.componentStack && '\n\nComponent stack:'}
              {info?.componentStack}
            </pre>
          </details>
        )}
      </div>
    );
  }
}

function btn(bg: string): React.CSSProperties {
  return {
    background:    bg,
    color:         '#fff',
    border:        'none',
    borderRadius:  6,
    padding:       '8px 14px',
    fontSize:      '0.9rem',
    cursor:        'pointer',
    transition:    'background 0.15s',
  };
}

const preStyle: React.CSSProperties = {
  marginTop:    '0.5rem',
  padding:      '0.75rem',
  background:   '#212529',
  color:        '#f8f9fa',
  borderRadius: 6,
  fontSize:     '0.78rem',
  overflowX:    'auto',
  whiteSpace:   'pre-wrap',
  wordBreak:    'break-word',
};

export default ErrorBoundary;
