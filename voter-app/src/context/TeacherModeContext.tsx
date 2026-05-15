/**
 * TeacherModeContext — state and helpers for the Teacher Presentation feature.
 *
 * Slides are persisted in localStorage so they survive page refreshes.
 * Screenshots are captured on-demand via html2canvas.
 */
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react';

// ── Types ───────────────────────────────────────────────────────────────────

export interface Slide {
  id: string;
  type: 'chart' | 'comparison' | 'definition' | 'quiz-question' | 'captured';
  title: string;
  content: {
    screenshot?: string; // base64 data URL (PNG) captured via html2canvas
    route?: string;      // browser path when pinned
    description?: string;
    data?: unknown;      // arbitrary params/state
  };
  notes?: string;
  capturedAt: string;   // ISO string
}

interface TeacherModeContextValue {
  teacherMode: boolean;
  setTeacherMode: (v: boolean) => void;
  slides: Slide[];
  addSlide: (slide: Omit<Slide, 'id' | 'capturedAt'>) => void;
  removeSlide: (id: string) => void;
  reorderSlides: (fromIndex: number, toIndex: number) => void;
  updateSlideNotes: (id: string, notes: string) => void;
  updateSlideTitle: (id: string, title: string) => void;
  captureScreen: (title?: string) => Promise<void>;
  exportPresentation: () => Promise<void>;
  capturing: boolean;
}

// ── Defaults ────────────────────────────────────────────────────────────────

const TeacherModeContext = createContext<TeacherModeContextValue>({
  teacherMode: false,
  setTeacherMode: () => {},
  slides: [],
  addSlide: () => {},
  removeSlide: () => {},
  reorderSlides: () => {},
  updateSlideNotes: () => {},
  updateSlideTitle: () => {},
  captureScreen: async () => {},
  exportPresentation: async () => {},
  capturing: false,
});

export function useTeacherMode(): TeacherModeContextValue {
  return useContext(TeacherModeContext);
}

// ── Storage helpers ─────────────────────────────────────────────────────────

const LS_SLIDES = 'votelab_teacher_slides';

function loadSlides(): Slide[] {
  try {
    const raw = localStorage.getItem(LS_SLIDES);
    if (!raw) return [];
    return JSON.parse(raw) as Slide[];
  } catch {
    return [];
  }
}

function saveSlides(slides: Slide[]): void {
  try {
    localStorage.setItem(LS_SLIDES, JSON.stringify(slides));
  } catch {
    // Storage quota exceeded — silently ignore
  }
}

function uid(): string {
  return `slide-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

// ── Provider ────────────────────────────────────────────────────────────────

export const TeacherModeProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [teacherMode, setTeacherModeState] = useState(false);
  const [slides, setSlides] = useState<Slide[]>(() => loadSlides());
  const [capturing, setCapturing] = useState(false);
  const pendingCapture = useRef<AbortController | null>(null);

  // Persist slides to localStorage whenever they change
  useEffect(() => {
    saveSlides(slides);
  }, [slides]);

  const setTeacherMode = useCallback((v: boolean) => {
    setTeacherModeState(v);
  }, []);

  const addSlide = useCallback((slide: Omit<Slide, 'id' | 'capturedAt'>) => {
    const full: Slide = { ...slide, id: uid(), capturedAt: new Date().toISOString() };
    setSlides((prev) => [...prev, full]);
  }, []);

  const removeSlide = useCallback((id: string) => {
    setSlides((prev) => prev.filter((s) => s.id !== id));
  }, []);

  const reorderSlides = useCallback((fromIndex: number, toIndex: number) => {
    setSlides((prev) => {
      const arr = [...prev];
      const [moved] = arr.splice(fromIndex, 1);
      arr.splice(toIndex, 0, moved);
      return arr;
    });
  }, []);

  const updateSlideNotes = useCallback((id: string, notes: string) => {
    setSlides((prev) => prev.map((s) => (s.id === id ? { ...s, notes } : s)));
  }, []);

  const updateSlideTitle = useCallback((id: string, title: string) => {
    setSlides((prev) => prev.map((s) => (s.id === id ? { ...s, title } : s)));
  }, []);

  const captureScreen = useCallback(async (title = 'Capture') => {
    if (capturing) return;
    setCapturing(true);
    try {
      // Dynamically import to avoid bloating the initial bundle
      const { default: html2canvas } = await import('html2canvas');
      const target = document.getElementById('teacher-capture-root') ?? document.body;
      const canvas = await html2canvas(target, {
        useCORS: true,
        allowTaint: true,
        scale: 1,
        logging: false,
      });
      const screenshot = canvas.toDataURL('image/png');
      addSlide({
        type: 'captured',
        title: title || 'Capture',
        content: {
          screenshot,
          route: window.location.pathname + window.location.search,
          description: document.title,
        },
      });
    } catch {
      // Capture failed — add slide without screenshot
      addSlide({
        type: 'captured',
        title: title || 'Capture',
        content: {
          route: window.location.pathname,
          description: document.title,
        },
      });
    } finally {
      setCapturing(false);
    }
  }, [capturing, addSlide]);

  const exportPresentation = useCallback(async () => {
    if (!slides.length) return;
    try {
      const [{ default: jsPDF }, { default: html2canvas }] = await Promise.all([
        import('jspdf'),
        import('html2canvas'),
      ]);

      const pdf = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' });
      const W = 297, H = 210;  // A4 landscape mm
      const NOTES_H = 18;      // reserved for notes zone at bottom

      for (let i = 0; i < slides.length; i++) {
        if (i > 0) pdf.addPage();
        const slide = slides[i];

        // ── Slide number + title ───────────────────────────────────────────
        pdf.setFontSize(9);
        pdf.setTextColor(160, 160, 160);
        pdf.text(`${i + 1} / ${slides.length}`, W - 12, 8, { align: 'right' });
        pdf.setFontSize(14);
        pdf.setTextColor(30, 30, 30);
        pdf.text(slide.title, 10, 14);

        // ── Slide content (screenshot or placeholder) ─────────────────────
        const contentY = 18;
        const contentH = H - contentY - NOTES_H - 4;

        if (slide.content.screenshot) {
          pdf.addImage(slide.content.screenshot, 'PNG', 10, contentY, W - 20, contentH);
        } else {
          // Capture the slide preview element live
          const el = document.getElementById(`slide-export-${slide.id}`);
          if (el) {
            const canvas = await html2canvas(el, { scale: 2, useCORS: true, logging: false });
            const img = canvas.toDataURL('image/png');
            pdf.addImage(img, 'PNG', 10, contentY, W - 20, contentH);
          } else {
            // Placeholder
            pdf.setFillColor(240, 240, 240);
            pdf.rect(10, contentY, W - 20, contentH, 'F');
            pdf.setFontSize(11);
            pdf.setTextColor(100, 100, 100);
            pdf.text(slide.content.description ?? slide.title, W / 2, contentY + contentH / 2, { align: 'center' });
          }
        }

        // ── Notes zone ─────────────────────────────────────────────────────
        if (slide.notes?.trim()) {
          const notesY = H - NOTES_H;
          pdf.setFillColor(245, 245, 245);
          pdf.rect(0, notesY, W, NOTES_H, 'F');
          pdf.setDrawColor(220, 220, 220);
          pdf.line(0, notesY, W, notesY);
          pdf.setFontSize(8);
          pdf.setTextColor(80, 80, 80);
          pdf.text('Notes :', 6, notesY + 5);
          const noteLines = pdf.splitTextToSize(slide.notes, W - 16);
          pdf.text(noteLines.slice(0, 2), 6, notesY + 10);
        }
      }

      pdf.save('presentation-vote-lab.pdf');
    } catch (e) {
      console.error('PDF export failed', e);
    }
  }, [slides]);

  return (
    <TeacherModeContext.Provider
      value={{
        teacherMode, setTeacherMode,
        slides, addSlide, removeSlide, reorderSlides,
        updateSlideNotes, updateSlideTitle,
        captureScreen, exportPresentation,
        capturing,
      }}
    >
      {children}
    </TeacherModeContext.Provider>
  );
};
