/**
 * The count's geometry on the page: a screen of the count (its pinned stage's height)
 * and the scroll position where the stage pins, which is the track's top less the
 * navbar the stage sticks under. CountStory plays from there; HandoverMap lands there.
 */
export function countPin(track: Element, stage: Element): { H: number; top: number } {
  const H = stage.clientHeight || window.innerHeight;
  return { H, top: track.getBoundingClientRect().top + window.scrollY - (window.innerHeight - H) };
}
