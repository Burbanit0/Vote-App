import React, { useEffect, useState } from 'react';
import { useRegisterSW } from 'virtual:pwa-register/react';
import { Button } from '@/components/ui/button';

// ── Tailwind-migrated (Phase 6) — Toast → fixed bottom-end div.
const UpdatePrompt: React.FC = () => {
  const {
    needRefresh: [needRefresh],
    updateServiceWorker,
  } = useRegisterSW();

  const [show, setShow] = useState(false);

  useEffect(() => {
    if (needRefresh) setShow(true);
  }, [needRefresh]);

  if (!show) return null;

  return (
    <div data-style="tailwind" className="fixed bottom-0 right-0 z-[11500] p-3">
      <div className="flex items-center gap-3 rounded-md bg-primary px-4 py-3 text-white shadow-lg">
        <span className="flex-1">Vote Lab a été mis à jour.</span>
        <Button size="sm" variant="light" onClick={() => updateServiceWorker(true)}>
          Recharger
        </Button>
        <button
          type="button"
          aria-label="Fermer"
          className="ml-1 text-white/80 hover:text-white"
          onClick={() => setShow(false)}
        >
          ✕
        </button>
      </div>
    </div>
  );
};

export default UpdatePrompt;
