/**
 * PoliticalClusterMap — Pol.is-style consensus clustering visualisation.
 * Shows participants in 2D PCA space, coloured by opinion cluster.
 * Highlights consensus and polarising statements.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Badge } from 'react-bootstrap';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface PolisCluster {
  id:    number;
  size:  number;
  votes: Record<string, number>;
}

export interface PolisData {
  clusters:              PolisCluster[];
  consensus_statements:  { statement: string; approval_rate: number }[];
  polarizing_statements: { statement: string; cluster_delta: number }[];
  participant_positions: { id: number; x_pca: number; y_pca: number; cluster_id: number }[];
  num_clusters:          number;
  num_participants:      number;
}

// ── Palette ───────────────────────────────────────────────────────────────────

const CLUSTER_COLORS = ['#005CAB', '#C8590A', '#007A33', '#9b59b6', '#e67e22'];
function clusterColor(id: number): string {
  return CLUSTER_COLORS[id % CLUSTER_COLORS.length];
}

// ── PCA Scatter ───────────────────────────────────────────────────────────────

const SCATTER_W = 480, SCATTER_H = 320, SCATTER_PAD = 24;

interface ScatterProps {
  positions: PolisData['participant_positions'];
}

const PolisScatter: React.FC<ScatterProps> = ({ positions }) => {
  if (!positions.length) return null;

  const xs   = positions.map((p) => p.x_pca);
  const ys   = positions.map((p) => p.y_pca);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const spanX = (maxX - minX) || 1, spanY = (maxY - minY) || 1;

  const px = (x: number) =>
    SCATTER_PAD + ((x - minX) / spanX) * (SCATTER_W - 2 * SCATTER_PAD);
  const py = (y: number) =>
    SCATTER_H - SCATTER_PAD - ((y - minY) / spanY) * (SCATTER_H - 2 * SCATTER_PAD);

  // Sample up to 200 dots for performance
  const sample = positions.length > 200
    ? positions.filter((_, i) => i % Math.ceil(positions.length / 200) === 0)
    : positions;

  return (
    <svg
      data-testid="polis-scatter-svg"
      width="100%"
      viewBox={`0 0 ${SCATTER_W} ${SCATTER_H}`}
      style={{ display: 'block' }}
    >
      {sample.map((p) => (
        <circle
          key={p.id}
          cx={px(p.x_pca)}
          cy={py(p.y_pca)}
          r={3.5}
          fill={clusterColor(p.cluster_id)}
          opacity={0.7}
        />
      ))}
    </svg>
  );
};

// ── Main component ────────────────────────────────────────────────────────────

interface Props {
  data: PolisData;
}

const PoliticalClusterMap: React.FC<Props> = ({ data }) => {
  const { t } = useTranslation();

  const allStmts = data.clusters[0] ? Object.keys(data.clusters[0].votes) : [];

  return (
    <div>
      {/* Legend */}
      <div className="d-flex gap-2 flex-wrap mb-2">
        {data.clusters.map((c) => (
          <Badge key={c.id} style={{ background: clusterColor(c.id), fontSize: '0.75rem' }}>
            {t('tech.polisCluster')} {c.id + 1} — {c.size} {t('tech.participants')}
          </Badge>
        ))}
      </div>

      {/* PCA scatter */}
      <div className="border rounded mb-3" style={{ background: '#f8f9fa', overflow: 'hidden' }}>
        <PolisScatter positions={data.participant_positions} />
      </div>

      {/* Consensus statements */}
      {data.consensus_statements.length > 0 && (
        <div
          className="border border-success rounded p-3 mb-3"
          data-testid="consensus-section"
        >
          <div className="fw-semibold mb-2" style={{ color: '#198754', fontSize: '0.85rem' }}>
            ✅ {t('tech.consensusTitle')}
          </div>
          <div className="text-muted mb-2" style={{ fontSize: '0.75rem' }}>
            {t('tech.consensusDesc')}
          </div>
          {data.consensus_statements.map((s, i) => (
            <div key={i} className="d-flex align-items-center gap-2 mb-1">
              <div
                style={{
                  width: `${Math.round(s.approval_rate * 100)}%`,
                  minWidth: 40, height: 6,
                  background: '#198754', borderRadius: 3,
                }}
              />
              <span style={{ fontSize: '0.78rem', color: '#198754', fontWeight: 600 }}>
                {Math.round(s.approval_rate * 100)}%
              </span>
              <span style={{ fontSize: '0.78rem' }}>{s.statement}</span>
            </div>
          ))}
        </div>
      )}

      {/* Polarising statements */}
      {data.polarizing_statements.length > 0 && (
        <div
          className="border border-danger rounded p-3 mb-3"
          data-testid="polarizing-section"
        >
          <div className="fw-semibold mb-2" style={{ color: '#dc3545', fontSize: '0.85rem' }}>
            ⚡ {t('tech.polarizingTitle')}
          </div>
          {data.polarizing_statements.map((s, i) => (
            <div key={i} className="d-flex align-items-center gap-2 mb-1">
              <Badge bg="danger" style={{ fontSize: '0.65rem' }}>
                Δ {Math.round(s.cluster_delta * 100)}%
              </Badge>
              <span style={{ fontSize: '0.78rem' }}>{s.statement}</span>
            </div>
          ))}
        </div>
      )}

      {/* Per-statement approval by cluster */}
      {allStmts.length > 0 && data.clusters.length > 0 && (
        <div data-testid="cluster-vote-table">
          <div className="fw-semibold mb-2" style={{ fontSize: '0.85rem' }}>
            {t('tech.clusterVoteTable')}
          </div>
          {allStmts.slice(0, 8).map((stmt, si) => (
            <div key={si} className="mb-2">
              <div style={{ fontSize: '0.72rem', color: '#6c757d', marginBottom: 2 }}>
                {stmt.length > 70 ? stmt.slice(0, 68) + '…' : stmt}
              </div>
              <div className="d-flex gap-1">
                {data.clusters.map((c) => {
                  const rate = c.votes[stmt] ?? 0;
                  return (
                    <div key={c.id} title={`${t('tech.polisCluster')} ${c.id + 1}: ${Math.round(rate * 100)}%`}
                      style={{
                        width: `${Math.round(rate * 100)}%`,
                        minWidth: 4, height: 8,
                        background: clusterColor(c.id),
                        borderRadius: 2, transition: 'width 0.3s',
                      }}
                    />
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default PoliticalClusterMap;
