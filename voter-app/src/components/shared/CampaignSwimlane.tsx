import React, { useEffect, useMemo, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { useTranslation } from 'react-i18next';
import { CampaignSnapshot, MethodStability } from '../../services/electionApi';

// ── SVG layout constants ──────────────────────────────────────────────────────

const LABEL_W      = 104;   // method label area width (viewBox units)
const MARGIN_TOP   = 28;    // space for day-axis ticks
const MARGIN_BOTTOM = 10;
const MARGIN_RIGHT  = 10;
const ROW_H        = 24;    // height per method row
const ROW_GAP      = 5;     // gap between rows
const SVG_W        = 680;   // fixed viewBox width
const PLOT_W       = SVG_W - LABEL_W - MARGIN_RIGHT;   // 566

// ── Candidate colour palette (WCAG-AA on white) ───────────────────────────────

const CAND_PALETTE = [
  '#1a56cc', '#b35c00', '#b71c1c', '#006957',
  '#1b5e20', '#544200', '#7B2D8B', '#005f73',
];

// ── Types ─────────────────────────────────────────────────────────────────────

interface Props {
  snapshots:       CampaignSnapshot[];
  methodStability: Record<string, MethodStability>;
  candidates:      string[];
}

interface HoveredInfo {
  method:    string;
  day:       number;
  winner:    string;
  voteShare: number;
}

// ── Component ─────────────────────────────────────────────────────────────────

const CampaignSwimlane: React.FC<Props> = ({ snapshots, methodStability, candidates }) => {
  const { t } = useTranslation();

  const [selectedCand, setSelectedCand] = useState<string | null>(null);
  const [hovered,      setHovered]      = useState<HoveredInfo | null>(null);
  const [mounted,      setMounted]      = useState(false);

  // Fade-in on first render
  useEffect(() => {
    const id = setTimeout(() => setMounted(true), 40);
    return () => clearTimeout(id);
  }, []);

  // Reset on new data
  useEffect(() => { setSelectedCand(null); setHovered(null); }, [snapshots]);

  // ── Derived values ──────────────────────────────────────────────────────
  const candColorMap = useMemo(
    () => Object.fromEntries(candidates.map((c, i) => [c, CAND_PALETTE[i % CAND_PALETTE.length]])),
    [candidates]
  );

  // Sort methods by stability_score descending (most stable first)
  const sortedMethods = useMemo(
    () =>
      Object.keys(methodStability).sort(
        (a, b) => (methodStability[b]?.stability_score ?? 0) - (methodStability[a]?.stability_score ?? 0)
      ),
    [methodStability]
  );

  // X-axis mapping: day → SVG X coordinate
  const days    = snapshots.map((s) => s.day);
  const maxDay  = days[days.length - 1] || 1;
  const dayToX  = (day: number) => LABEL_W + (PLOT_W * day) / maxDay;

  // SVG total height
  const nMethods = sortedMethods.length;
  const svgH     = MARGIN_TOP + nMethods * (ROW_H + ROW_GAP) - ROW_GAP + MARGIN_BOTTOM;

  // Methods elected by selectedCand
  const methodsForSelected = useMemo(() => {
    if (!selectedCand) return [];
    return sortedMethods.filter(
      (m) => methodStability[m]?.final_winner === selectedCand
    );
  }, [selectedCand, sortedMethods, methodStability]);

  if (snapshots.length === 0 || sortedMethods.length === 0) return null;

  const tickColor  = 'var(--bs-secondary-color, #6c757d)';
  const labelColor = 'var(--bs-body-color, #212529)';

  return (
    <div>
      {/* Click hint */}
      <p className="text-muted mb-1" style={{ fontSize: '0.72rem' }}>
        {t('campaign.swimlaneClickHint')}
      </p>

      {/* ── SVG canvas ── */}
      <div style={{ position: 'relative' }}>
        <svg
          viewBox={`0 0 ${SVG_W} ${svgH}`}
          width="100%"
          style={{ display: 'block', userSelect: 'none', cursor: 'default' }}
          aria-label={t('campaign.swimlaneTitle')}
          onClick={() => setSelectedCand(null)}
        >
          {/* Day-axis ticks */}
          {snapshots.map((s) => {
            const x = dayToX(s.day);
            return (
              <g key={s.day}>
                <line x1={x} y1={MARGIN_TOP - 5} x2={x} y2={MARGIN_TOP - 1}
                  stroke={tickColor} strokeWidth={1} />
                <text x={x} y={MARGIN_TOP - 8} textAnchor="middle"
                  fontSize={9} fill={tickColor}>
                  J{s.day}
                </text>
              </g>
            );
          })}

          {/* Method rows */}
          {sortedMethods.map((method, rowIdx) => {
            const rowY = MARGIN_TOP + rowIdx * (ROW_H + ROW_GAP);

            return (
              <g key={method}>
                {/* Method label */}
                <text
                  x={LABEL_W - 6}
                  y={rowY + ROW_H / 2 + 4}
                  textAnchor="end"
                  fontSize={10}
                  fill={labelColor}
                  data-testid={`swimlane-label-${method}`}
                >
                  {method}
                </text>

                {/* Row background for click-reset */}
                <rect
                  x={LABEL_W} y={rowY}
                  width={PLOT_W} height={ROW_H}
                  fill="transparent"
                  onClick={() => setSelectedCand(null)}
                />

                {/* Winner segments — one per snapshot */}
                {snapshots.map((snap, si) => {
                  const winner = snap.methods[method]?.winner ?? null;
                  if (!winner) return null;

                  const x1  = dayToX(snap.day);
                  const x2  = si < snapshots.length - 1
                    ? dayToX(snapshots[si + 1].day)
                    : LABEL_W + PLOT_W;
                  const w   = Math.max(0, x2 - x1);
                  const clr = candColorMap[winner] ?? '#888';
                  const sel = selectedCand;
                  const opBase = !mounted ? 0 : sel === null ? 1 : sel === winner ? 1 : 0.25;

                  return (
                    <rect
                      key={`${method}-${si}`}
                      x={x1}
                      y={rowY + 2}
                      width={w}
                      height={ROW_H - 4}
                      rx={3}
                      fill={clr}
                      opacity={opBase}
                      style={{ transition: mounted ? 'opacity 0.25s' : 'opacity 0.5s', cursor: 'pointer' }}
                      data-testid={`swimlane-rect-${method}-${si}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedCand(selectedCand === winner ? null : winner);
                      }}
                      onMouseEnter={() => setHovered({
                        method,
                        day:       snap.day,
                        winner,
                        voteShare: snap.methods[method]?.vote_share ?? 0,
                      })}
                      onMouseLeave={() => setHovered(null)}
                    />
                  );
                })}
              </g>
            );
          })}
        </svg>
      </div>

      {/* Hover info */}
      {hovered && (
        <div className="text-muted mt-1" style={{ fontSize: '0.74rem', minHeight: '1.2em' }}>
          <strong>{hovered.method}</strong> — {t('campaign.day')} {hovered.day} :{' '}
          <span style={{ color: candColorMap[hovered.winner] ?? '#888', fontWeight: 600 }}>
            {hovered.winner}
          </span>{' '}
          ({Math.round(hovered.voteShare * 100)}%)
        </div>
      )}

      {/* Candidate legend */}
      <div className="d-flex gap-3 mt-2 flex-wrap" style={{ fontSize: '0.72rem' }}>
        {candidates.map((cand, idx) => (
          <span
            key={cand}
            className="d-flex align-items-center gap-1"
            style={{ cursor: 'pointer', opacity: selectedCand === null || selectedCand === cand ? 1 : 0.4 }}
            onClick={() => setSelectedCand(selectedCand === cand ? null : cand)}
          >
            <span style={{
              width: 10, height: 10, borderRadius: 2,
              background: CAND_PALETTE[idx % CAND_PALETTE.length],
              display: 'inline-block',
            }} />
            {cand}
          </span>
        ))}
      </div>

      {/* Selected candidate panel */}
      {selectedCand && (
        <div className="d-flex align-items-center gap-2 mt-2 flex-wrap" style={{ fontSize: '0.75rem' }}>
          <Badge
            style={{ background: candColorMap[selectedCand], fontSize: '0.72rem' }}
          >
            {selectedCand}
          </Badge>
          {methodsForSelected.length > 0 ? (
            <>
              <span className="text-muted">{t('campaign.swimlaneElectedBy')}:</span>
              {methodsForSelected.map((m) => (
                <Badge key={m} variant="secondary" style={{ fontSize: '0.68rem' }}>{m}</Badge>
              ))}
            </>
          ) : (
            <span className="text-muted">{t('campaign.swimlaneNoFinal')}</span>
          )}
          <span
            className="text-muted"
            style={{ cursor: 'pointer', fontSize: '0.7rem' }}
            onClick={() => setSelectedCand(null)}
          >
            ✕
          </span>
        </div>
      )}
    </div>
  );
};

export default CampaignSwimlane;
