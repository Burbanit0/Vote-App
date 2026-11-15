import React from 'react';
import { useElectionStore, type ScenarioMeta } from '../stores/useElectionStore';
import type { ElectionConfig, PlaygroundState } from '../lib/electionTypes';
import type { Lens, MomentId } from '../lib/journeyTypes';
import type { Rule } from '../lib/playgroundVoting';
import { readScenarioLink, type ScenarioLink } from '../lib/scenarioLink';
import { track } from '../lib/analytics';

/** What the visitor had before a link replaced it: what "Back to my scenario" puts back. */
interface Previous {
  config: ElectionConfig;
  scenarioMeta: ScenarioMeta | null;
  playground: PlaygroundState;
  rule: Rule;
  moment: MomentId;
  lens: Lens;
}

/** A lens to show in `moment`, over that moment's default one. */
export interface PendingLens {
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
  /** Read by the controller when the moment changes, to show a link's lens instead of the default. */
  pendingLens: React.MutableRefObject<PendingLens | null>;
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
 * `sharedLink` is null until a link has been opened, then what the notice needs; `opened` counts
 * the links opened, for what must end when one is (a story).
 */
export function useScenarioLink(options: Options) {
  const [previous, setPrevious] = React.useState<Previous | null>(null);
  const [opened, setOpened] = React.useState(0);

  // What the listener below reads, so that it is set up once and not at every click of the
  // journey: the state it needs is the latest, not the one of the render that added it.
  const latest = React.useRef(options);
  React.useLayoutEffect(() => {
    latest.current = options;
  });

  // `description` and `phenomenon` are optional, and a patch that lacks them leaves the old
  // ones in place: name them, so a scenario without them does not inherit another's.
  const put = React.useCallback((config: ElectionConfig, playground: PlaygroundState) => {
    latest.current.setConfig({ description: undefined, phenomenon: undefined, ...config });
    latest.current.setPlayground(playground);
  }, []);

  // The lens comes with the moment: the controller shows it when the moment changes, and it is set
  // here too for a moment that does not (the one already open).
  const go = React.useCallback((moment: MomentId, lens: Lens) => {
    const { setActiveMoment, setLens, pendingLens } = latest.current;
    pendingLens.current = { moment, lens };
    setActiveMoment(moment);
    setLens(lens);
  }, []);

  React.useLayoutEffect(() => {
    const apply = () => {
      const link: ScenarioLink | null = readScenarioLink(window.location.hash);
      if (!link) return;
      window.history.replaceState(
        window.history.state,
        '',
        window.location.pathname + window.location.search
      );
      track('scenario_link_opened');
      const { config, playground, scenarioMeta } = useElectionStore.getState();
      const { leaderRule, activeMoment, lens, setLeaderRule } = latest.current;
      // The first link keeps what the visitor had; a second one must not replace it with the first.
      setPrevious(
        (p) =>
          p ?? { config, scenarioMeta, playground, rule: leaderRule, moment: activeMoment, lens }
      );
      put(link.config, link.playground);
      setLeaderRule(link.rule);
      go(link.moment, link.lens);
      setOpened((n) => n + 1);
    };
    apply();
    window.addEventListener('hashchange', apply);
    return () => window.removeEventListener('hashchange', apply);
  }, [put, go]);

  const sharedLink = React.useMemo(
    () =>
      previous
        ? {
            restore: () => {
              put(previous.config, previous.playground);
              // `setConfig` forgets the named scenario (its name and what it shows): put it back.
              useElectionStore.setState({ scenarioMeta: previous.scenarioMeta });
              latest.current.setLeaderRule(previous.rule);
              go(previous.moment, previous.lens);
              setPrevious(null);
            },
            dismiss: () => setPrevious(null),
          }
        : null,
    [previous, put, go]
  );

  return { sharedLink, opened };
}
