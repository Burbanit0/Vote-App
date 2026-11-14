import React from 'react';
import { useElectionStore } from '../stores/useElectionStore';
import type { ElectionConfig, PlaygroundState } from '../lib/electionTypes';
import type { Lens, MomentId } from '../lib/journeyTypes';
import type { Rule } from '../lib/playgroundVoting';
import { readScenarioLink, type ScenarioLink } from '../lib/scenarioLink';
import { track } from '../lib/analytics';

/** What the visitor had before a link replaced it: what "Back to my scenario" puts back. */
interface Previous {
  config: ElectionConfig;
  playground: PlaygroundState;
  rule: Rule;
  moment: MomentId;
  lens: Lens;
}

interface Options {
  activeMoment: MomentId;
  leaderRule: Rule;
  lens: Lens;
  setActiveMoment: (m: MomentId) => void;
  setLeaderRule: (r: Rule) => void;
  setLens: (l: Lens) => void;
  /** A lens to apply when the moment next changes, over that moment's default one. */
  pendingLens: React.MutableRefObject<Lens | null>;
  setConfig: (patch: Partial<ElectionConfig>) => void;
  setPlayground: (patch: Partial<PlaygroundState>) => void;
}

/**
 * Opens a scenario link (`#s=...`, see lib/scenarioLink.ts): on mount, and whenever the hash
 * changes, as when a link is pasted into the address bar of the tab already open. The link
 * replaces the visitor's own scenario, which is saved as they edit, so what they had is kept
 * here for "Back to my scenario" (`restore`), and the hash is removed from the address so a
 * reload does not apply the link over what they do next.
 *
 * Returns null until a link has been opened, then what the notice needs.
 */
export function useScenarioLink({
  activeMoment,
  leaderRule,
  lens,
  setActiveMoment,
  setLeaderRule,
  setLens,
  pendingLens,
  setConfig,
  setPlayground,
}: Options) {
  const [previous, setPrevious] = React.useState<Previous | null>(null);

  // `description` and `phenomenon` are optional, and a patch that lacks them leaves the old
  // ones in place: name them, so a scenario without them does not inherit another's.
  const put = React.useCallback(
    (config: ElectionConfig, playground: PlaygroundState) => {
      setConfig({ description: undefined, phenomenon: undefined, ...config });
      setPlayground(playground);
    },
    [setConfig, setPlayground]
  );

  const go = React.useCallback(
    (to: MomentId, toLens: Lens) => {
      if (to === activeMoment) {
        setLens(toLens);
      } else {
        pendingLens.current = toLens;
        setActiveMoment(to);
      }
    },
    [activeMoment, setLens, setActiveMoment, pendingLens]
  );

  const open = React.useCallback(
    (link: ScenarioLink) => {
      const { config, playground } = useElectionStore.getState();
      // The first link keeps what the visitor had; a second one must not replace it with the first.
      setPrevious((p) => p ?? { config, playground, rule: leaderRule, moment: activeMoment, lens });
      put(link.config, link.playground);
      setLeaderRule(link.rule);
      go(link.moment, link.lens);
    },
    [leaderRule, activeMoment, lens, put, setLeaderRule, go]
  );

  React.useLayoutEffect(() => {
    const apply = () => {
      const link = readScenarioLink(window.location.hash);
      if (!link) return;
      window.history.replaceState(
        window.history.state,
        '',
        window.location.pathname + window.location.search
      );
      track('scenario_link_opened');
      open(link);
    };
    apply();
    window.addEventListener('hashchange', apply);
    return () => window.removeEventListener('hashchange', apply);
  }, [open]);

  return React.useMemo(
    () =>
      previous
        ? {
            restore: () => {
              put(previous.config, previous.playground);
              setLeaderRule(previous.rule);
              go(previous.moment, previous.lens);
              setPrevious(null);
            },
            dismiss: () => setPrevious(null),
          }
        : null,
    [previous, put, setLeaderRule, go]
  );
}
