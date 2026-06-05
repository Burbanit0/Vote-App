/**
 * BlankVoteTimeSeries — Historical blank-vote trend visualization.
 *
 * Features:
 *   - Multi-country LineChart (France, Colombia, Uruguay)
 *   - Coloured dots: green (<2%), orange (2–5%), red (>5%)
 *   - Vertical ReferenceLine on notable political events
 *   - Automatic linear trend analysis per country
 *   - Peak detection
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Check } from '@/components/ui/form-controls';
import { Spinner } from '@/components/ui/spinner';
import {
  CartesianGrid,
  Dot,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  getBlankHistory,
  BlankHistoryPoint,
  BlankHistoryResult,
} from '../../services/simulationCompareApi';

// ── Constants ─────────────────────────────────────────────────────────────────

const COUNTRIES = [
  { key: 'france', label: '🇫🇷 France', color: '#1a56cc' },
  { key: 'colombia', label: '🇨🇴 Colombie', color: '#b71c1c' },
  { key: 'uruguay', label: '🇺🇾 Uruguay', color: '#006957' },
];

// Notable events to annotate on the chart
const EVENTS: { year: number; label: string; country?: string }[] = [
  { year: 2002, label: 'Choc du 21 avril (FR)', country: 'france' },
  { year: 2014, label: 'Record voto en blanco (CO)', country: 'colombia' },
  { year: 2017, label: 'Séparation blanc/nul (FR)', country: 'france' },
];

// Colour by value
function dotColor(pct: number): string {
  if (pct < 2) return '#1b5e20'; // green
  if (pct < 5) return '#b35c00'; // orange
  return '#b71c1c'; // red
}

// ── Linear trend helper ────────────────────────────────────────────────────────

function linearTrend(series: BlankHistoryPoint[]): number {
  const n = series.length;
  if (n < 2) return 0;
  const mX = series.reduce((s, p) => s + p.year, 0) / n;
  const mY = series.reduce((s, p) => s + p.blank_pct, 0) / n;
  const num = series.reduce((s, p) => s + (p.year - mX) * (p.blank_pct - mY), 0);
  const den = series.reduce((s, p) => s + (p.year - mX) ** 2, 0);
  return den > 0 ? num / den : 0; // pct per year
}

// ── Custom dot — coloured by value ────────────────────────────────────────────

function ColoredDot(props: any) {
  const { cx, cy, payload } = props;
  if (!cx || !cy) return null;
  // Find blank_pct from any country key
  const pct = Object.values(payload).find((v) => typeof v === 'number' && v >= 0 && v <= 100) as
    | number
    | undefined;
  return (
    <circle
      cx={cx}
      cy={cy}
      r={5}
      fill={pct !== undefined ? dotColor(pct) : '#6c757d'}
      stroke="white"
      strokeWidth={1.5}
    />
  );
}

// ── Custom tooltip ────────────────────────────────────────────────────────────

function TimeTooltip({ active, payload, label, allData }: any) {
  if (!active || !payload?.length) return null;

  // Find context for this year from the loaded data
  const contexts: string[] = [];
  (allData as Record<string, BlankHistoryResult | null>).france &&
    (allData as any).france?.series.find((p: BlankHistoryPoint) => {
      if (p.year === label && p.context) contexts.push(`🇫🇷 ${p.context}`);
    });
  (allData as any).colombia?.series.find((p: BlankHistoryPoint) => {
    if (p.year === label && p.context) contexts.push(`🇨🇴 ${p.context}`);
  });
  (allData as any).uruguay?.series.find((p: BlankHistoryPoint) => {
    if (p.year === label && p.context) contexts.push(`🇺🇾 ${p.context}`);
  });

  return (
    <div
      style={{
        background: 'var(--bs-body-bg, white)',
        border: '1px solid var(--bs-border-color, #dee2e6)',
        borderRadius: 8,
        padding: '10px 14px',
        maxWidth: 320,
        fontSize: '0.82rem',
        boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
      }}
    >
      <div className="font-bold mb-1">{label}</div>
      {payload.map((entry: any) => (
        <div key={entry.dataKey} style={{ color: entry.stroke }} className="mb-1">
          {entry.name} : <strong>{entry.value?.toFixed(1)} %</strong>
        </div>
      ))}
      {contexts.map((ctx, i) => (
        <div
          key={i}
          className="text-muted-foreground mt-2"
          style={{ fontSize: '0.76rem', lineHeight: 1.4 }}
        >
          {ctx}
        </div>
      ))}
    </div>
  );
}

// ── Trend analysis text ───────────────────────────────────────────────────────

interface TrendAnalysis {
  slopePerDecade: number;
  startYear: number;
  endYear: number;
  peak: BlankHistoryPoint;
  min: BlankHistoryPoint;
  displayName: string;
}

function computeTrend(data: BlankHistoryResult): TrendAnalysis {
  const { series, display_name } = data;
  const slope = linearTrend(series) * 10; // pct per decade
  const peak = series.reduce((a, b) => (b.blank_pct > a.blank_pct ? b : a));
  const min = series.reduce((a, b) => (b.blank_pct < a.blank_pct ? b : a));
  return {
    slopePerDecade: slope,
    startYear: series[0].year,
    endYear: series[series.length - 1].year,
    peak,
    min,
    displayName: display_name,
  };
}

// ── BlankVoteTimeSeries ───────────────────────────────────────────────────────

const BlankVoteTimeSeries: React.FC = () => {
  const [selected, setSelected] = useState<Set<string>>(new Set(['france']));
  const [loaded, setLoaded] = useState<Record<string, BlankHistoryResult | null>>({});
  const [loading, setLoading] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  const fetchCountry = useCallback(
    async (key: string) => {
      if (loaded[key] !== undefined || loading.has(key)) return;
      setLoading((prev) => new Set([...prev, key]));
      try {
        const data = await getBlankHistory(key);
        setLoaded((prev) => ({ ...prev, [key]: data }));
      } catch {
        setLoaded((prev) => ({ ...prev, [key]: null }));
        setError(`Impossible de charger les données pour "${key}".`);
      } finally {
        setLoading((prev) => {
          const s = new Set(prev);
          s.delete(key);
          return s;
        });
      }
    },
    [loaded, loading]
  );

  // Fetch on mount and when selection changes
  useEffect(() => {
    selected.forEach((key) => fetchCountry(key));
  }, [selected, fetchCountry]);

  const toggleCountry = (key: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        if (next.size === 1) return prev; // keep at least one
        next.delete(key);
      } else {
        next.add(key);
        fetchCountry(key);
      }
      return next;
    });
  };

  // ── Build unified chart data ──────────────────────────────────────────────
  const allYears = new Set<number>();
  COUNTRIES.forEach(({ key }) => {
    if (selected.has(key) && loaded[key]) {
      loaded[key]!.series.forEach((p) => allYears.add(p.year));
    }
  });
  const chartData = [...allYears].sort().map((year) => {
    const row: Record<string, number | string> = { year };
    COUNTRIES.forEach(({ key, label }) => {
      if (selected.has(key) && loaded[key]) {
        const point = loaded[key]!.series.find((p) => p.year === year);
        if (point) row[label] = point.blank_pct;
      }
    });
    return row;
  });

  // Visible events for selected countries
  const visibleEvents = EVENTS.filter((e) => !e.country || selected.has(e.country));

  // Trend analyses
  const trends = COUNTRIES.filter(({ key }) => selected.has(key) && loaded[key]).map(({ key }) =>
    computeTrend(loaded[key]!)
  );

  const isAnyLoading = loading.size > 0;

  return (
    <div>
      {/* Country selector */}
      <div className="flex gap-3 mb-3 flex-wrap" role="group" aria-label="Choisir les pays">
        {COUNTRIES.map(({ key, label, color }) => (
          <Check
            key={key}
            id={`bvts-${key}`}
            type="checkbox"
            label={label}
            checked={selected.has(key)}
            onChange={() => toggleCountry(key)}
            style={{ accentColor: color, fontWeight: selected.has(key) ? 600 : 400 }}
          />
        ))}
        {isAnyLoading && <Spinner size="sm" className="self-center" />}
      </div>

      {error && (
        <Alert variant="danger" className="py-2">
          {error}
        </Alert>
      )}

      {/* Chart */}
      <Card className="mb-3">
        <CardHeader className="block space-y-0 border-b border-border px-4 py-2 flex items-center justify-between">
          <strong>Taux de vote blanc dans le temps</strong>
          <div className="flex gap-3" style={{ fontSize: '0.78rem' }}>
            {[
              ['<2%', '#1b5e20', 'Faible'],
              ['2–5%', '#b35c00', 'Modéré'],
              ['>5%', '#b71c1c', 'Élevé'],
            ].map(([range, color, label]) => (
              <span key={range}>
                <span
                  style={{
                    display: 'inline-block',
                    width: 10,
                    height: 10,
                    borderRadius: '50%',
                    background: color,
                    marginRight: 4,
                  }}
                />
                {label} ({range})
              </span>
            ))}
          </div>
        </CardHeader>
        <CardBody>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 16 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--bs-border-color, #dee2e6)" />
              <XAxis
                dataKey="year"
                type="number"
                domain={['dataMin', 'dataMax']}
                tickCount={10}
                label={{ value: 'Année', position: 'insideBottom', offset: -10, fontSize: 11 }}
                tick={{ fontSize: 11 }}
              />
              <YAxis
                domain={[0, 8]}
                tickFormatter={(v) => `${v}%`}
                label={{
                  value: 'Vote blanc (%)',
                  angle: -90,
                  position: 'insideLeft',
                  fontSize: 11,
                }}
                tick={{ fontSize: 11 }}
                width={52}
              />
              <Tooltip content={<TimeTooltip allData={loaded} />} />
              <Legend verticalAlign="top" />

              {/* Threshold reference lines */}
              <ReferenceLine
                y={2}
                stroke="#b35c00"
                strokeDasharray="4 2"
                strokeOpacity={0.5}
                label={{ value: '2%', position: 'right', fontSize: 10, fill: '#b35c00' }}
              />
              <ReferenceLine
                y={5}
                stroke="#b71c1c"
                strokeDasharray="4 2"
                strokeOpacity={0.5}
                label={{ value: '5%', position: 'right', fontSize: 10, fill: '#b71c1c' }}
              />

              {/* Event lines */}
              {visibleEvents.map((ev) => (
                <ReferenceLine
                  key={`${ev.year}-${ev.label}`}
                  x={ev.year}
                  stroke="#6c757d"
                  strokeDasharray="3 3"
                  strokeOpacity={0.6}
                  label={{ value: '●', position: 'top', fontSize: 10, fill: '#6c757d' }}
                />
              ))}

              {/* Country lines */}
              {COUNTRIES.filter(({ key }) => selected.has(key) && loaded[key]).map(
                ({ key, label, color }) => (
                  <Line
                    key={key}
                    type="monotone"
                    dataKey={label}
                    stroke={color}
                    strokeWidth={2}
                    connectNulls
                    dot={(props: any) => <ColoredDot {...props} />}
                    activeDot={{ r: 6, strokeWidth: 2, stroke: 'white' }}
                  />
                )
              )}
            </LineChart>
          </ResponsiveContainer>

          {/* Event legend */}
          {visibleEvents.length > 0 && (
            <div
              className="mt-1 flex flex-wrap gap-3"
              style={{ fontSize: '0.75rem', color: '#6c757d' }}
            >
              {visibleEvents.map((ev) => (
                <span key={ev.label}>
                  ● {ev.year} — {ev.label}
                </span>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      {/* Trend analysis */}
      {trends.length > 0 && (
        <Card>
          <CardHeader className="block space-y-0 border-b border-border px-4 py-2 py-2">
            <strong>📈 Analyse tendancielle</strong>
          </CardHeader>
          <CardBody>
            {trends.map((trend, i) => (
              <div key={i} className="mb-3">
                <div className="font-semibold mb-1" style={{ fontSize: '0.88rem' }}>
                  {trend.displayName.split('—')[0].trim()}
                </div>
                <ul
                  className="mb-0"
                  style={{ fontSize: '0.83rem', lineHeight: 1.7, paddingLeft: '1.2rem' }}
                >
                  <li>
                    Tendance {trend.slopePerDecade >= 0 ? '↑ hausse' : '↓ baisse'} de{' '}
                    <strong>
                      {trend.slopePerDecade >= 0 ? '+' : ''}
                      {trend.slopePerDecade.toFixed(2)} pt
                    </strong>{' '}
                    par décennie depuis {trend.startYear}
                    {trend.slopePerDecade > 0.3 && (
                      <Badge variant="warning" className="ms-2" style={{ fontSize: '0.7rem' }}>
                        Tendance à surveiller
                      </Badge>
                    )}
                  </li>
                  <li>
                    Pic en <strong>{trend.peak.year}</strong> :{' '}
                    <strong>{trend.peak.blank_pct.toFixed(1)} %</strong> (+
                    {(trend.peak.blank_pct - trend.min.blank_pct).toFixed(1)} pts vs minimum)
                  </li>
                  <li>
                    Niveau le plus bas : <strong>{trend.min.blank_pct.toFixed(1)} %</strong> en{' '}
                    {trend.min.year}
                  </li>
                </ul>
              </div>
            ))}
          </CardBody>
        </Card>
      )}

      {/* Country notes */}
      {COUNTRIES.filter(({ key }) => selected.has(key) && loaded[key]).map(({ key, label }) => (
        <Alert
          key={key}
          variant="light"
          className="mt-2 py-2"
          style={{ fontSize: '0.78rem', borderLeft: '3px solid #0d6efd' }}
        >
          <strong>{label} :</strong> {loaded[key]!.note}
        </Alert>
      ))}
    </div>
  );
};

export default BlankVoteTimeSeries;
