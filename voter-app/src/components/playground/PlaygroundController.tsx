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
  const [lens, setLens] = React.useState<Lens>('winner');
  React.useEffect(() => {
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
    const firstPrefCounts = new Array(m).fill(0);
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
    cands: leaderCandidates.map((c) => [c.name, c.x, c.y, c.z]),
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
  }, [shakeKey]);

  // ── Scorecard + values lens (P5) ──────────────────────────────────────────
  const [leaderSc, setLeaderSc] = React.useState<LeaderScorecard | null>(null);
  const leaderScKey = JSON.stringify({
    on: mode === 'leader',
    cands: leaderCandidates.map((c) => [c.name, c.x, c.y, c.z]),
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
  }, [parlScKey]);

  const [leaderWeights, setLeaderWeights] = React.useState(() => defaultWeights(LEADER_AXES_KEYS));
  const [parlWeights, setParlWeights] = React.useState(() => defaultWeights(PARLIAMENT_AXES_KEYS));

  // FA-2 — the Lijphart identity dial drives correlated weights; any granular
  // slider touch switches to manual mode (the stated escape hatch).
  const [lensMode, setLensMode] = React.useState<'dial' | 'granular'>('dial');
  const [dial, setDial] = React.useState(0.5);
  const manualWeights = mode === 'leader' ? leaderWeights : parlWeights;
  const effectiveWeights = lensMode === 'dial' ? dialWeights(dial, mode) : manualWeights;

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
  const currentAxes: ScorecardAxis[] = axisMeta.map(({ key, label, hint }) => ({
    key,
    label,
    hint,
    band:
      mode === 'leader'
        ? (leaderSc?.[leaderRule]?.[key] ?? null)
        : (parlSc?.structures?.[assembly.structure]?.[key] ?? null),
  }));
  const lensItems: LensItem[] =
    mode === 'leader'
      ? leaderSc
        ? LEADER_RULES.filter((r) => enabledRules.has(r)).map((r) => ({ id: r, axes: leaderSc[r] }))
        : []
      : parlSc
        ? Object.keys(structureLabels).map((s) => ({ id: s, axes: parlSc.structures[s] }))
        : [];

  return {
    // stores
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
    // diagnostics
    result,
    loading,
    assemblyResult,
    assemblyLoading,
    // journey
    activeMoment,
    setActiveMoment,
    // instrument
    dims,
    leaderRule,
    setLeaderRule,
    enabledRules,
    setEnabledRules,
    lens,
    setLens,
    youPos,
    setYouPos,
    showYou,
    electorate,
    composed,
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
    pinToPlayground,
    // shake
    shakeOn,
    setShakeOn,
    shake,
    // scorecards
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
    lensItems,
  };
}

export type PlaygroundCtx = ReturnType<typeof useController>;

const Ctx = createContext<PlaygroundCtx | null>(null);

export const PlaygroundProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const value = useController();
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
};

export function usePlaygroundCtx(): PlaygroundCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error('usePlaygroundCtx must be used within a PlaygroundProvider');
  return c;
}
