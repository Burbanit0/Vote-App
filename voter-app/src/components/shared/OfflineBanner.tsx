import React, { useEffect, useState } from 'react';

// ── Tailwind-migrated (Phase 6) ──────────────────────────────────────────────
// First component moved off react-bootstrap to Tailwind utilities. Marked with
// data-style="tailwind" so migration progress is greppable. The amber palette
// mirrors Bootstrap's `variant="warning"` alert.
const OfflineBanner: React.FC = () => {
  const [offline, setOffline] = useState(!navigator.onLine);

  useEffect(() => {
    const goOffline = () => setOffline(true);
    const goOnline = () => setOffline(false);
    window.addEventListener('offline', goOffline);
    window.addEventListener('online', goOnline);
    return () => {
      window.removeEventListener('offline', goOffline);
      window.removeEventListener('online', goOnline);
    };
  }, []);

  if (!offline) return null;

  return (
    <div
      role="alert"
      data-style="tailwind"
      className="mb-0 border-y border-amber-300 bg-amber-100 px-3 py-2 text-center text-[0.85rem] leading-snug text-amber-900"
    >
      Mode hors-ligne — certaines simulations peuvent être indisponibles. Les pages Quiz,
      Régimes internationaux et Galerie fonctionnent sans réseau.
    </div>
  );
};

export default OfflineBanner;
