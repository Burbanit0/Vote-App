import React, { createContext, useCallback, useContext, useRef, useState } from 'react';
import { Toast, ToastContainer } from 'react-bootstrap';

// ── Types ──────────────────────────────────────────────────────────────────

type Variant = 'success' | 'danger' | 'info';

interface ToastItem {
  id: number;
  message: string;
  variant: Variant;
}

interface ToastContextValue {
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
}

// ── Context ────────────────────────────────────────────────────────────────

const ToastContext = createContext<ToastContextValue>({
  success: () => {},
  error: () => {},
  info: () => {},
});

/** Call anywhere inside <ToastProvider> to display a notification. */
export function useToast(): ToastContextValue {
  return useContext(ToastContext);
}

// ── Provider ───────────────────────────────────────────────────────────────

const ICONS: Record<Variant, string> = {
  success: '✓',
  danger:  '✗',
  info:    'ℹ',
};

const AUTO_HIDE_MS = 3000;

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const nextId = useRef(0);

  const push = useCallback((message: string, variant: Variant) => {
    const id = ++nextId.current;
    setToasts((ts) => [...ts, { id, message, variant }]);
    setTimeout(
      () => setToasts((ts) => ts.filter((t) => t.id !== id)),
      AUTO_HIDE_MS + 300 // slight buffer after fade-out
    );
  }, []);

  const ctx: ToastContextValue = {
    success: (msg) => push(msg, 'success'),
    error:   (msg) => push(msg, 'danger'),
    info:    (msg) => push(msg, 'info'),
  };

  return (
    <ToastContext.Provider value={ctx}>
      {children}

      <ToastContainer
        position="bottom-end"
        className="p-3"
        style={{ zIndex: 11000 }}
      >
        {toasts.map(({ id, message, variant }) => (
          <Toast
            key={id}
            bg={variant}
            autohide
            delay={AUTO_HIDE_MS}
            show
            onClose={() => setToasts((ts) => ts.filter((t) => t.id !== id))}
          >
            <Toast.Body
              className={variant === 'info' ? 'text-dark' : 'text-white'}
              style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 500 }}
            >
              <span style={{ fontSize: '1rem' }}>{ICONS[variant]}</span>
              {message}
            </Toast.Body>
          </Toast>
        ))}
      </ToastContainer>
    </ToastContext.Provider>
  );
};
