// curiosityQuestions — an entry by CURIOSITY, not by mechanism. A newcomer rarely
// searches for "the spoiler effect"; they wonder "how can a no-hope candidate make
// my favourite lose?". Each question is a plain wondering that routes to the story
// which answers it (reusing the existing STORIES + /playground?story= deep-link).
//
// Data only: `id` names the i18n key (curiosity.q.<id>) and `story` is the target
// story. A test validates every story id against the real STORIES registry.

export interface CuriosityQuestion {
  /** i18n key suffix under playground `curiosity.q.<id>`. */
  id: string;
  /** Target story id (must exist in STORIES). */
  story: string;
}

export const CURIOSITY_QUESTIONS: CuriosityQuestion[] = [
  { id: 'wasted', story: 'utile' },
  { id: 'spoiler', story: 'spoiler' },
  { id: 'centre', story: 'squeeze' },
  { id: 'method', story: 'paradox' },
  { id: 'best', story: 'valence' },
  { id: 'small', story: 'seuil' },
];
