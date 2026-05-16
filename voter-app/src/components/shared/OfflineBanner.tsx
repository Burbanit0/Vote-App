import React, { useEffect, useState } from 'react';
import { Alert } from 'react-bootstrap';

const OfflineBanner: React.FC = () => {
  const [offline, setOffline] = useState(!navigator.onLine);

  useEffect(() => {
    const goOffline = () => setOffline(true);
    const goOnline  = () => setOffline(false);
    window.addEventListener('offline', goOffline);
    window.addEventListener('online',  goOnline);
    return () => {
      window.removeEventListener('offline', goOffline);
      window.removeEventListener('online',  goOnline);
    };
  }, []);

  if (!offline) return null;

  return (
    <Alert
      variant="warning"
      className="mb-0 py-2 text-center rounded-0"
      style={{ fontSize: '0.85rem', borderRadius: 0, borderLeft: 'none', borderRight: 'none' }}
    >
      Mode hors-ligne — certaines simulations peuvent être indisponibles.
      Les pages Quiz, Régimes internationaux et Galerie fonctionnent sans réseau.
    </Alert>
  );
};

export default OfflineBanner;
