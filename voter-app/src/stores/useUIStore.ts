/**
 * useUIStore — UI-preferences slice (Phase 5.4).
 *
 * Consolidates the three small UI contexts:
 *   - theme            (light/dark, persisted as votelab_theme, sets data-bs-theme)
 *   - expertMode       (persisted as votelab_expert)
 *   - teacherMode      + slides/capture/export (slides persisted as
 *                        votelab_teacher_slides)
 *
 * Each former context (ThemeContext / ExpertModeContext / TeacherModeContext)
 * is now a thin shim over this store so consumers + the providers in App.tsx
 * keep working until 5.5 deletes the shims.
 */
import { create } from 'zustand';

// ── Types ───────────────────────────────────────────────────────────────────

export type Theme = 'light' | 'dark';

export interface Slide {
  id: string;
  type: 'chart' | 'comparison' | 'definition' | 'quiz-question' | 'captured';
  title: string;
  content: {
    screenshot?: string;
    route?: string;
    description?: string;
    data?: unknown;
  };
  notes?: string;
  capturedAt: string;
}

interface UIState {
  /** Re-read theme/expert/slides from localStorage; reset teacherMode (mount). */
  hydrate: () => void;
  // Theme
  theme: Theme;
  toggleTheme: () => void;
  // Expert mode
  expertMode: boolean;
  setExpertMode: (value: boolean) => void;
  // Teacher mode
  teacherMode: boolean;
  setTeacherMode: (v: boolean) => void;
  slides: Slide[];
  capturing: boolean;
  addSlide: (slide: Omit<Slide, 'id' | 'capturedAt'>) => void;
  removeSlide: (id: string) => void;
  reorderSlides: (fromIndex: number, toIndex: number) => void;
  updateSlideNotes: (id: string, notes: string) => void;
  updateSlideTitle: (id: string, title: string) => void;
  captureScreen: (title?: string) => Promise<void>;
  exportPresentation: () => Promise<void>;
}

// ── Storage helpers ─────────────────────────────────────────────────────────

const LS_SLIDES = 'votelab_teacher_slides';

function initialTheme(): Theme {
  if (typeof window === 'undefined') return 'light';
  return (localStorage.getItem('votelab_theme') as Theme) ?? 'light';
}

function initialExpert(): boolean {
  if (typeof window === 'undefined') return false;
  return localStorage.getItem('votelab_expert') === 'true';
}

function loadSlides(): Slide[] {
  try {
    const raw = localStorage.getItem(LS_SLIDES);
    return raw ? (JSON.parse(raw) as Slide[]) : [];
  } catch {
    return [];
  }
}

function saveSlides(slides: Slide[]): void {
  try {
    localStorage.setItem(LS_SLIDES, JSON.stringify(slides));
  } catch {
    // quota exceeded — ignore
  }
}

function applyTheme(theme: Theme) {
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('data-bs-theme', theme);
  }
}

function uid(): string {
  return `slide-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

// ── Store ─────────────────────────────────────────────────────────────────

export const useUIStore = create<UIState>((set, get) => ({
  hydrate: () => {
    const theme = initialTheme();
    applyTheme(theme);
    set({ theme, expertMode: initialExpert(), slides: loadSlides(), teacherMode: false });
  },

  // ── Theme ──
  theme: initialTheme(),
  toggleTheme: () => {
    const next: Theme = get().theme === 'light' ? 'dark' : 'light';
    localStorage.setItem('votelab_theme', next);
    applyTheme(next);
    set({ theme: next });
  },

  // ── Expert mode ──
  expertMode: initialExpert(),
  setExpertMode: (value) => {
    localStorage.setItem('votelab_expert', String(value));
    set({ expertMode: value });
  },

  // ── Teacher mode ──
  teacherMode: false,
  setTeacherMode: (v) => set({ teacherMode: v }),
  slides: loadSlides(),
  capturing: false,

  addSlide: (slide) => {
    const full: Slide = { ...slide, id: uid(), capturedAt: new Date().toISOString() };
    const slides = [...get().slides, full];
    saveSlides(slides);
    set({ slides });
  },
  removeSlide: (id) => {
    const slides = get().slides.filter((s) => s.id !== id);
    saveSlides(slides);
    set({ slides });
  },
  reorderSlides: (fromIndex, toIndex) => {
    const arr = [...get().slides];
    const [moved] = arr.splice(fromIndex, 1);
    arr.splice(toIndex, 0, moved);
    saveSlides(arr);
    set({ slides: arr });
  },
  updateSlideNotes: (id, notes) => {
    const slides = get().slides.map((s) => (s.id === id ? { ...s, notes } : s));
    saveSlides(slides);
    set({ slides });
  },
  updateSlideTitle: (id, title) => {
    const slides = get().slides.map((s) => (s.id === id ? { ...s, title } : s));
    saveSlides(slides);
    set({ slides });
  },

  captureScreen: async (title = 'Capture') => {
    if (get().capturing) return;
    set({ capturing: true });
    try {
      const { default: html2canvas } = await import('html2canvas');
      const target = document.getElementById('teacher-capture-root') ?? document.body;
      const canvas = await html2canvas(target, {
        useCORS: true, allowTaint: true, scale: 1, logging: false,
      });
      const screenshot = canvas.toDataURL('image/png');
      get().addSlide({
        type: 'captured',
        title: title || 'Capture',
        content: {
          screenshot,
          route: window.location.pathname + window.location.search,
          description: document.title,
        },
      });
    } catch {
      get().addSlide({
        type: 'captured',
        title: title || 'Capture',
        content: { route: window.location.pathname, description: document.title },
      });
    } finally {
      set({ capturing: false });
    }
  },

  exportPresentation: async () => {
    const slides = get().slides;
    if (!slides.length) return;
    try {
      const [{ default: jsPDF }, { default: html2canvas }] = await Promise.all([
        import('jspdf'),
        import('html2canvas'),
      ]);

      const pdf = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' });
      const W = 297, H = 210;
      const NOTES_H = 18;

      for (let i = 0; i < slides.length; i++) {
        if (i > 0) pdf.addPage();
        const slide = slides[i];

        pdf.setFontSize(9);
        pdf.setTextColor(160, 160, 160);
        pdf.text(`${i + 1} / ${slides.length}`, W - 12, 8, { align: 'right' });
        pdf.setFontSize(14);
        pdf.setTextColor(30, 30, 30);
        pdf.text(slide.title, 10, 14);

        const contentY = 18;
        const contentH = H - contentY - NOTES_H - 4;

        if (slide.content.screenshot) {
          pdf.addImage(slide.content.screenshot, 'PNG', 10, contentY, W - 20, contentH);
        } else {
          const el = document.getElementById(`slide-export-${slide.id}`);
          if (el) {
            const canvas = await html2canvas(el, { scale: 2, useCORS: true, logging: false });
            const img = canvas.toDataURL('image/png');
            pdf.addImage(img, 'PNG', 10, contentY, W - 20, contentH);
          } else {
            pdf.setFillColor(240, 240, 240);
            pdf.rect(10, contentY, W - 20, contentH, 'F');
            pdf.setFontSize(11);
            pdf.setTextColor(100, 100, 100);
            pdf.text(slide.content.description ?? slide.title, W / 2, contentY + contentH / 2, { align: 'center' });
          }
        }

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
  },
}));

/** Apply the persisted theme to <html> on app start. */
export function initUITheme(): void {
  applyTheme(useUIStore.getState().theme);
}

// ── Convenience hooks (former context APIs) ───────────────────────────────────
// Select fields individually — never return a fresh composite object from one
// selector (that defeats zustand's snapshot caching).

export function useTheme(): { theme: Theme; toggleTheme: () => void } {
  const theme = useUIStore((s) => s.theme);
  const toggleTheme = useUIStore((s) => s.toggleTheme);
  return { theme, toggleTheme };
}

export function useExpertMode(): { expertMode: boolean; setExpertMode: (v: boolean) => void } {
  const expertMode = useUIStore((s) => s.expertMode);
  const setExpertMode = useUIStore((s) => s.setExpertMode);
  return { expertMode, setExpertMode };
}

export function useTeacherMode() {
  const teacherMode = useUIStore((s) => s.teacherMode);
  const setTeacherMode = useUIStore((s) => s.setTeacherMode);
  const slides = useUIStore((s) => s.slides);
  const addSlide = useUIStore((s) => s.addSlide);
  const removeSlide = useUIStore((s) => s.removeSlide);
  const reorderSlides = useUIStore((s) => s.reorderSlides);
  const updateSlideNotes = useUIStore((s) => s.updateSlideNotes);
  const updateSlideTitle = useUIStore((s) => s.updateSlideTitle);
  const captureScreen = useUIStore((s) => s.captureScreen);
  const exportPresentation = useUIStore((s) => s.exportPresentation);
  const capturing = useUIStore((s) => s.capturing);
  return {
    teacherMode, setTeacherMode, slides, addSlide, removeSlide, reorderSlides,
    updateSlideNotes, updateSlideTitle, captureScreen, exportPresentation, capturing,
  };
}
