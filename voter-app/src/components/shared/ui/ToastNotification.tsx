import React, { createContext, useCallback, useContext, useRef, useState } from 'react';
import { cn } from '@/lib/utils';

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
// Tailwind-migrated (Phase 6): react-bootstrap Toast/ToastContainer → a fixed
// bottom-end stack of Tailwind toast divs.

const ICONS: Record<Variant, string> = {
  success: '✓',
  danger: '✗',
  info: 'ℹ',
};

const VARIANT_BG: Record<Variant, string> = {
  success: 'bg-[#198754] text-white',
  danger: 'bg-[#dc3545] text-white',
  info: 'bg-[#0dcaf0] text-slate-900',
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
    error: (msg) => push(msg, 'danger'),
    info: (msg) => push(msg, 'info'),
  };

  return (
    <ToastContext.Provider value={ctx}>
      {children}

      <div
        data-style="tailwind"
        className="fixed bottom-0 right-0 z-[11000] flex flex-col gap-2 p-3"
      >
        {toasts.map(({ id, message, variant }) => (
          <div
            key={id}
            role="status"
            className={cn(
              'flex items-center gap-2 rounded-md px-4 py-2 font-medium shadow-lg',
              VARIANT_BG[variant]
            )}
          >
            <span className="text-base">{ICONS[variant]}</span>
            {message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};
