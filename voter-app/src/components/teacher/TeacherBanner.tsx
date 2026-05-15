/**
 * TeacherBanner — shown at the top of the page when Teacher Mode is active.
 *
 * Also renders the floating "📌 Add to presentation" capture button so that
 * ANY view can be pinned without modifying existing page components.
 */
import React, { useRef, useState } from 'react';
import { Button, Form, InputGroup, Spinner } from 'react-bootstrap';
import { useNavigate } from 'react-router';
import { useTeacherMode } from '../../context/TeacherModeContext';

// ── Teacher Banner ────────────────────────────────────────────────────────

export const TeacherBanner: React.FC = () => {
  const { teacherMode, slides } = useTeacherMode();
  const navigate = useNavigate();

  if (!teacherMode) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        backgroundColor: '#198754',
        color: 'white',
        padding: '5px 16px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 8,
        fontSize: '0.85rem',
        flexWrap: 'wrap',
      }}
    >
      <span>
        🎓 <strong>Mode Enseignant actif</strong>{' '}
        — {slides.length} slide{slides.length !== 1 ? 's' : ''} en mémoire
      </span>
      <Button
        variant="outline-light"
        size="sm"
        onClick={() => navigate('/teacher/presentation')}
        style={{ fontSize: '0.8rem', padding: '2px 10px' }}
      >
        Gérer la présentation →
      </Button>
    </div>
  );
};

// ── Floating capture button ───────────────────────────────────────────────

export const TeacherCaptureButton: React.FC = () => {
  const { teacherMode, captureScreen, capturing } = useTeacherMode();
  const [open, setOpen]   = useState(false);
  const [title, setTitle] = useState('');
  const inputRef          = useRef<HTMLInputElement>(null);

  if (!teacherMode) return null;

  const handleCapture = async () => {
    await captureScreen(title.trim() || 'Capture sans titre');
    setTitle('');
    setOpen(false);
  };

  const handleOpen = () => {
    setOpen(true);
    // Pre-fill with page title
    setTitle(document.title.replace(' — Vote Lab', '').trim());
    setTimeout(() => inputRef.current?.select(), 60);
  };

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 24,
        right: 24,
        zIndex: 10000,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-end',
        gap: 8,
      }}
    >
      {open && (
        <div
          style={{
            background: 'var(--bs-body-bg, white)',
            border: '1px solid var(--bs-border-color, #dee2e6)',
            borderRadius: 10,
            padding: '12px 14px',
            boxShadow: '0 4px 16px rgba(0,0,0,0.15)',
            width: 280,
          }}
        >
          <div className="fw-semibold mb-2" style={{ fontSize: '0.88rem' }}>
            Titre de la slide
          </div>
          <InputGroup size="sm" className="mb-2">
            <Form.Control
              ref={inputRef}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Ex : Résultats Borda vs IRV"
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleCapture();
                if (e.key === 'Escape') setOpen(false);
              }}
              aria-label="Titre de la slide à capturer"
            />
          </InputGroup>
          <div className="d-flex gap-2">
            <Button
              variant="success"
              size="sm"
              onClick={handleCapture}
              disabled={capturing}
              className="flex-grow-1"
            >
              {capturing ? <><Spinner size="sm" className="me-1" />Capture…</> : '📌 Capturer'}
            </Button>
            <Button variant="outline-secondary" size="sm" onClick={() => setOpen(false)}>
              ✕
            </Button>
          </div>
        </div>
      )}

      <Button
        variant={open ? 'secondary' : 'success'}
        onClick={open ? () => setOpen(false) : handleOpen}
        disabled={capturing}
        style={{ borderRadius: 28, padding: '8px 18px', boxShadow: '0 2px 8px rgba(0,0,0,0.2)' }}
        aria-label="Ajouter la vue actuelle à la présentation"
        title="Ajouter à la présentation"
      >
        {capturing ? <Spinner size="sm" /> : '📌'}
        {!open && <span className="ms-1" style={{ fontSize: '0.82rem' }}>Ajouter</span>}
      </Button>
    </div>
  );
};

// ── PinZone — optional wrapper for explicit pin areas ────────────────────

interface PinZoneProps {
  title: string;
  content?: unknown;
  type?: 'chart' | 'comparison' | 'definition' | 'quiz-question' | 'captured';
  children: React.ReactNode;
  className?: string;
}

/**
 * Wraps a section with a 📌 button overlay when teacher mode is active.
 * Use this in NEW pages/sections — no need to touch existing chart components.
 */
export const PinZone: React.FC<PinZoneProps> = ({
  title, content, type = 'chart', children, className,
}) => {
  const { teacherMode, addSlide } = useTeacherMode();

  return (
    <div
      style={{ position: 'relative' }}
      className={className}
    >
      {children}
      {teacherMode && (
        <button
          onClick={() => addSlide({
            type,
            title,
            content: {
              description: title,
              data: content,
              route: window.location.pathname,
            },
          })}
          title="Ajouter à la présentation enseignant"
          aria-label={`Ajouter « ${title} » à la présentation`}
          style={{
            position: 'absolute',
            top: 6,
            right: 6,
            background: '#198754',
            color: 'white',
            border: 'none',
            borderRadius: 6,
            padding: '3px 8px',
            fontSize: '0.75rem',
            cursor: 'pointer',
            zIndex: 100,
            opacity: 0.85,
            transition: 'opacity 0.15s',
          }}
          onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.opacity = '1'; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.opacity = '0.85'; }}
        >
          📌 Ajouter
        </button>
      )}
    </div>
  );
};
