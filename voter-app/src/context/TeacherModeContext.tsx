/**
 * TeacherModeContext — compatibility shim over useUIStore (Phase 5.4).
 * The teacher-presentation state (slides, capture, PDF export) now lives in
 * stores/useUIStore. This keeps useTeacherMode()/TeacherModeProvider + the
 * `Slide` type working until 5.5 deletes the shim.
 */
import React, { useEffect } from 'react';
import { useUIStore, type Slide } from '../stores/useUIStore';

export type { Slide };

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

export function useTeacherMode(): TeacherModeContextValue {
  // Select each field individually — returning a fresh composite object from a
  // single selector would defeat zustand's snapshot caching.
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

export const TeacherModeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const hydrate = useUIStore((s) => s.hydrate);
  useEffect(() => { hydrate(); }, [hydrate]);
  return <>{children}</>;
};
