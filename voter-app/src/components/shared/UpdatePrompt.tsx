import React, { useEffect, useState } from 'react';
import { Button, Toast, ToastContainer } from 'react-bootstrap';
import { useRegisterSW } from 'virtual:pwa-register/react';

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
    <ToastContainer position="bottom-end" className="p-3" style={{ zIndex: 11500 }}>
      <Toast show onClose={() => setShow(false)} bg="primary">
        <Toast.Body className="text-white d-flex align-items-center gap-3">
          <span style={{ flex: 1 }}>Vote Lab a été mis à jour.</span>
          <Button
            size="sm"
            variant="light"
            onClick={() => updateServiceWorker(true)}
          >
            Recharger
          </Button>
        </Toast.Body>
      </Toast>
    </ToastContainer>
  );
};

export default UpdatePrompt;
