/**
 * SortitionPanel — compares three assembly selection methods:
 * election, pure sortition (random sample), stratified sortition.
 * Metrics: representativity, diversity, decision regret, Gini of representation.
 */
import React, { useCallback, useRef, useState } from 'react';
import axios from 'axios';
import { apiPath } from '../../api/apiVersion';
import { useTranslation } from 'react-i18next';
import {
  Alert, Badge, Button, Col, Form, Row, Spinner, Table,
} from 'react-bootstrap';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
  ResponsiveContainer,
} from 'recharts';
import { useElection } from '../../context/ElectionContext';

const API = process.env.REACT_APP_API_URL ?? 'http://localhost:4434';
const DEBOUNCE_MS = 400;

// ── Types ─────────────────────────────────────────────────────────────────────

interface AssemblyMetrics {
  members_ideology_mean: number;
  representativity:      number;
  diversity:             number;
  decision_regret:       number;
  gini_representation:   number;
  demographic_profile:   { age: number; education: number };
}

interface SortitionData {
  population: {
    mean_ideology: number;
    gini_ideology: number;
    demographics:  { mean_age_group: number; mean_education_level: number };
  };
  assemblies: {
    elected:             AssemblyMetrics;
    sortition_pure:      AssemblyMetrics;
    sortition_stratified: AssemblyMetrics;
  };
  variance: { elected: number; sortition_pure: number; sortition_stratified: number };
  winner_by_method:   Record<string, string | null>;
  consensus_possible: boolean;
  pedagogical_note:   string;
}

// ── Historical examples ───────────────────────────────────────────────────────

const EXAMPLES = [
  { year: '-500', location: '🏛 Athènes', desc: 'Boulé (500 citoyens) pendant 200 ans', method: 'Tirage au sort' },
  { year: '2016', location: '🇮🇪 Irlande', desc: '66 citoyens + 33 élus', result: 'Avortement légalisé (66,4%)' },
  { year: '2019', location: '🇫🇷 France',  desc: '150 citoyens (Convention Climat)', result: '149/150 propositions' },
  { year: '2019+', location: '🇧🇪 Bruxelles', desc: 'Assemblée citoyenne permanente', result: 'En cours' },
];

// ── Colour scheme for 3 assemblies ───────────────────────────────────────────

const ASM_COLORS: Record<string, string> = {
  elected:              '#dc3545',
  sortition_pure:       '#198754',
  sortition_stratified: '#005CAB',
};

const ASM_KEYS = ['elected', 'sortition_pure', 'sortition_stratified'] as const;

// ── 1D ideology bar ───────────────────────────────────────────────────────────

interface IdeologyBarProps {
  populationMean: number;
  assemblyMean:   number;
  color:          string;
  label:          string;
}

const IdeologyBar: React.FC<IdeologyBarProps> = ({ populationMean, assemblyMean, color, label }) => {
  const pct = (x: number) => `${Math.round((x + 1) / 2 * 100)}%`;
  return (
    <div className="mb-1">
      <div style={{ fontSize: '0.72rem', color: '#6c757d', marginBottom: 2 }}>{label}</div>
      <div style={{ position: 'relative', height: 12, background: '#f0f0f0', borderRadius: 6, overflow: 'hidden' }}>
        {/* Population mean */}
        <div style={{ position: 'absolute', left: pct(populationMean), top: 0, bottom: 0, width: 2, background: '#adb5bd' }} />
        {/* Assembly mean */}
        <div style={{ position: 'absolute', left: pct(assemblyMean), top: 0, bottom: 0, width: 3, background: color, borderRadius: 2 }} />
      </div>
    </div>
  );
};

// ── Main panel ────────────────────────────────────────────────────────────────

const SortitionPanel: React.FC = () => {
  const { t }      = useTranslation();
  const { config } = useElection();

  const [assemblySize,   setAssemblySize]   = useState(50);
  const [realisticCands, setRealisticCands] = useState(true);
  const [genderParity,   setGenderParity]   = useState(true);
  const [eduQuota,       setEduQuota]       = useState(true);
  const [data,           setData]           = useState<SortitionData | null>(null);
  const [loading,        setLoading]        = useState(false);
  const [error,          setError]          = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const runSimulation = useCallback(async (sz: number, real: boolean, gp: boolean, eq: boolean) => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post(`${API}${apiPath('election/sortition')}`, {
        candidates:             config.candidates.map((c) => ({ name: c.name, x: c.x, y: c.y })),
        num_voters:             config.num_voters,
        assembly_size:          sz,
        ideology:               config.ideology,
        seed:                   config.seed,
        method:                 'plurality',
        realistic_candidates:   real,
        num_simulations:        20,
        stratification:         { age_groups: [0.25, 0.45, 0.30], gender_parity: gp, education_quota: eq },
      });
      setData(res.data);
    } catch {
      setError(t('sortition.error'));
    } finally {
      setLoading(false);
    }
  }, [config, t]);

  const handleSimulate = () => runSimulation(assemblySize, realisticCands, genderParity, eduQuota);

  const schedule = (sz: number, real: boolean, gp: boolean, eq: boolean) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => runSimulation(sz, real, gp, eq), DEBOUNCE_MS);
  };

  // ── Radar data ──────────────────────────────────────────────────────────
  const radarData = data
    ? [
        { metric: t('sortition.representativity'), elected: data.assemblies.elected.representativity, pure: data.assemblies.sortition_pure.representativity, stratified: data.assemblies.sortition_stratified.representativity },
        { metric: t('sortition.diversity'),         elected: data.assemblies.elected.diversity,        pure: data.assemblies.sortition_pure.diversity,        stratified: data.assemblies.sortition_stratified.diversity },
        { metric: t('sortition.lowRegret'),         elected: Math.max(0, 1 - data.assemblies.elected.decision_regret * 2), pure: Math.max(0, 1 - data.assemblies.sortition_pure.decision_regret * 2), stratified: Math.max(0, 1 - data.assemblies.sortition_stratified.decision_regret * 2) },
        { metric: t('sortition.equity'),            elected: Math.max(0, 1 - data.assemblies.elected.gini_representation), pure: Math.max(0, 1 - data.assemblies.sortition_pure.gini_representation), stratified: Math.max(0, 1 - data.assemblies.sortition_stratified.gini_representation) },
      ]
    : [];

  const labelMap: Record<string, string> = {
    elected: t('sortition.elected'),
    sortition_pure: t('sortition.pure'),
    sortition_stratified: t('sortition.stratified'),
  };

  return (
    <div>
      {/* Controls */}
      <Row className="g-2 mb-3 align-items-end">
        <Col xs={12} md={4}>
          <Form.Label className="small mb-0">
            {t('sortition.assemblySize')}: <strong>{assemblySize}</strong>
          </Form.Label>
          <Form.Range
            data-testid="assembly-size-slider"
            min={10} max={300} step={10}
            value={assemblySize}
            onChange={(e) => { setAssemblySize(Number(e.target.value)); schedule(Number(e.target.value), realisticCands, genderParity, eduQuota); }}
          />
        </Col>
        <Col xs="auto">
          <Form.Check type="switch" id="realistic-switch" label={t('sortition.realisticCandidates')}
            checked={realisticCands}
            data-testid="realistic-switch"
            onChange={(e) => { setRealisticCands(e.target.checked); schedule(assemblySize, e.target.checked, genderParity, eduQuota); }}
          />
        </Col>
        <Col xs="auto">
          <Form.Check type="switch" id="parity-switch" label={t('sortition.genderParity')}
            checked={genderParity} onChange={(e) => { setGenderParity(e.target.checked); schedule(assemblySize, realisticCands, e.target.checked, eduQuota); }}
          />
        </Col>
        <Col xs="auto">
          <Form.Check type="switch" id="edu-switch" label={t('sortition.eduQuota')}
            checked={eduQuota} onChange={(e) => { setEduQuota(e.target.checked); schedule(assemblySize, realisticCands, genderParity, e.target.checked); }}
          />
        </Col>
        <Col xs="auto">
          <Button variant="primary" onClick={handleSimulate} disabled={loading} data-testid="simulate-btn">
            {loading ? <Spinner size="sm" animation="border" /> : t('sortition.run')}
          </Button>
        </Col>
      </Row>

      {!data && !loading && !error && (
        <Alert variant="info" role="alert">{t('sortition.prompt')}</Alert>
      )}
      {error && <Alert variant="danger">{error}</Alert>}

      {data && (
        <>
          {/* Consensus badge */}
          {data.consensus_possible
            ? <Badge bg="success" className="mb-3" data-testid="consensus-badge">{t('sortition.consensus')}</Badge>
            : <Badge bg="warning" text="dark" className="mb-3" data-testid="no-consensus-badge">{t('sortition.noConsensus')}</Badge>}

          {/* 3-column ideology comparison */}
          <div className="mb-4" data-testid="ideology-bars">
            <div className="fw-semibold mb-2" style={{ fontSize: '0.85rem' }}>{t('sortition.ideologyTitle')}</div>
            {ASM_KEYS.map((key) => (
              <IdeologyBar key={key}
                populationMean={data.population.mean_ideology}
                assemblyMean={data.assemblies[key].members_ideology_mean}
                color={ASM_COLORS[key]}
                label={`${labelMap[key]} — ${t('sortition.representativity')}: ${(data.assemblies[key].representativity * 100).toFixed(0)}%`}
              />
            ))}
            <div className="d-flex gap-2 mt-1" style={{ fontSize: '0.68rem', color: '#6c757d' }}>
              <span style={{ display: 'inline-block', width: 12, height: 2, background: '#adb5bd' }} /> {t('sortition.population')}
              {ASM_KEYS.map((k) => (
                <span key={k}><span style={{ display: 'inline-block', width: 12, height: 2, background: ASM_COLORS[k] }} /> {labelMap[k]}</span>
              ))}
            </div>
          </div>

          {/* Radar chart */}
          <div className="mb-4" data-testid="radar-chart">
            <div className="fw-semibold mb-1" style={{ fontSize: '0.85rem' }}>{t('sortition.radarTitle')}</div>
            <ResponsiveContainer width="100%" height={280}>
              <RadarChart data={radarData} margin={{ top: 20, right: 30, bottom: 20, left: 30 }}>
                <PolarGrid />
                <PolarAngleAxis dataKey="metric" tick={{ fontSize: 10 }} />
                <Radar name={t('sortition.elected')}    dataKey="elected"    stroke={ASM_COLORS.elected}    fill={ASM_COLORS.elected}    fillOpacity={0.15} />
                <Radar name={t('sortition.pure')}       dataKey="pure"       stroke={ASM_COLORS.sortition_pure}       fill={ASM_COLORS.sortition_pure}       fillOpacity={0.15} />
                <Radar name={t('sortition.stratified')} dataKey="stratified" stroke={ASM_COLORS.sortition_stratified} fill={ASM_COLORS.sortition_stratified} fillOpacity={0.15} />
                <Legend wrapperStyle={{ fontSize: 10 }} />
                <Tooltip />
              </RadarChart>
            </ResponsiveContainer>
          </div>

          {/* Metrics table */}
          <Table size="sm" hover className="mb-4" data-testid="metrics-table">
            <thead>
              <tr>
                <th style={{ fontSize: '0.78rem' }}>{t('sortition.metric')}</th>
                {ASM_KEYS.map((k) => (
                  <th key={k} style={{ fontSize: '0.78rem', color: ASM_COLORS[k] }}>{labelMap[k]}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[
                { key: 'representativity', label: t('sortition.representativity'), fmt: (v: number) => `${(v*100).toFixed(0)}%` },
                { key: 'diversity',        label: t('sortition.diversity'),        fmt: (v: number) => v.toFixed(3) },
                { key: 'decision_regret',  label: t('sortition.regret'),           fmt: (v: number) => v.toFixed(3) },
                { key: 'gini_representation', label: t('sortition.giniRepr'),     fmt: (v: number) => v.toFixed(3) },
              ].map((row) => (
                <tr key={row.key}>
                  <td style={{ fontSize: '0.78rem' }}>{row.label}</td>
                  {ASM_KEYS.map((k) => (
                    <td key={k} style={{ fontSize: '0.78rem' }}>
                      {row.fmt((data.assemblies[k] as any)[row.key])}
                    </td>
                  ))}
                </tr>
              ))}
              <tr>
                <td style={{ fontSize: '0.78rem' }}>{t('sortition.variance')}</td>
                {ASM_KEYS.map((k) => (
                  <td key={k} style={{ fontSize: '0.78rem' }}>
                    {data.variance[k as keyof typeof data.variance].toFixed(4)}
                  </td>
                ))}
              </tr>
              <tr>
                <td style={{ fontSize: '0.78rem' }}>{t('sortition.winner')}</td>
                {ASM_KEYS.map((k) => (
                  <td key={k} style={{ fontSize: '0.78rem' }}>{data.winner_by_method[k] ?? '—'}</td>
                ))}
              </tr>
            </tbody>
          </Table>

          {/* Historical examples */}
          <div className="fw-semibold mb-2" style={{ fontSize: '0.85rem' }}>{t('sortition.examplesTitle')}</div>
          <div className="d-flex flex-wrap gap-2 mb-3" data-testid="examples-section">
            {EXAMPLES.map((ex) => (
              <div key={ex.year} className="border rounded p-2" style={{ fontSize: '0.72rem', background: '#f8f9fa', maxWidth: 200 }}>
                <strong>{ex.location} ({ex.year})</strong>
                <div className="text-muted">{ex.desc}</div>
                {ex.result && <Badge bg="success" style={{ fontSize: '0.6rem' }} className="mt-1">{ex.result}</Badge>}
                <div><code style={{ fontSize: '0.65rem' }}>{ex.method ?? 'Tirage au sort'}</code></div>
              </div>
            ))}
          </div>

          {/* Pedagogical note */}
          <Alert variant="secondary" style={{ fontSize: '0.8rem' }}>
            <strong>{t('sortition.noteTitle')}</strong> {data.pedagogical_note}
          </Alert>
        </>
      )}
    </div>
  );
};

export default SortitionPanel;
