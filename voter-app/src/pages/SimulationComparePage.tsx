import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Badge, Button, Card, Col, Container, Form, OverlayTrigger, Row, Spinner, Tab, Tabs, Tooltip } from 'react-bootstrap';
import { useToast } from '../components/shared/ToastNotification';
import SkeletonCard from '../components/shared/SkeletonCard';
import CondorcetMatrix from '../components/Simulation/CondorcetMatrix';
import ArrowCriteriaMatrix from '../components/Simulation/ArrowCriteriaMatrix';
import BandwagonAnalysis from '../components/Simulation/BandwagonAnalysis';
import MultiwinnerAnalysis from '../components/Simulation/MultiwinnerAnalysis';
import MonteCarloResults from '../components/Simulation/MonteCarloResults';
import WinnerMatrixTab from '../components/Simulation/WinnerMatrixTab';
import MetricsTab from '../components/Simulation/MetricsTab';
import StrategicImpactTab from '../components/Simulation/StrategicImpactTab';
import SensitivityTab from '../components/Simulation/SensitivityTab';
import RealElectionsTab from '../components/Simulation/RealElectionsTab';
import ScenarioModals from '../components/Simulation/ScenarioModals';
import ScenarioConfigRow from '../components/Simulation/ScenarioConfigRow';
import {
  CANDIDATE_PALETTE,
  METHOD_LABELS,
  ScenarioConfig,
  STRATEGIC_PERCENTAGES,
} from '../components/Simulation/simulationConstants';
import {
  ArrowCriteriaResult,
  CondorcetMatrixResult,
  ScenarioDetail,
  ScenarioSummary,
  SimulationCompareResult,
  StrategicImpactPoint,
} from '../types';
import {
  getArrowCriteria,
  getCondorcetMatrix,
  runComparisonSimulation,
  runStrategicImpactAnalysis,
} from '../services/simulationCompareApi';
import { deleteScenario, listScenarios, saveScenario } from '../services/scenariosApi';
import { buildShareURL, copyShareURL, decodeShareConfig, encodeShareConfig, readShareParam } from '../utils/shareUtils';
import { useExpertMode } from '../context/ExpertModeContext';
import { useMetaTags } from '../hooks/useMetaTags';
import { useTranslation } from 'react-i18next';
import { useMethodLabels } from '../components/Simulation/simulationConstants';

// ── Presentation mode ──────────────────────────────────────────────────────

const TAB_ORDER = [
  'winners', 'metrics', 'strategic', 'condorcet', 'arrow',
  'bandwagon', 'montecarlo', 'real-elections', 'multiwinner', 'sensitivity',
];

const BEGINNER_TABS = ['winners', 'metrics', 'strategic', 'real-elections', 'montecarlo'];

const BEGINNER_METHODS = ['plurality', 'borda', 'irv', 'schulze', 'approval'];


// ── Report generation ──────────────────────────────────────────────────────

function buildConclusion(
  results: SimulationCompareResult[],
  methodNames: string[],
): string {
  if (!results.length) return 'Aucun résultat disponible.';

  const avg = (vals: number[]) => vals.reduce((a, b) => a + b, 0) / (vals.length || 1);

  const regret = methodNames
    .map((m) => ({ m, v: avg(results.map((r) => r.methods[m]?.bayesian_regret ?? 0)) }))
    .filter((x) => x.v > 0)
    .sort((a, b) => a.v - b.v);

  const vuln = methodNames
    .map((m) => ({ m, v: avg(results.map((r) => r.methods[m]?.strategic_vulnerability ?? 0)) }))
    .filter((x) => x.v > 0)
    .sort((a, b) => b.v - a.v);

  const condorcet = methodNames
    .map((m) => ({ m, v: avg(results.map((r) => (r.methods[m]?.condorcet_consistent === true ? 1 : 0))) }))
    .sort((a, b) => b.v - a.v);

  const parts: string[] = [];

  if (regret.length) {
    const best = regret[0], worst = regret[regret.length - 1];
    parts.push(
      `Méthode la plus robuste (regret bayésien moyen le plus bas) : ` +
      `${METHOD_LABELS[best.m] ?? best.m} (${best.v.toFixed(4)}).`
    );
    if (worst.m !== best.m) {
      parts.push(
        `Méthode la moins robuste : ` +
        `${METHOD_LABELS[worst.m] ?? worst.m} (${worst.v.toFixed(4)}).`
      );
    }
  }

  if (vuln.length) {
    const v = vuln[0];
    parts.push(
      `Méthode la plus vulnérable au vote stratégique : ` +
      `${METHOD_LABELS[v.m] ?? v.m} (${(v.v * 100).toFixed(1)}% des électeurs peuvent l'influencer).`
    );
  }

  if (condorcet.length && condorcet[0].v > 0) {
    const c = condorcet[0];
    parts.push(
      `Méthode la plus cohérente avec le critère de Condorcet : ` +
      `${METHOD_LABELS[c.m] ?? c.m} (${(c.v * 100).toFixed(0)}% de cohérence).`
    );
  }

  return parts.join('\n\n');
}

function buildReportHTML(
  configA: ScenarioConfig,
  numSimulations: number,
  results: SimulationCompareResult[],
  methodNames: string[],
  conclusion: string,
  date: string,
  shareUrl: string = '',
): string {
  // Winners table rows
  const methodRows = methodNames.map((m) => {
    const winners = results.map((r) => r.methods[m]?.winner ?? '—');
    const mostCommon = winners.reduce<Record<string, number>>((acc, w) => ({ ...acc, [w]: (acc[w] ?? 0) + 1 }), {});
    const dominant = Object.entries(mostCommon).sort((a, b) => b[1] - a[1])[0];
    const avg = results.reduce((a, r) => a + (r.methods[m]?.bayesian_regret ?? 0), 0) / results.length;
    return `<tr><td>${METHOD_LABELS[m] ?? m}</td><td>${dominant?.[0] ?? '—'} (${dominant?.[1]}/${results.length})</td><td>${avg.toFixed(4)}</td></tr>`;
  }).join('');

  return `<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <title>Vote Lab — Rapport de simulation ${date}</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: 'Georgia', serif; margin: 0; padding: 2cm; color: #333; font-size: 11pt; }
    h1 { font-size: 20pt; color: #0d6efd; margin-bottom: 0.2cm; }
    h2 { font-size: 14pt; color: #444; border-bottom: 1px solid #dee2e6; padding-bottom: 4px; margin-top: 1cm; }
    .meta { color: #6c757d; font-size: 9pt; margin-bottom: 0.8cm; }
    table { width: 100%; border-collapse: collapse; font-size: 10pt; margin: 0.4cm 0; }
    th { background: #f8f9fa; text-align: left; padding: 6px 8px; border: 1px solid #dee2e6; }
    td { padding: 5px 8px; border: 1px solid #dee2e6; }
    tr:nth-child(even) { background: #f8f9fa; }
    .conclusion { background: #e8f4e8; border-left: 4px solid #198754; padding: 0.5cm; white-space: pre-line; font-size: 10pt; }
    .config-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.3cm; margin: 0.4cm 0; }
    .config-item { background: #f8f9fa; padding: 0.3cm; border-radius: 4px; }
    .config-item strong { display: block; font-size: 9pt; color: #6c757d; }
    @media print {
      body { padding: 1cm; }
      .no-print { display: none; }
      @page { margin: 1.5cm; size: A4; }
    }
  </style>
</head>
<body>
  <button class="no-print" onclick="window.print()" style="position:fixed;top:1rem;right:1rem;padding:0.5rem 1.2rem;background:#0d6efd;color:white;border:none;border-radius:6px;cursor:pointer;font-size:14px;">🖨️ Imprimer / Sauvegarder PDF</button>

  <h1>🗳️ Vote Lab — Rapport de simulation</h1>
  <div class="meta">Généré le ${date} · ${numSimulations} simulations · ${methodNames.length} méthodes analysées</div>

  <h2>Configuration</h2>
  <div class="config-grid">
    <div class="config-item"><strong>Candidats</strong>${configA.candidateInput}</div>
    <div class="config-item"><strong>Électeurs / simulation</strong>${configA.numVoters.toLocaleString()}</div>
    <div class="config-item"><strong>Distribution idéologique</strong>${configA.ideology_distribution}</div>
    <div class="config-item"><strong>Nombre de simulations</strong>${numSimulations}</div>
  </div>

  <h2>Vainqueurs par méthode</h2>
  <table>
    <thead><tr><th>Méthode</th><th>Vainqueur dominant (n/N)</th><th>Regret bayésien moyen</th></tr></thead>
    <tbody>${methodRows}</tbody>
  </table>

  <h2>Analyse et conclusions</h2>
  <div class="conclusion">${conclusion}</div>

  <div class="meta" style="margin-top:1cm; border-top:1px solid #dee2e6; padding-top:0.5cm;">
    Vote Lab · Outil de recherche sur les méthodes de vote ·
    Modèle spatial de vote avec utilité bayésienne et vote stratégique
    ${shareUrl ? `<br/><strong>Lien permanent :</strong>
    <a href="${shareUrl}" style="color:#0d6efd; word-break:break-all;">${shareUrl}</a>` : ''}
  </div>
</body>
</html>`;
}

// ── Page ───────────────────────────────────────────────────────────────────

interface SharedConfig {
  n: number;
  sc: 1 | 2;
  a: { nv: number; c: string; id: string };
  b?: { nv: number; c: string; id: string };
}

const SimulationComparePage: React.FC = () => {
  const { t } = useTranslation();
  const methodLabels = useMethodLabels();

  const TAB_LABELS: Record<string, string> = {
    winners:          t('simulation.tabs.winners'),
    metrics:          t('simulation.tabs.metrics'),
    strategic:        t('simulation.tabs.strategic'),
    condorcet:        t('simulation.tabs.condorcet'),
    arrow:            t('simulation.tabs.arrow'),
    bandwagon:        t('simulation.tabs.bandwagon'),
    montecarlo:       t('simulation.tabs.montecarlo'),
    'real-elections': t('simulation.tabs.realElections'),
    multiwinner:      t('simulation.tabs.multiwinner'),
    sensitivity:      t('simulation.tabs.sensitivity'),
  };

  // ── Scenario config ──
  const [numSimulations, setNumSimulations] = useState(10);
  const [configA, setConfigA] = useState<ScenarioConfig>({
    numVoters: 500,
    candidateInput: 'Alice, Bob, Charlie',
    ideology_distribution: 'random',
  });
  const [scenarioCount, setScenarioCount] = useState<1 | 2>(1);
  const [configB, setConfigB] = useState<ScenarioConfig>({
    numVoters: 500,
    candidateInput: 'Alice, Bob, Charlie, Carol',
    ideology_distribution: 'random',
  });

  // ── Results ──
  const [comparisonResults, setComparisonResults] = useState<SimulationCompareResult[]>([]);
  const [strategicData, setStrategicData] = useState<StrategicImpactPoint[]>([]);
  const [condorcetData, setCondorcetData] = useState<CondorcetMatrixResult | null>(null);
  const [arrowData, setArrowData] = useState<ArrowCriteriaResult | null>(null);
  const [resultsB, setResultsB] = useState<SimulationCompareResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const toast = useToast();
  const { expertMode, setExpertMode } = useExpertMode();

  // ── Save / Load modal state ──
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [saveName, setSaveName] = useState('');
  const [saving, setSaving] = useState(false);
  const [showLoadModal, setShowLoadModal] = useState(false);
  const [scenarioList, setScenarioList] = useState<ScenarioSummary[]>([]);
  const [loadingList, setLoadingList] = useState(false);

  // ── UI state ──
  const [activeTab, setActiveTab] = useState('winners');
  const [presentationMode, setPresentationMode] = useState(false);
  const [presentationTabIndex, setPresentationTabIndex] = useState(0);
  const [linkCopied, setLinkCopied] = useState(false);
  const [reportCopied, setReportCopied] = useState(false);

  // ── Restore config from URL on mount ──
  useEffect(() => {
    const raw = readShareParam();
    if (!raw) return;
    const cfg = decodeShareConfig<SharedConfig>(raw);
    if (!cfg) return;
    if (cfg.n) setNumSimulations(cfg.n);
    if (cfg.sc) setScenarioCount(cfg.sc);
    if (cfg.a) setConfigA({ numVoters: cfg.a.nv, candidateInput: cfg.a.c, ideology_distribution: cfg.a.id });
    if (cfg.b) setConfigB({ numVoters: cfg.b.nv, candidateInput: cfg.b.c, ideology_distribution: cfg.b.id });
  }, []);

  // ── Keyboard navigation for presentation mode ──
  useEffect(() => {
    if (!presentationMode) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') setPresentationTabIndex((i) => Math.min(i + 1, TAB_ORDER.length - 1));
      if (e.key === 'ArrowLeft')  setPresentationTabIndex((i) => Math.max(i - 1, 0));
      if (e.key === 'Escape')     setPresentationMode(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [presentationMode]);

  // Keep active tab in sync with presentation tab
  useEffect(() => {
    if (presentationMode) setActiveTab(TAB_ORDER[presentationTabIndex]);
  }, [presentationMode, presentationTabIndex]);

  // ── Derived ──
  const candidateNamesA = useMemo(
    () => configA.candidateInput.split(',').map((s) => s.trim()).filter(Boolean),
    [configA.candidateInput]
  );
  const candidateNamesB = useMemo(
    () => configB.candidateInput.split(',').map((s) => s.trim()).filter(Boolean),
    [configB.candidateInput]
  );
  const candidateColorMap = useMemo(() => {
    const names = new Set<string>();
    [...comparisonResults, ...(resultsB ?? [])].forEach((r) =>
      Object.values(r.methods).forEach((m) => { if (m.winner) names.add(m.winner); })
    );
    return Object.fromEntries(
      [...names].map((name, i) => [name, CANDIDATE_PALETTE[i % CANDIDATE_PALETTE.length]])
    );
  }, [comparisonResults, resultsB]);
  const allMethodNames = useMemo(() => {
    if (!comparisonResults.length) return [];
    const all = Object.keys(comparisonResults[0].methods);
    return expertMode ? all : all.filter((m) => BEGINNER_METHODS.includes(m));
  }, [comparisonResults, expertMode]);

  const visibleTabs = expertMode ? TAB_ORDER : BEGINNER_TABS;

  // ── Run analysis ──
  const runAnalysis = async () => {
    if (candidateNamesA.length < 2) { toast.error(t('simulation.errMinCandA')); return; }
    if (scenarioCount === 2 && candidateNamesB.length < 2) { toast.error(t('simulation.errMinCandB')); return; }
    setLoading(true);
    try {
      const paramsA = { num_voters: configA.numVoters, candidates: candidateNamesA, ideology_distribution: configA.ideology_distribution };
      const [simResultsA, strategicResults, condorcetResult, arrowResult, simResultsB] = await Promise.all([
        Promise.all(Array.from({ length: numSimulations }, () => runComparisonSimulation(paramsA))),
        runStrategicImpactAnalysis({ ...paramsA, strategic_percentages: STRATEGIC_PERCENTAGES }),
        getCondorcetMatrix(paramsA),
        getArrowCriteria(paramsA),
        scenarioCount === 2
          ? Promise.all(Array.from({ length: numSimulations }, () => runComparisonSimulation({ num_voters: configB.numVoters, candidates: candidateNamesB, ideology_distribution: configB.ideology_distribution })))
          : Promise.resolve(null),
      ]);
      setComparisonResults(simResultsA);
      setStrategicData(strategicResults);
      setCondorcetData(condorcetResult);
      setArrowData(arrowResult);
      setResultsB(simResultsB);
    } catch {
      toast.error(t('simulation.errBackend'));
    } finally {
      setLoading(false);
    }
  };

  // ── Export ──
  const exportDate = new Date().toISOString().slice(0, 10);

  const exportJSON = () => {
    const blob = new Blob([JSON.stringify({ comparisonResults, strategicData }, null, 2)], { type: 'application/json' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `simulation_results_${exportDate}.json`; a.click();
  };

  const exportCSV = () => {
    const header = 'simulation_id,method,winner,bayesian_regret,majority_satisfaction,strategic_vulnerability,condorcet_consistent\n';
    const rows = comparisonResults.flatMap((r, idx) =>
      Object.entries(r.methods).map(([method, m]) =>
        [idx + 1, method, m.winner ?? '', m.bayesian_regret ?? '', m.majority_satisfaction ?? '', m.strategic_vulnerability ?? '', m.condorcet_consistent ?? ''].join(',')
      )
    );
    const blob = new Blob([header + rows.join('\n')], { type: 'text/csv' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `simulation_results_${exportDate}.csv`; a.click();
  };

  const exportReport = () => {
    const conclusion = buildConclusion(comparisonResults, allMethodNames);
    const cfgUrl = buildShareURL({
      n: numSimulations, sc: scenarioCount,
      a: { nv: configA.numVoters, c: configA.candidateInput, id: configA.ideology_distribution },
      ...(scenarioCount === 2 ? { b: { nv: configB.numVoters, c: configB.candidateInput, id: configB.ideology_distribution } } : {}),
    });
    const html = buildReportHTML(configA, numSimulations, comparisonResults, allMethodNames, conclusion, exportDate, cfgUrl);
    const win = window.open('', '_blank');
    if (!win) return;
    win.document.write(html);
    win.document.close();
  };

  // ── Share link ──
  const copyShareLink = async () => {
    const cfg: SharedConfig = {
      n: numSimulations, sc: scenarioCount,
      a: { nv: configA.numVoters, c: configA.candidateInput, id: configA.ideology_distribution },
      ...(scenarioCount === 2 ? { b: { nv: configB.numVoters, c: configB.candidateInput, id: configB.ideology_distribution } } : {}),
    };
    await copyShareURL(cfg);
    setLinkCopied(true);
    setTimeout(() => setLinkCopied(false), 2000);
  };

  // ── Scenario persistence ──
  const handleSave = async () => {
    if (!saveName.trim()) return;
    setSaving(true);
    try {
      await saveScenario(saveName.trim(), { numSimulations, configA, configB, scenarioCount }, { comparisonResults, strategicData, condorcetData, resultsB });
      setShowSaveModal(false); setSaveName('');
      toast.success(t('simulation.scenarioSaved'));
    } finally { setSaving(false); }
  };

  const handleOpenLoadModal = async () => {
    setShowLoadModal(true); setLoadingList(true);
    try { setScenarioList(await listScenarios()); } finally { setLoadingList(false); }
  };

  const handleLoad = async (scenario: ScenarioDetail) => {
    const cfg = scenario.config as any; const res = scenario.results as any;
    if (cfg) {
      if (cfg.numSimulations != null) setNumSimulations(cfg.numSimulations);
      if (cfg.configA) setConfigA(cfg.configA);
      if (cfg.configB) setConfigB(cfg.configB);
      if (cfg.scenarioCount) setScenarioCount(cfg.scenarioCount);
    }
    if (res) {
      if (res.comparisonResults) setComparisonResults(res.comparisonResults);
      if (res.strategicData) setStrategicData(res.strategicData);
      if ('condorcetData' in res) setCondorcetData(res.condorcetData);
      if ('resultsB' in res) setResultsB(res.resultsB);
    }
    setShowLoadModal(false);
    toast.success(t('simulation.scenarioLoaded'));
  };

  const handleDelete = async (id: number) => {
    await deleteScenario(id);
    setScenarioList((prev) => prev.filter((s) => s.id !== id));
  };

  const hasResults = comparisonResults.length > 0;
  const baseParamsA = { num_voters: configA.numVoters, candidates: candidateNamesA, ideology_distribution: configA.ideology_distribution };

  // ── Simulation summary (for meta tags + report sharing) ───────────────────
  const simulationSummary = useMemo(() => {
    if (!hasResults || !allMethodNames.length) return null;
    const avg = (vals: number[]) => vals.reduce((a, b) => a + b, 0) / (vals.length || 1);
    const bestM = allMethodNames
      .map((m) => ({ m, v: avg(comparisonResults.map((r) => r.methods[m]?.bayesian_regret ?? 0)) }))
      .filter((x) => x.v > 0)
      .sort((a, b) => a.v - b.v)[0]?.m ?? null;
    const divergences = allMethodNames.filter((m) => {
      const ws = new Set(comparisonResults.map((r) => r.methods[m]?.winner).filter(Boolean));
      return ws.size > 1;
    }).length;
    return { bestM, divergences };
  }, [hasResults, allMethodNames, comparisonResults]);

  // ── Meta tags — updated after simulation ──────────────────────────────────
  useMetaTags({
    title: simulationSummary?.bestM
      ? `${configA.candidateInput} — ${methodLabels[simulationSummary.bestM] ?? simulationSummary.bestM} — Vote Lab`
      : `Vote Lab — ${t('simulation.pageTitle')}`,
    description: hasResults
      ? `${allMethodNames.length} methods · ${configA.numVoters} voters · ${simulationSummary?.divergences ?? 0} divergences`
      : '15 voting methods compared. Bayesian regret, Condorcet, strategic vulnerability.',
  });

  // ── Share report handler ──────────────────────────────────────────────────
  const shareReport = async () => {
    const cfg: SharedConfig = {
      n: numSimulations, sc: scenarioCount,
      a: { nv: configA.numVoters, c: configA.candidateInput, id: configA.ideology_distribution },
      ...(scenarioCount === 2 ? { b: { nv: configB.numVoters, c: configB.candidateInput, id: configB.ideology_distribution } } : {}),
    };
    const summary = simulationSummary
      ? { b: simulationSummary.bestM, d: simulationSummary.divergences }
      : {};
    const encoded = encodeShareConfig({ ...cfg, rs: summary });
    const url = `${window.location.origin}${window.location.pathname}?cfg=${encoded}`;
    await navigator.clipboard.writeText(url);
    setReportCopied(true);
    setTimeout(() => setReportCopied(false), 2500);
  };

  // ── Presentation mode overlay ──────────────────────────────────────────────
  const PresentationOverlay = presentationMode ? (
    <div style={{ position: 'fixed', inset: 0, zIndex: 9999, background: 'white', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header */}
      <div className="d-flex align-items-center justify-content-between px-4 py-2" style={{ background: '#0d6efd', color: 'white', flexShrink: 0 }}>
        <div className="d-flex align-items-center gap-2">
          <span className="fw-semibold">{t('simulation.presentationMode')}</span>
          <Badge bg="light" text="dark">{presentationTabIndex + 1} / {TAB_ORDER.length}</Badge>
        </div>
        <span className="fw-bold" style={{ fontSize: '1rem' }}>{TAB_LABELS[TAB_ORDER[presentationTabIndex]]}</span>
        <Button variant="outline-light" size="sm" onClick={() => setPresentationMode(false)}>
          ✕ {t('simulation.quit')} <kbd style={{ fontSize: '0.7rem', opacity: 0.7 }}>{t('simulation.quitHint')}</kbd>
        </Button>
      </div>

      {/* Content — mirrors the controlled Tabs below via shared state */}
      <div style={{ flex: 1, overflow: 'auto', padding: '1.5rem' }}>
        {/* The <Tabs> below is controlled and already shows the right tab. We show it by scroll. */}
        <div className="text-muted text-center py-3 small">
          Le contenu s'affiche dans la zone principale (faites défiler si nécessaire)
        </div>
      </div>

      {/* Footer navigation */}
      <div className="d-flex align-items-center justify-content-between px-4 py-3 border-top" style={{ flexShrink: 0 }}>
        <Button variant="outline-secondary" disabled={presentationTabIndex === 0} onClick={() => setPresentationTabIndex((i) => i - 1)}>
          {t('simulation.prev')}
        </Button>
        <div className="d-flex gap-1">
          {TAB_ORDER.map((t, i) => (
            <span
              key={t}
              title={TAB_LABELS[t]}
              onClick={() => setPresentationTabIndex(i)}
              style={{ cursor: 'pointer', fontSize: '0.65rem', color: i === presentationTabIndex ? '#0d6efd' : '#dee2e6' }}
            >
              ●
            </span>
          ))}
        </div>
        <Button variant="outline-secondary" disabled={presentationTabIndex === TAB_ORDER.length - 1} onClick={() => setPresentationTabIndex((i) => i + 1)}>
          {t('simulation.next')}
        </Button>
      </div>
    </div>
  ) : null;

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <>
      {PresentationOverlay}

      <Container className="py-4">
        <h2 className="mb-1">{t('simulation.pageTitle')}</h2>
        <p className="text-muted mb-3">{t('simulation.pageSubtitle')}</p>

        <div className="d-flex gap-2 mb-4 flex-wrap">
          <Button variant="outline-secondary" size="sm" onClick={handleOpenLoadModal}>{t('simulation.load')}</Button>
          <Button variant={linkCopied ? 'success' : 'outline-info'} size="sm" onClick={copyShareLink}>
            {linkCopied ? t('simulation.linkCopied') : t('simulation.share')}
          </Button>
          {hasResults && (
            <>
              <Button variant="outline-success" size="sm" onClick={() => { setSaveName(''); setShowSaveModal(true); }}>{t('simulation.save')}</Button>
              <Button variant="outline-primary" size="sm" onClick={exportJSON}>{t('simulation.exportJson')}</Button>
              <Button variant="outline-primary" size="sm" onClick={exportCSV}>{t('simulation.exportCsv')}</Button>
              <Button variant="outline-warning" size="sm" onClick={exportReport}>{t('simulation.exportPdf')}</Button>
              <Button variant={reportCopied ? 'success' : 'outline-secondary'} size="sm" onClick={shareReport}>
                {reportCopied ? t('simulation.reportCopied') : t('simulation.shareReport')}
              </Button>
              <Button variant="outline-dark" size="sm" onClick={() => { setPresentationTabIndex(0); setPresentationMode(true); }}>
                {t('simulation.presentation')}
              </Button>
            </>
          )}
        </div>

        {/* ── Configuration ── */}
        <Card className="mb-4">
          <Card.Header className="d-flex align-items-center justify-content-between">
            <strong>{t('simulation.configTitle')}</strong>
            {scenarioCount === 1 ? (
              <Button size="sm" variant="outline-secondary" onClick={() => setScenarioCount(2)}>{t('simulation.addScenarioB')}</Button>
            ) : (
              <Button size="sm" variant="outline-danger" onClick={() => { setScenarioCount(1); setResultsB(null); }}>{t('simulation.removeScenarioB')}</Button>
            )}
          </Card.Header>
          <Card.Body>
            <Row className="g-3 align-items-end mb-3">
              <Col md={4}>
                <Form.Label>{t('simulation.simulationsLabel')} <strong>{numSimulations}</strong></Form.Label>
                <Form.Range min={5} max={20} value={numSimulations} onChange={(e) => setNumSimulations(Number(e.target.value))} />
              </Col>
              <Col md={2}>
                <Button variant="primary" className="w-100" onClick={runAnalysis} disabled={loading}>
                  {loading ? <><Spinner size="sm" className="me-2" />{t('simulation.running')}</> : t('simulation.runAnalysis')}
                </Button>
              </Col>
            </Row>
            {scenarioCount === 1 ? (
              <ScenarioConfigRow config={configA} onChange={(p) => setConfigA((c) => ({ ...c, ...p }))} />
            ) : (
              <Row className="g-3">
                <Col md={6}><ScenarioConfigRow config={configA} onChange={(p) => setConfigA((c) => ({ ...c, ...p }))} label={t('simulation.scenarioA')} /></Col>
                <Col md={6}><ScenarioConfigRow config={configB} onChange={(p) => setConfigB((c) => ({ ...c, ...p }))} label={t('simulation.scenarioB')} /></Col>
              </Row>
            )}
          </Card.Body>
        </Card>

        {loading && (
          <Row className="g-3 mb-4">
            {[0, 1, 2].map((i) => (
              <Col key={i} md={4}><SkeletonCard height={180} /></Col>
            ))}
          </Row>
        )}
        {!hasResults && !loading && (
          <Alert variant="info" dangerouslySetInnerHTML={{ __html: t('simulation.noResults') }} />
        )}

        {hasResults && !expertMode && (
          <Alert variant="secondary" className="py-2 mb-3 d-flex align-items-center justify-content-between flex-wrap gap-2">
            <span>
              <strong>{t('simulation.beginnerBanner')}</strong> — {t('simulation.beginnerBannerDetail', {
                shown: BEGINNER_METHODS.length,
                total: comparisonResults.length > 0 ? Object.keys(comparisonResults[0].methods).length : 15,
                shownTabs: BEGINNER_TABS.length,
                totalTabs: TAB_ORDER.length,
              })}
            </span>
            <Button variant="outline-secondary" size="sm" onClick={() => setExpertMode(true)}>
              {t('simulation.switchExpert')}
            </Button>
          </Alert>
        )}

        {hasResults && (
          <Tabs
            activeKey={activeTab}
            onSelect={(k) => { if (k) { setActiveTab(k); if (presentationMode) setPresentationTabIndex(TAB_ORDER.indexOf(k)); }}}
            className="mb-3"
          >
            <Tab eventKey="winners" title={scenarioCount === 2 ? t('simulation.tabs.scenarioComparison') : t('simulation.tabs.winners')}>
              <WinnerMatrixTab comparisonResults={comparisonResults} resultsB={resultsB} allMethodNames={allMethodNames} candidateColorMap={candidateColorMap} configA={configA} configB={configB} numSimulations={numSimulations} scenarioCount={scenarioCount} />
            </Tab>
            <Tab eventKey="metrics" title={t('simulation.tabs.metrics')}>
              <MetricsTab comparisonResults={comparisonResults} allMethodNames={allMethodNames} numSimulations={numSimulations} />
            </Tab>
            <Tab eventKey="strategic" title={t('simulation.tabs.strategic')}>
              <StrategicImpactTab strategicData={strategicData} allMethodNames={allMethodNames} />
            </Tab>
            {visibleTabs.includes('condorcet') && (
              <Tab eventKey="condorcet" title={t('simulation.tabs.condorcet')}>
                <Card className="mb-4">
                  <Card.Header><strong>{t('simulation.condorcetHeader')}</strong><span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>{t('simulation.condorcetSubtitle')}</span></Card.Header>
                  <Card.Body>{condorcetData ? <CondorcetMatrix result={condorcetData} /> : <Alert variant="info">{t('simulation.condorcetNoData')}</Alert>}</Card.Body>
                </Card>
              </Tab>
            )}
            {visibleTabs.includes('arrow') && (
              <Tab eventKey="arrow" title={
                <span>
                  {t('simulation.tabs.arrow')}{' '}
                  <OverlayTrigger trigger={['hover','focus']} placement="bottom" overlay={<Tooltip id="tip-tab-arrow">{t('simulation.tabTips.arrow')}</Tooltip>}>
                    <span tabIndex={0} onClick={(e) => e.stopPropagation()} style={{ fontSize: '0.75em', color: '#6c757d', cursor: 'help' }}>ⓘ</span>
                  </OverlayTrigger>
                </span>
              }>
                <Card className="mb-4">
                  <Card.Header><strong>{t('simulation.arrowHeader')}</strong><span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>{t('simulation.arrowSubtitle')}</span></Card.Header>
                  <Card.Body>{arrowData ? <ArrowCriteriaMatrix result={arrowData} /> : <Alert variant="info">{t('simulation.arrowNoData')}</Alert>}</Card.Body>
                </Card>
              </Tab>
            )}
            {visibleTabs.includes('bandwagon') && (
              <Tab eventKey="bandwagon" title={
                <span>
                  {t('simulation.tabs.bandwagon')}{' '}
                  <OverlayTrigger trigger={['hover','focus']} placement="bottom" overlay={<Tooltip id="tip-tab-bandwagon">{t('simulation.tabTips.bandwagon')}</Tooltip>}>
                    <span tabIndex={0} onClick={(e) => e.stopPropagation()} style={{ fontSize: '0.75em', color: '#6c757d', cursor: 'help' }}>ⓘ</span>
                  </OverlayTrigger>
                </span>
              }><BandwagonAnalysis baseParams={baseParamsA} /></Tab>
            )}
            <Tab eventKey="montecarlo" title={t('simulation.tabs.montecarlo')}><MonteCarloResults baseParams={baseParamsA} /></Tab>
            <Tab eventKey="real-elections" title={t('simulation.tabs.realElections')}><RealElectionsTab /></Tab>
            {visibleTabs.includes('multiwinner') && (
              <Tab eventKey="multiwinner" title={t('simulation.tabs.multiwinner')}><MultiwinnerAnalysis /></Tab>
            )}
            {visibleTabs.includes('sensitivity') && (
              <Tab eventKey="sensitivity" title={
                <span>
                  {t('simulation.tabs.sensitivity')}{' '}
                  <OverlayTrigger trigger={['hover','focus']} placement="bottom" overlay={<Tooltip id="tip-tab-sensitivity">{t('simulation.tabTips.sensitivity')}</Tooltip>}>
                    <span tabIndex={0} onClick={(e) => e.stopPropagation()} style={{ fontSize: '0.75em', color: '#6c757d', cursor: 'help' }}>ⓘ</span>
                  </OverlayTrigger>
                </span>
              }><SensitivityTab baseConfig={{ numVoters: configA.numVoters, candidates: candidateNamesA, ideology_distribution: configA.ideology_distribution }} /></Tab>
            )}
          </Tabs>
        )}

        <ScenarioModals
          showSaveModal={showSaveModal} setShowSaveModal={setShowSaveModal}
          saveName={saveName} setSaveName={setSaveName} saving={saving} handleSave={handleSave}
          showLoadModal={showLoadModal} setShowLoadModal={setShowLoadModal}
          scenarioList={scenarioList} loadingList={loadingList}
          handleLoad={handleLoad} handleDelete={handleDelete}
        />
      </Container>
    </>
  );
};

export default SimulationComparePage;
