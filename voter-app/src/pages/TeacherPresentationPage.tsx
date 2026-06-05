import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Control } from '@/components/ui/form-controls';
import { Container } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import { useNavigate } from 'react-router';
import { Slide, useTeacherMode } from '../stores/useUIStore';
import { useMetaTags } from '../hooks/useMetaTags';

// ── Slide preview ────────────────────────────────────────────────────────────

const SlidePreview: React.FC<{ slide: Slide; previewRef?: React.Ref<HTMLDivElement> }> = ({
  slide,
  previewRef,
}) => {
  const TYPE_ICONS: Record<string, string> = {
    chart: '📊',
    comparison: '⚖️',
    definition: '📖',
    'quiz-question': '❓',
    captured: '📸',
  };

  return (
    <div
      ref={previewRef}
      id={`slide-export-${slide.id}`}
      style={{
        width: '100%',
        aspectRatio: '16/9',
        background: 'var(--bs-secondary-bg, #f8f9fa)',
        borderRadius: 8,
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
      }}
    >
      {slide.content.screenshot ? (
        // ── Screenshot view ────────────────────────────────────────────────
        <img
          src={slide.content.screenshot}
          alt={slide.title}
          style={{ width: '100%', height: '100%', objectFit: 'contain' }}
        />
      ) : (
        // ── Text placeholder ───────────────────────────────────────────────
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 32,
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: '3rem', marginBottom: 12 }} aria-hidden="true">
            {TYPE_ICONS[slide.type] ?? '📄'}
          </div>
          <h4 className="font-bold mb-2">{slide.title}</h4>
          {slide.content.description && (
            <p className="text-muted-foreground mb-3" style={{ fontSize: '0.9rem' }}>
              {slide.content.description}
            </p>
          )}
          {slide.content.route && (
            <Badge variant="secondary" style={{ fontSize: '0.75rem' }}>
              {slide.content.route}
            </Badge>
          )}
        </div>
      )}
      {/* Slide number overlay */}
      <div
        style={{
          position: 'absolute',
          bottom: 8,
          right: 10,
          background: 'rgba(0,0,0,0.35)',
          color: 'white',
          borderRadius: 4,
          padding: '1px 7px',
          fontSize: '0.72rem',
        }}
        aria-hidden="true"
      >
        {slide.type}
      </div>
    </div>
  );
};

// ── Drag-and-drop list item ──────────────────────────────────────────────────

interface SidebarItemProps {
  slide: Slide;
  index: number;
  isActive: boolean;
  onSelect: () => void;
  onRemove: () => void;
  onDragStart: (e: React.DragEvent) => void;
  onDragOver: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent) => void;
}

const SidebarItem: React.FC<SidebarItemProps> = ({
  slide,
  index,
  isActive,
  onSelect,
  onRemove,
  onDragStart,
  onDragOver,
  onDrop,
}) => (
  <div
    draggable
    onDragStart={onDragStart}
    onDragOver={(e) => {
      e.preventDefault();
      onDragOver(e);
    }}
    onDrop={(e) => {
      e.preventDefault();
      onDrop(e);
    }}
    onClick={onSelect}
    role="button"
    tabIndex={0}
    aria-current={isActive}
    aria-label={`Slide ${index + 1}: ${slide.title}`}
    onKeyDown={(e) => {
      if (e.key === 'Enter' || e.key === ' ') onSelect();
    }}
    style={{
      cursor: 'grab',
      padding: '8px 10px',
      borderRadius: 6,
      border: '1px solid',
      borderColor: isActive ? '#0d6efd' : 'var(--bs-border-color, #dee2e6)',
      background: isActive ? '#e7f1ff' : 'var(--bs-body-bg, white)',
      marginBottom: 6,
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      userSelect: 'none',
    }}
  >
    <span className="text-muted-foreground" style={{ fontSize: '0.72rem', minWidth: 18 }}>
      {index + 1}
    </span>
    <div style={{ flex: 1, overflow: 'hidden' }}>
      {slide.content.screenshot ? (
        <img
          src={slide.content.screenshot}
          alt=""
          style={{ width: '100%', height: 36, objectFit: 'cover', borderRadius: 3 }}
        />
      ) : (
        <div
          style={{
            height: 36,
            background: 'var(--bs-secondary-bg, #e9ecef)',
            borderRadius: 3,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '0.75rem',
            color: '#6c757d',
            overflow: 'hidden',
            padding: '0 4px',
          }}
        >
          {slide.title}
        </div>
      )}
    </div>
    <button
      onClick={(e) => {
        e.stopPropagation();
        onRemove();
      }}
      aria-label={`Supprimer la slide ${index + 1}`}
      style={{
        background: 'none',
        border: 'none',
        cursor: 'pointer',
        color: '#dc3545',
        fontSize: '0.8rem',
        padding: 0,
        flexShrink: 0,
      }}
    >
      ✕
    </button>
  </div>
);

// ── TeacherPresentationPage ──────────────────────────────────────────────────

const TeacherPresentationPage: React.FC = () => {
  useMetaTags({ title: 'Présentation — Mode Enseignant — Vote Lab', description: '' });

  const navigate = useNavigate();
  const {
    teacherMode,
    slides,
    removeSlide,
    reorderSlides,
    updateSlideNotes,
    updateSlideTitle,
    exportPresentation,
    captureScreen,
    capturing,
  } = useTeacherMode();

  const [activeIdx, setActiveIdx] = useState(0);
  const [fullscreen, setFullscreen] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [dragFrom, setDragFrom] = useState<number | null>(null);
  const previewRef = useRef<HTMLDivElement>(null);
  const fsContainerRef = useRef<HTMLDivElement>(null);

  const active = slides[activeIdx] ?? slides[0] ?? null;

  // ── Keyboard navigation ────────────────────────────────────────────────────
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        setActiveIdx((i) => Math.min(slides.length - 1, i + 1));
      }
      if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        setActiveIdx((i) => Math.max(0, i - 1));
      }
      if (e.key === 'Escape' && fullscreen) {
        setFullscreen(false);
      }
      if (e.key === 'f' || e.key === 'F') {
        setFullscreen((v) => !v);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [slides.length, fullscreen]);

  // ── Fullscreen API ─────────────────────────────────────────────────────────
  const toggleFullscreen = useCallback(async () => {
    if (!fullscreen) {
      try {
        await fsContainerRef.current?.requestFullscreen?.();
      } catch {
        /* Fullscreen blocked in some browsers */
      }
      setFullscreen(true);
    } else {
      if (document.fullscreenElement) await document.exitFullscreen?.();
      setFullscreen(false);
    }
  }, [fullscreen]);

  useEffect(() => {
    const onFsChange = () => {
      if (!document.fullscreenElement) setFullscreen(false);
    };
    document.addEventListener('fullscreenchange', onFsChange);
    return () => document.removeEventListener('fullscreenchange', onFsChange);
  }, []);

  // ── PDF export ─────────────────────────────────────────────────────────────
  const handleExport = useCallback(async () => {
    setExporting(true);
    await exportPresentation();
    setExporting(false);
  }, [exportPresentation]);

  // ── Drag-and-drop ──────────────────────────────────────────────────────────
  const handleDragStart = useCallback((index: number) => {
    setDragFrom(index);
  }, []);

  const handleDrop = useCallback(
    (index: number) => {
      if (dragFrom === null || dragFrom === index) return;
      reorderSlides(dragFrom, index);
      setActiveIdx(index);
      setDragFrom(null);
    },
    [dragFrom, reorderSlides]
  );

  // ── Password guard ─────────────────────────────────────────────────────────
  if (!teacherMode) {
    return (
      <Container className="py-5 text-center" style={{ maxWidth: 500 }}>
        <div style={{ fontSize: '3rem' }}>🎓</div>
        <h2 className="mt-3 mb-2">Mode Enseignant</h2>
        <p className="text-muted-foreground mb-4">
          Le mode enseignant n'est pas activé. Cliquez sur 🎓 dans la barre de navigation pour
          l'activer.
        </p>
        <Button variant="primary" onClick={() => navigate('/')}>
          Retour à l'accueil
        </Button>
      </Container>
    );
  }

  if (!slides.length) {
    return (
      <Container className="py-5" style={{ maxWidth: 680 }}>
        <h2 className="mb-3 font-bold">🎓 Présentation enseignant</h2>
        <Alert variant="info">
          <strong>Aucune slide encore.</strong> Naviguez dans Vote Lab et cliquez sur{' '}
          <strong>📌 Ajouter</strong> pour capturer des vues. Vous pouvez aussi utiliser le bouton
          flottant "📌 Ajouter" visible en mode enseignant.
        </Alert>
        <Button variant="outline-primary" onClick={() => captureScreen()} disabled={capturing}>
          {capturing ? (
            <>
              <Spinner size="sm" /> Capture…
            </>
          ) : (
            '📸 Capturer la vue actuelle'
          )}
        </Button>
        <Button variant="outline-secondary" className="ms-2" onClick={() => navigate('/')}>
          Aller sur Vote Lab
        </Button>
      </Container>
    );
  }

  // ── Fullscreen overlay ─────────────────────────────────────────────────────
  if (fullscreen) {
    return (
      <div
        ref={fsContainerRef}
        style={{
          position: 'fixed',
          inset: 0,
          background: '#111',
          zIndex: 99999,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* FS Header */}
        <div
          style={{
            background: '#0d6efd',
            color: 'white',
            padding: '6px 16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexShrink: 0,
          }}
        >
          <span className="font-semibold">{active?.title}</span>
          <div className="flex items-center gap-3">
            <span style={{ fontSize: '0.85rem', opacity: 0.8 }}>
              {activeIdx + 1} / {slides.length}
            </span>
            <button
              onClick={() => setFullscreen(false)}
              style={{
                background: 'none',
                border: 'none',
                color: 'white',
                cursor: 'pointer',
                fontSize: '1rem',
              }}
              aria-label="Quitter le plein écran"
            >
              ✕ <span style={{ fontSize: '0.75rem', opacity: 0.7 }}>Échap</span>
            </button>
          </div>
        </div>

        {/* FS Content */}
        <div
          style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 20,
          }}
        >
          {active && <SlidePreview slide={active} />}
        </div>

        {/* FS Nav */}
        <div
          style={{
            background: '#222',
            padding: '10px 16px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexShrink: 0,
          }}
        >
          <Button
            variant="outline-light"
            size="sm"
            disabled={activeIdx === 0}
            onClick={() => setActiveIdx((i) => i - 1)}
          >
            ← Précédente
          </Button>
          <div style={{ display: 'flex', gap: 6 }}>
            {slides.map((_, i) => (
              <button
                key={i}
                onClick={() => setActiveIdx(i)}
                aria-label={`Aller à la slide ${i + 1}`}
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  border: 'none',
                  cursor: 'pointer',
                  padding: 0,
                  background: i === activeIdx ? '#0d6efd' : '#666',
                }}
              />
            ))}
          </div>
          <Button
            variant="outline-light"
            size="sm"
            disabled={activeIdx === slides.length - 1}
            onClick={() => setActiveIdx((i) => i + 1)}
          >
            Suivante →
          </Button>
        </div>
      </div>
    );
  }

  // ── Normal editor view ─────────────────────────────────────────────────────
  return (
    <div
      style={{
        height: 'calc(100vh - 56px)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* Header toolbar */}
      <div
        className="flex items-center gap-2 flex-wrap border-b border-border py-2 px-3"
        style={{ flexShrink: 0, background: 'var(--bs-body-bg, white)' }}
      >
        <h5 className="mb-0 font-bold">🎓 Présentation</h5>
        <Badge variant="secondary">
          {slides.length} slide{slides.length !== 1 ? 's' : ''}
        </Badge>
        <span className="mr-auto text-muted-foreground text-sm">
          ← → pour naviguer · F = plein écran
        </span>

        <Button
          variant="outline-secondary"
          size="sm"
          onClick={() => captureScreen()}
          disabled={capturing}
        >
          {capturing ? <Spinner size="sm" /> : '📸 Capturer la vue'}
        </Button>
        <Button variant="outline-primary" size="sm" onClick={toggleFullscreen}>
          ⛶ Plein écran
        </Button>
        <Button
          variant="success"
          size="sm"
          onClick={handleExport}
          disabled={exporting || !slides.length}
        >
          {exporting ? (
            <>
              <Spinner size="sm" className="me-1" />
              Export…
            </>
          ) : (
            '⬇ PDF'
          )}
        </Button>
      </div>

      {/* Main layout */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* ── Sidebar ── */}
        <div
          style={{
            width: 200,
            borderRight: '1px solid var(--bs-border-color, #dee2e6)',
            padding: 10,
            overflowY: 'auto',
            flexShrink: 0,
            background: 'var(--bs-secondary-bg, #f8f9fa)',
          }}
          role="list"
          aria-label="Liste des slides"
        >
          {slides.map((s, i) => (
            <SidebarItem
              key={s.id}
              slide={s}
              index={i}
              isActive={i === activeIdx}
              onSelect={() => setActiveIdx(i)}
              onRemove={() => {
                removeSlide(s.id);
                if (activeIdx >= slides.length - 1) setActiveIdx(Math.max(0, slides.length - 2));
              }}
              onDragStart={() => handleDragStart(i)}
              onDragOver={() => {}}
              onDrop={() => handleDrop(i)}
            />
          ))}
        </div>

        {/* ── Preview + Notes ── */}
        <div style={{ flex: 1, overflow: 'auto', padding: 16 }} ref={fsContainerRef}>
          {active ? (
            <>
              {/* Title editable */}
              <Control
                value={active.title}
                onChange={(e) => updateSlideTitle(active.id, e.target.value)}
                className="font-bold mb-3 border-0 ps-0 text-lg"
                style={{ boxShadow: 'none', background: 'transparent' }}
                aria-label="Titre de la slide"
              />

              {/* Slide preview */}
              <Card className="mb-3 shadow-sm">
                <CardBody className="p-2">
                  <SlidePreview slide={active} previewRef={previewRef} />
                </CardBody>
              </Card>

              {/* Navigation buttons */}
              <div className="flex justify-between items-center mb-3">
                <Button
                  variant="outline-secondary"
                  size="sm"
                  onClick={() => setActiveIdx((i) => Math.max(0, i - 1))}
                  disabled={activeIdx === 0}
                >
                  ← Précédente
                </Button>
                <span className="text-muted-foreground text-sm">
                  {activeIdx + 1} / {slides.length}
                </span>
                <Button
                  variant="outline-secondary"
                  size="sm"
                  onClick={() => setActiveIdx((i) => Math.min(slides.length - 1, i + 1))}
                  disabled={activeIdx === slides.length - 1}
                >
                  Suivante →
                </Button>
              </div>

              {/* Notes */}
              <Card>
                <CardHeader className="block space-y-0 border-b border-border px-4 py-2 py-2">
                  <small className="font-semibold text-muted-foreground">
                    📝 Notes de l'enseignant
                  </small>
                  <small className="text-muted-foreground ms-2">
                    (non affichées pendant la présentation)
                  </small>
                </CardHeader>
                <CardBody className="p-2">
                  <Control
                    as="textarea"
                    rows={4}
                    value={active.notes ?? ''}
                    onChange={(e) => updateSlideNotes(active.id, e.target.value)}
                    placeholder="Ajoutez vos notes pédagogiques ici…"
                    style={{ fontSize: '0.88rem', resize: 'vertical' }}
                    aria-label="Notes de l'enseignant"
                  />
                </CardBody>
              </Card>

              <div className="mt-2 text-right">
                <small className="text-muted-foreground">
                  Capturé le {new Date(active.capturedAt).toLocaleString('fr-FR')}
                </small>
              </div>
            </>
          ) : (
            <Alert variant="info">Sélectionnez une slide dans la liste.</Alert>
          )}
        </div>
      </div>
    </div>
  );
};

export default TeacherPresentationPage;
