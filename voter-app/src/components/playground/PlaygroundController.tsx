import React, { createContext, useContext } from 'react';
import { useElection, usePlayground } from '../../stores/useElectionStore';
import { useProfileDiagnostics, useAssembly } from '../../hooks/usePlaygroundData';
import { type Lens } from './LeaderCanvas';
import { type MomentId } from './MomentRail';
import {
  sampleVoters,
  applyTurnout,
  applyBlankVote,
  computeRanks,
  computeScores,
  ruleWinnerFromRanks,
  type Rule,
  type Pt,
} from '../../lib/playgroundVoting';
import { blankVerdict, type BlankVerdict } from '../../lib/blankVote';
import { shakeWinRates, type ShakeResult } from '../../lib/playgroundDynamics';
import { runAssemblyScorecard, type AssemblyScorecardResult } from '../../services/assemblyApi';
import { type ScorecardAxis } from './Scorecard';
import {
  leaderScorecard,
  consensusIndex,
  dialWeights,
  manipulationProbe,
  LEADER_AXES_KEYS,
  LEADER_RULES,
  type LeaderScorecard,
  type LensItem,
} from '../../lib/scorecard';
import { strategicVote, type StrategicOutcome } from '../../lib/playgroundSincerity';
import { composeElectorate, COMMUNITY_PALETTE } from '../../lib/playgroundElectorate';
import { track } from '../../lib/analytics';
import { PARLIAMENT_AXES_KEYS, defaultWeights } from '../../lib/playgroundMeta';
import { useVotingLabels } from '../../hooks/useVotingLabels';

// PlaygroundController — the single source of truth for the instrument. All state,
// derivations and effects live here and are exposed through one context, so the
// moment panels, the instrument and the readouts are thin consumers rather than a
// prop-drilling chain. The page is then a pure layout shell.

function useController() {
  const { config, setConfig } = useElection();
  const { playground, setMode, setPlayground, setPlaygroundDeep, applyPreset, presets } =
    usePlayground();
  const { mode, space, behavior, prefSource, prefParams, assembly, turnout, blank } = playground;
  const pointWord = mode === 'leader' ? 'candidats' : 'partis';
  const { result, loading } = useProfileDiagnostics(config, playground);
  const { assembly: assemblyResult, loading: assemblyLoading } = useAssembly(
    config,
    playground,
    mode === 'parliament'
  );
  const { leaderAxisMeta, parliamentAxisMeta, structureLabels } = useVotingLabels();

  // The active "moment" — the station on the instrument's journey. Drives the
  // left control panel and the instrument's lens; the others stay one click away.
  const [activeMoment, _setActiveMoment] = React.useState<MomentId>('electorate');
  const setActiveMoment = React.useCallback((m: MomentId) => {
    track('moment_changed', { moment: m });
    _setActiveMoment(m);
  }, []);

  const dims = space.dims;
  const [leaderRule, _setLeaderRule] = React.useState<Rule>('plurality');
  // Every rule selector in the app (Méthode moment, Lab strip, campaign) routes
  // through this setter, so one track() covers them all.
  const setLeaderRule = React.useCallback((r: Rule) => {
    track('rule_changed', { rule: r });
    _setLeaderRule(r);
  }, []);
  const [enabledRules, setEnabledRules] = React.useState<Set<Rule>>(() => new Set(LEADER_RULES));
  // Central-map lens: the moment sets a sensible default (Méthode → critères,
  // Stratégie → manipulation, sinon vainqueur). The user can still override it on
  // the instrument within the current moment.
  //
  // useLayoutEffect, so the moment's default lens commits with the moment itself
  // and no frame paints the previous lens. It was once blamed for
  // playground-method.spec.ts's "the four lenses..." Firefox flake (a click
  // overwritten by this effect firing late), but a moment click is a discrete
  // event whose effects React flushes synchronously. The click was lost instead,
  // to WinnerRobustness's strip arriving above the lens switch mid-click; that
  // component now holds its place while it computes.
  const [lens, setLens] = React.useState<Lens>('winner');
  React.useLayoutEffect(() => {
    setLens(
      activeMoment === 'method'
        ? 'criteria'
        : activeMoment === 'strategy'
          ? 'manipulation'
          : 'winner'
    );
  }, [activeMoment]);

  // Phase 0 perf: warm the heavy Recharts vendor chunk after first paint, so the
  // first behaviour/analysis panel that uses it opens without a cold parse.
  React.useEffect(() => {
    let idle: number | undefined;
    let timer: number | undefined;
    const warm = () => {
      import('recharts').catch(() => {});
    };
    if (typeof window.requestIdleCallback === 'function') {
      idle = window.requestIdleCallback(warm);
    } else {
      timer = window.setTimeout(warm, 1500);
    }
    return () => {
      if (idle !== undefined && typeof window.cancelIdleCallback === 'function')
        window.cancelIdleCallback(idle);
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, []);

  // "You" — the sincere-vote voter, draggable on the map. Shown while the Stratégie
  // moment is active (the sincerity module lives there).
  const [youPos, setYouPos] = React.useState<Pt>({ x: -0.5, y: 0, z: 0 });
  const showYou = mode === 'leader' && activeMoment === 'strategy';
  // Stable identity across renders (unlike the inline arrow InstrumentPanel used
  // to pass as onMoveYou) — required for LeaderCanvas's React.memo to actually
  // bail when nothing it reads changed; see moveCandidate/pinToPlayground below
  // for the same pattern, already established before this one.
  const moveYou = React.useCallback(
    (x: number, y: number) => setYouPos((p) => ({ ...p, x, y })),
    []
  );

  // The composable electorate (engine): when 'composed', a community mixture
  // replaces the single ideology Gaussian and tags each voter with its bloc.
  const electorate = playground.electorate;
  const composed = electorate.mode === 'composed';
  const electorateSampler = React.useMemo(
    () =>
      composed
        ? {
            communities: electorate.communities,
            correlation: electorate.correlation,
            noise: electorate.noise,
          }
        : null,
    [composed, electorate.communities, electorate.correlation, electorate.noise]
  );
  const voters = React.useMemo(() => {
    if (electorateSampler) {
      const { voters: vs, community } = composeElectorate(
        electorateSampler.communities,
        electorateSampler.correlation,
        config.num_voters,
        config.seed,
        dims,
        electorateSampler.noise
      );
      return vs.map((v, i) => ({ ...v, _community: community[i] }));
    }
    return sampleVoters(config.num_voters, config.seed, config.ideology, dims);
  }, [electorateSampler, config.num_voters, config.seed, config.ideology, dims]);

  const moveCandidate = React.useCallback(
    (index: number, x: number, y: number, z?: number) => {
      setConfig({
        candidates: config.candidates.map((c, i) =>
          i === index ? { ...c, x, y, ...(z !== undefined ? { z } : {}) } : c
        ),
      });
    },
    [config.candidates, setConfig]
  );

  // "Pin this drifted instant back as the new baseline electorate" — the one
  // explicit write-back from the campaign moment into the shared snapshot.
  const pinToPlayground = React.useCallback(
    (pinned: { name: string; x: number; y: number; z?: number }[]) =>
      setConfig({
        candidates: pinned.map((c) => ({ name: c.name, x: c.x, y: c.y, z: c.z })),
      }),
    [setConfig]
  );

  // Project candidates onto the active dimension count so the math, the map and
  // the re-rolls all agree (1-D zeroes y,z; 2-D zeroes z; 3-D keeps all).
  const valenceOn = space.valenceEnabled;
  const leaderCandidates = React.useMemo(
    () =>
      config.candidates.map((c) => ({
        ...c,
        y: dims >= 2 ? c.y : 0,
        z: dims >= 3 ? (c.z ?? 0) : 0,
        // Stokes valence only bites when enabled; otherwise the model is purely
        // positional (keeps every existing readout identical when off).
        valence: valenceOn ? (c.valence ?? 0) : 0,
      })),
    [config.candidates, dims, valenceOn]
  );
  const turnoutResult = React.useMemo(
    () => applyTurnout(voters, leaderCandidates, turnout.model, turnout.intensity),
    [voters, leaderCandidates, turnout.model, turnout.intensity]
  );
  const votingVoters = turnoutResult.voters;

  // Blank vote (leader mode): voters who show up but reject every candidate.
  // A layer ON TOP of turnout (turnout's no-shows never reach this check), so
  // it's additive and off by default — every other derivation below keeps
  // reading `votingVoters` unchanged; only the live winner + its verdict read
  // the post-blank set.
  const blankSplit = React.useMemo(
    () => applyBlankVote(votingVoters, leaderCandidates, blank.enabled, blank.intensity),
    [votingVoters, leaderCandidates, blank.enabled, blank.intensity]
  );
  const expressedVoters = blank.enabled ? blankSplit.expressed : votingVoters;
  const blankVerdictLive: BlankVerdict | null = React.useMemo(() => {
    if (mode !== 'leader' || !blank.enabled || blankSplit.blankCount === 0) return null;
    const m = leaderCandidates.length;
    const ranks = computeRanks(expressedVoters, leaderCandidates);
    const scores = computeScores(expressedVoters, leaderCandidates);
    const winnerIdx = ruleWinnerFromRanks(ranks, m, leaderRule, scores);
    const firstPrefCounts: number[] = new Array(m).fill(0);
    for (const r of ranks) firstPrefCounts[r[0]] += 1;
    const total = expressedVoters.length + blankSplit.blankCount;
    const shares = firstPrefCounts.map((c) => c / total);
    return blankVerdict(shares, blankSplit.blankCount / total, blank.lens, winnerIdx);
  }, [
    mode,
    blank.enabled,
    blank.lens,
    blankSplit.blankCount,
    expressedVoters,
    leaderCandidates,
    leaderRule,
  ]);

  // Re-draw the SAME electorate composition on an arbitrary seed (post-turnout),
  // so the verdict's robustness can be measured across resamples.
  const sampleAtSeed = React.useCallback(
    (seed: number): Pt[] => {
      const raw = electorateSampler
        ? composeElectorate(
            electorateSampler.communities,
            electorateSampler.correlation,
            config.num_voters,
            seed,
            dims,
            electorateSampler.noise
          ).voters
        : sampleVoters(config.num_voters, seed, config.ideology, dims);
      return applyTurnout(raw, leaderCandidates, turnout.model, turnout.intensity).voters;
    },
    [
      electorateSampler,
      config.num_voters,
      config.ideology,
      dims,
      leaderCandidates,
      turnout.model,
      turnout.intensity,
    ]
  );
  const voterColors = React.useMemo(
    () =>
      composed
        ? votingVoters.map(
            (v) =>
              COMMUNITY_PALETTE[
                ((v as { _community?: number })._community ?? 0) % COMMUNITY_PALETTE.length
              ]
          )
        : undefined,
    [composed, votingVoters]
  );

  // "Shake the assumptions": re-roll the electorate, win-rate per candidate.
  const [shakeOn, setShakeOn] = React.useState(false);
  const [shake, setShake] = React.useState<ShakeResult | null>(null);
  const shakeKey = JSON.stringify({
    on: shakeOn,
    rule: leaderRule,
    cands: leaderCandidates.map((c) => [c.name, c.x, c.y, c.z, c.valence]),
    n: config.num_voters,
    seed: config.seed,
    ideology: config.ideology,
    dims,
    turnout,
    electorate: electorateSampler,
  });
  React.useEffect(() => {
    if (!shakeOn) {
      setShake(null);
      return;
    }
    const t = setTimeout(() => {
      setShake(
        shakeWinRates(
          leaderCandidates,
          leaderRule,
          Math.min(config.num_voters, 300),
          config.seed,
          config.ideology,
          60,
          dims,
          turnout,
          electorateSampler
        )
      );
    }, 200);
    return () => clearTimeout(t);
    // shakeKey is a deliberate serialized digest of every value this effect
    // actually reads (including c.valence — omitted until a /code-review
    // ultra pass caught it: valence-only edits were silently not
    // re-triggering a shake), so the effect re-fires on VALUE change only,
    // not on every new object identity (turnout/electorateSampler are
    // recreated each render). Depending on the raw fields instead would
    // defeat that — react-hooks/exhaustive-deps flags this as informational
    // only (see eslint.config.js), not silenced.
  }, [shakeKey]);

  // ── Scorecard + values lens (P5) ──────────────────────────────────────────
  const [leaderSc, setLeaderSc] = React.useState<LeaderScorecard | null>(null);
  const leaderScKey = JSON.stringify({
    on: mode === 'leader',
    cands: leaderCandidates.map((c) => [c.name, c.x, c.y, c.z, c.valence]),
    n: config.num_voters,
    seed: config.seed,
    ideology: config.ideology,
    dims,
    turnout,
    electorate: electorateSampler,
  });
  React.useEffect(() => {
    if (mode !== 'leader') return;
    const t = setTimeout(() => {
      setLeaderSc(
        leaderScorecard(
          leaderCandidates,
          Math.min(config.num_voters, 200),
          config.seed,
          config.ideology,
          20,
          dims,
          turnout,
          electorateSampler
        )
      );
    }, 250);
    return () => clearTimeout(t);
    // leaderScKey is a deliberate serialized digest (incl. c.valence) — see
    // shakeKey above.
  }, [leaderScKey]);

  const [parlSc, setParlSc] = React.useState<AssemblyScorecardResult | null>(null);
  const parlScKey = JSON.stringify({
    on: mode === 'parliament',
    parties: config.candidates.map((c) => [c.name, c.x, c.y]),
    n: config.num_voters,
    seed: config.seed,
    ideology: config.ideology,
    seats: assembly.seats,
    threshold: assembly.threshold,
    appt: assembly.apportionment,
    des: assembly.strategic_desertion,
    turnout,
    electorate: electorateSampler,
  });
  React.useEffect(() => {
    if (mode !== 'parliament') return;
    let alive = true;
    const t = setTimeout(() => {
      runAssemblyScorecard(config, playground)
        .then((r) => {
          if (alive) setParlSc(r);
        })
        .catch(() => {
          if (alive) setParlSc(null);
        });
    }, 350);
    return () => {
      alive = false;
      clearTimeout(t);
    };
    // parlScKey is a deliberate serialized digest of everything
    // runAssemblyScorecard's payload actually sends (turnout + composed-
    // electorate settings included — both were missing until a
    // /code-review ultra pass caught it: changing the abstention model or
    // electorate composition in Assemblée mode silently didn't refresh the
    // Bilan scorecard). See shakeKey above for why a digest, not raw deps.
  }, [parlScKey]);

  const [leaderWeights, setLeaderWeights] = React.useState(() => defaultWeights(LEADER_AXES_KEYS));
  const [parlWeights, setParlWeights] = React.useState(() => defaultWeights(PARLIAMENT_AXES_KEYS));

  // FA-2 — the Lijphart identity dial drives correlated weights; any granular
  // slider touch switches to manual mode (the stated escape hatch).
  const [lensMode, setLensMode] = React.useState<'dial' | 'granular'>('dial');
  const [dial, setDial] = React.useState(0.5);
  const manualWeights = mode === 'leader' ? leaderWeights : parlWeights;
  const effectiveWeights = React.useMemo(
    () => (lensMode === 'dial' ? dialWeights(dial, mode) : manualWeights),
    [lensMode, dial, mode, manualWeights]
  );

  const democracyEntries = React.useMemo(
    () =>
      parlSc
        ? Object.keys(structureLabels).map((s) => ({
            structure: s,
            label: structureLabels[s].split(' ')[0],
            index: consensusIndex(parlSc.structures[s]),
          }))
        : [],
    [parlSc, structureLabels]
  );

  // FC-1 — manipulation hardness: the empirical compromise probe on THIS
  // electorate for the selected rule, plus the plurality-vs-IRV worked example.
  const manipDetail = React.useMemo(() => {
    if (mode !== 'leader') return null;
    return {
      probe: manipulationProbe(votingVoters, leaderCandidates, leaderRule),
      easy: manipulationProbe(votingVoters, leaderCandidates, 'plurality'),
      hard: manipulationProbe(votingVoters, leaderCandidates, 'irv'),
    };
  }, [mode, votingVoters, leaderCandidates, leaderRule]);

  // FC-2 — strategic outcome: does tactical voting flip the winner on THIS map?
  // O(n²) probe, so debounced off the drag frame (settles ~200 ms after a move).
  const [strategicOutcome, setStrategicOutcome] = React.useState<StrategicOutcome | null>(null);
  React.useEffect(() => {
    if (mode !== 'leader') {
      setStrategicOutcome(null);
      return;
    }
    let alive = true;
    const id = setTimeout(() => {
      const out = strategicVote(votingVoters, leaderCandidates, leaderRule, behavior, {
        tactic: playground.stratTactic,
        blocShare: playground.stratShare,
      });
      if (alive) setStrategicOutcome(out);
    }, 200);
    return () => {
      alive = false;
      clearTimeout(id);
    };
  }, [
    mode,
    votingVoters,
    leaderCandidates,
    leaderRule,
    behavior,
    playground.stratTactic,
    playground.stratShare,
  ]);

  const axisMeta = mode === 'leader' ? leaderAxisMeta : parliamentAxisMeta;
  const currentAxes: ScorecardAxis[] = React.useMemo(
    () =>
      axisMeta.map(({ key, label, hint }) => ({
        key,
        label,
        hint,
        band:
          mode === 'leader'
            ? (leaderSc?.[leaderRule]?.[key] ?? null)
            : (parlSc?.structures?.[assembly.structure]?.[key] ?? null),
      })),
    [axisMeta, mode, leaderSc, leaderRule, parlSc, assembly.structure]
  );
  const lensItems: LensItem[] = React.useMemo(
    () =>
      mode === 'leader'
        ? leaderSc
          ? LEADER_RULES.filter((r) => enabledRules.has(r)).map((r) => ({
              id: r,
              axes: leaderSc[r],
            }))
          : []
        : parlSc
          ? Object.keys(structureLabels).map((s) => ({ id: s, axes: parlSc.structures[s] }))
          : [],
    [mode, leaderSc, enabledRules, parlSc, structureLabels]
  );

  // Split off from the main context on purpose: MethodMoment's checkbox
  // toggles change only these three values, but the main context bundles
  // ~70 fields behind one object, so every usePlaygroundCtx() consumer
  // (InstrumentPanel, LeaderCanvas, every moment panel — see
  // PlaygroundController.render.test.tsx) re-rendered on every toggle. That
  // re-render storm was cheap enough to be invisible normally, but was root-
  // caused as the reason a 28-checkbox uncheck loop intermittently hung past
  // WebKit's actionability timeout under real CI-runner CPU contention
  // (Chromium/Firefox unaffected by the identical contention) -- see the
  // commit that introduced this split for the full reproduction. A separate,
  // smaller context for just this slice means a checkbox toggle only
  // re-renders its own three real consumers (MethodMoment, ValuesLabPanel,
  // BilanMoment) on every engine, not just under load.
  //
  // This split closed that one reproduced case first; the general class
  // (every other field bundled in one blob) is now addressed by the four
  // concern-split contexts below, which extend the same pattern to the rest.
  const methodSelection = React.useMemo(
    () => ({ enabledRules, setEnabledRules, lensItems }),
    [enabledRules, setEnabledRules, lensItems]
  );

  // ── Four contexts by concern (PLAN_SURFACE_EXTERIEURE.md §2.J) ────────────
  // methodSelection above proved the pattern on one slice: a component that
  // only reads that context is NOT re-rendered by a change elsewhere (see
  // PlaygroundController.render.test.tsx). These four extend it to the rest
  // of what used to be one ~67-field `main` blob, split by how the data
  // actually behaves:
  //   - storeCtx: the raw config/playground bindings and anything that is a
  //     pure read of them (dims, electorate, composed). Coarse-grained --
  //     almost every consumer reads `mode` at least. CORRECTION (perf audit,
  //     see useElectionStore.tsx's debounced-persistence comment): this used
  //     to claim `config` changes only on an explicit settings edit, never on
  //     a drag/slider frame -- verified false. moveCandidate (below) writes
  //     into `config` via setConfig on EVERY drag frame/slider tick, same as
  //     any other settings edit, so storeCtx (and every plain
  //     usePlaygroundCtx() consumer: ModeSwitch, StoryPlayer, GuidedFooter,
  //     the active moment panel) re-renders on every one of those too -- this
  //     slice does NOT get the drag-frame isolation instrumentCtx gives a
  //     narrowly-scoped consumer. What the persistence fix removed was only
  //     the synchronous localStorage WRITE per frame, not the config update
  //     or the re-renders it causes; decoupling the live drag position from
  //     `config` entirely (so a drag doesn't touch storeCtx at all) was
  //     evaluated and deliberately deferred -- see the PR that introduced
  //     this correction for why.
  //   - journeyCtx: where the user is and what they're looking at -- the
  //     active moment, the rule under examination, the map lens (whose
  //     default is itself derived from the moment). Discrete clicks only.
  //   - instrumentCtx: the live spatial data -- voters, candidates, the
  //     drag/shake interactions. The HIGH-FREQUENCY one: every candidate
  //     drag frame recomputes it. Deliberately holds nothing a consumer
  //     would read without also needing that live data, so a consumer that
  //     only wants e.g. the current rule isn't dragged along by it.
  //   - scorecardCtx: async diagnostics + the Monte-Carlo scorecard/values
  //     dial. Recomputes on a debounce, not every frame, but still more
  //     often than storeCtx/journeyCtx.
  // `main`/usePlaygroundCtx() stays as a composed, backward-compatible view
  // over all four (see below) -- existing consumers and their tests keep
  // working unchanged; only the ones migrated to the narrower hooks
  // (storeCtx et al.) actually stop re-rendering on a slice they don't
  // read. Migrating every remaining consumer is future work, not required
  // to get the real isolation this item asked for.
  const storeCtx = React.useMemo(
    () => ({
      config,
      setConfig,
      playground,
      setMode,
      setPlayground,
      setPlaygroundDeep,
      applyPreset,
      presets,
      mode,
      space,
      behavior,
      prefSource,
      prefParams,
      assembly,
      turnout,
      blank,
      pointWord,
      // Pure reads of the store (space.dims, playground.electorate) -- change
      // only on a settings edit, never on a drag frame, so they live here
      // rather than in instrumentCtx even though the map consumes them.
      dims,
      electorate,
      composed,
      // A stable store write-back (depends only on setConfig), unlike
      // moveCandidate which changes identity on every drag -- see instrumentCtx.
      pinToPlayground,
    }),
    [
      config,
      setConfig,
      playground,
      setMode,
      setPlayground,
      setPlaygroundDeep,
      applyPreset,
      presets,
      mode,
      space,
      behavior,
      prefSource,
      prefParams,
      assembly,
      turnout,
      blank,
      pointWord,
      dims,
      electorate,
      composed,
      pinToPlayground,
    ]
  );

  const journeyCtx = React.useMemo(
    () => ({
      activeMoment,
      setActiveMoment,
      leaderRule,
      setLeaderRule,
      lens,
      setLens,
      showYou,
    }),
    [activeMoment, setActiveMoment, leaderRule, setLeaderRule, lens, setLens, showYou]
  );

  const instrumentCtx = React.useMemo(
    () => ({
      youPos,
      setYouPos,
      moveYou,
      voters,
      voterColors,
      leaderCandidates,
      votingVoters,
      expressedVoters,
      blankSplit,
      blankVerdictLive,
      sampleAtSeed,
      baseSeed: config.seed,
      moveCandidate,
      shakeOn,
      setShakeOn,
      shake,
    }),
    [
      youPos,
      setYouPos,
      moveYou,
      voters,
      voterColors,
      leaderCandidates,
      votingVoters,
      expressedVoters,
      blankSplit,
      blankVerdictLive,
      sampleAtSeed,
      config.seed,
      moveCandidate,
      shakeOn,
      setShakeOn,
      shake,
    ]
  );

  const scorecardCtx = React.useMemo(
    () => ({
      result,
      loading,
      assemblyResult,
      assemblyLoading,
      leaderSc,
      parlSc,
      lensMode,
      setLensMode,
      dial,
      setDial,
      effectiveWeights,
      setLeaderWeights,
      setParlWeights,
      democracyEntries,
      manipDetail,
      strategicOutcome,
      axisMeta,
      currentAxes,
    }),
    [
      result,
      loading,
      assemblyResult,
      assemblyLoading,
      leaderSc,
      parlSc,
      lensMode,
      setLensMode,
      dial,
      setDial,
      effectiveWeights,
      setLeaderWeights,
      setParlWeights,
      democracyEntries,
      manipDetail,
      strategicOutcome,
      axisMeta,
      currentAxes,
    ]
  );

  // Composed, backward-compatible view over the four contexts above. Each of
  // the four is independently memoized, so this only recomputes when one of
  // THEM changes (an unrelated ancestor re-render still yields the same
  // object reference) -- the same contract `main` always had, see
  // PlaygroundController.render.test.tsx. It still does NOT reduce re-render
  // COUNTS for a usePlaygroundCtx() consumer when a dependency genuinely
  // changes: that's exactly what migrating a consumer to the narrower
  // hooks buys, which this composed view can't retroactively grant it.
  const main = React.useMemo(
    () => ({ ...storeCtx, ...journeyCtx, ...instrumentCtx, ...scorecardCtx }),
    [storeCtx, journeyCtx, instrumentCtx, scorecardCtx]
  );

  return { main, methodSelection, storeCtx, journeyCtx, instrumentCtx, scorecardCtx };
}

export type PlaygroundCtx = ReturnType<typeof useController>['main'];
export type MethodSelectionCtx = ReturnType<typeof useController>['methodSelection'];
export type StoreCtx = ReturnType<typeof useController>['storeCtx'];
export type JourneyCtx = ReturnType<typeof useController>['journeyCtx'];
export type InstrumentCtx = ReturnType<typeof useController>['instrumentCtx'];
export type ScorecardCtx = ReturnType<typeof useController>['scorecardCtx'];

const Ctx = createContext<PlaygroundCtx | null>(null);
const MethodSelectionContext = createContext<MethodSelectionCtx | null>(null);
const StoreContext = createContext<StoreCtx | null>(null);
const JourneyContext = createContext<JourneyCtx | null>(null);
const InstrumentContext = createContext<InstrumentCtx | null>(null);
const ScorecardContext = createContext<ScorecardCtx | null>(null);

export const PlaygroundProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { main, methodSelection, storeCtx, journeyCtx, instrumentCtx, scorecardCtx } =
    useController();
  return (
    <StoreContext.Provider value={storeCtx}>
      <JourneyContext.Provider value={journeyCtx}>
        <InstrumentContext.Provider value={instrumentCtx}>
          <ScorecardContext.Provider value={scorecardCtx}>
            <MethodSelectionContext.Provider value={methodSelection}>
              <Ctx.Provider value={main}>{children}</Ctx.Provider>
            </MethodSelectionContext.Provider>
          </ScorecardContext.Provider>
        </InstrumentContext.Provider>
      </JourneyContext.Provider>
    </StoreContext.Provider>
  );
};

/** The full, composed context -- convenient, but a consumer that reads it
 * re-renders on ANY of the four slices below changing. Prefer useStoreCtx() /
 * useJourneyCtx() / useInstrumentCtx() / useScorecardCtx() for a consumer
 * that only actually needs one slice. */
export function usePlaygroundCtx(): PlaygroundCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error('usePlaygroundCtx must be used within a PlaygroundProvider');
  return c;
}

// Split from usePlaygroundCtx() on purpose -- see the `methodSelection` memo
// in useController() above for why.
export function useMethodSelection(): MethodSelectionCtx {
  const c = useContext(MethodSelectionContext);
  if (!c) throw new Error('useMethodSelection must be used within a PlaygroundProvider');
  return c;
}

/** config/playground store bindings -- see the storeCtx memo above. */
export function useStoreCtx(): StoreCtx {
  const c = useContext(StoreContext);
  if (!c) throw new Error('useStoreCtx must be used within a PlaygroundProvider');
  return c;
}

/** Active moment, rule under examination, map lens -- see the journeyCtx memo
 * above. */
export function useJourneyCtx(): JourneyCtx {
  const c = useContext(JourneyContext);
  if (!c) throw new Error('useJourneyCtx must be used within a PlaygroundProvider');
  return c;
}

/** Live, drag-driven spatial data (voters, candidates, shake) -- see the
 * instrumentCtx memo above. */
export function useInstrumentCtx(): InstrumentCtx {
  const c = useContext(InstrumentContext);
  if (!c) throw new Error('useInstrumentCtx must be used within a PlaygroundProvider');
  return c;
}

/** Async diagnostics + the Monte-Carlo scorecard -- see the scorecardCtx
 * memo above. */
export function useScorecardCtx(): ScorecardCtx {
  const c = useContext(ScorecardContext);
  if (!c) throw new Error('useScorecardCtx must be used within a PlaygroundProvider');
  return c;
}
