import React, { useMemo } from 'react';
import { Card, CardBody } from '@/components/ui/card';
import { Range } from '@/components/ui/form-controls';
import { Col, Row } from '@/components/ui/grid';
import { Area, AreaChart, ResponsiveContainer, XAxis } from 'recharts';
import { Trans, useTranslation } from 'react-i18next';

export interface ElectorateState {
  numVoters: number;
  ideologyPreset: 'polarized' | 'centrist' | 'left' | 'right' | 'random';
  dissatisfactionRate: number; // [0, 1]
}

const BEGINNER_PRESETS: ElectorateState['ideologyPreset'][] = ['polarized', 'centrist', 'random'];

interface Props {
  config: ElectorateState;
  onChange: (patch: Partial<ElectorateState>) => void;
  expertMode?: boolean;
}

// ── Distribution curve data ────────────────────────────────────────────────

function normalPDF(x: number, mean: number, std: number): number {
  return Math.exp(-0.5 * ((x - mean) / std) ** 2) / (std * Math.sqrt(2 * Math.PI));
}

const N = 41;
const xs = Array.from({ length: N }, (_, i) => -1 + i * 0.05);

function makeCurve(fn: (x: number) => number) {
  const raw = xs.map(fn);
  const max = Math.max(...raw);
  return xs.map((x, i) => ({ x: x.toFixed(2), y: max > 0 ? raw[i] / max : 0.5 }));
}

// ── Component ──────────────────────────────────────────────────────────────

const ElectorateConfig: React.FC<Props> = ({ config, onChange, expertMode = false }) => {
  const { t } = useTranslation();

  const PRESETS = useMemo(() => {
    const presets = {
      polarized: {
        color: '#e15759',
        label: t('ideology.polarized'),
        desc: t('ideology.polarizedDesc'),
        data: makeCurve((x) => normalPDF(x, -0.65, 0.2) + normalPDF(x, 0.65, 0.2)),
      },
      centrist: {
        color: '#59a14f',
        label: t('ideology.centrist'),
        desc: t('ideology.centristDesc'),
        data: makeCurve((x) => normalPDF(x, 0, 0.25)),
      },
      left: {
        color: '#4e79a7',
        label: t('ideology.left'),
        desc: t('ideology.leftDesc'),
        data: makeCurve((x) => normalPDF(x, -0.35, 0.3)),
      },
      right: {
        color: '#f28e2b',
        label: t('ideology.right'),
        desc: t('ideology.rightDesc'),
        data: makeCurve((x) => normalPDF(x, 0.35, 0.3)),
      },
      random: {
        color: '#76b7b2',
        label: t('ideology.random'),
        desc: t('ideology.randomDesc'),
        data: makeCurve(() => 1),
      },
    } as const;
    return presets;
  }, [t]);

  const visiblePresetKeys = expertMode
    ? (Object.keys(PRESETS) as ElectorateState['ideologyPreset'][])
    : BEGINNER_PRESETS;

  const dissatisfactionLabel = useMemo(() => {
    const pct = Math.round(config.dissatisfactionRate * 100);
    if (pct < 15) return t('scenario.dissatisfactionLabels.satisfied', { pct });
    if (pct < 40) return t('scenario.dissatisfactionLabels.moderate', { pct });
    if (pct < 65) return t('scenario.dissatisfactionLabels.high', { pct });
    return t('scenario.dissatisfactionLabels.crisis', { pct });
  }, [config.dissatisfactionRate, t]);

  return (
    <div>
      <p className="text-muted small mb-3">
        {t('scenario.electorateIntro')}
      </p>

      {/* Voter count */}
      <Card className="mb-4">
        <CardBody>
          <label className="mb-1 inline-block">
            {t('scenario.numVoters', { n: config.numVoters.toLocaleString() })}
          </label>
          <Range
            min={100} max={10000} step={100} value={config.numVoters}
            onChange={(e) => onChange({ numVoters: Number(e.target.value) })}
          />
          <div className="d-flex justify-content-between">
            <small className="text-muted">100</small>
            <small className="text-muted">{t('scenario.voterRangeMax')}</small>
          </div>
        </CardBody>
      </Card>

      {/* Ideology preset */}
      <p className="fw-semibold mb-2">{t('scenario.ideologyDistribution')}</p>
      <Row className="g-2 mb-4">
        {(Object.entries(PRESETS) as [ElectorateState['ideologyPreset'], typeof PRESETS[keyof typeof PRESETS]][]).filter(([key]) => visiblePresetKeys.includes(key)).map(([key, preset]) => (
          <Col xs={6} md={4} key={key}>
            <Card
              className={`h-100 ${config.ideologyPreset === key ? 'border-primary' : ''}`}
              style={{ cursor: 'pointer', transition: 'border-color 0.15s' }}
              onClick={() => onChange({ ideologyPreset: key })}
            >
              <CardBody className="p-2">
                <div className="d-flex align-items-center gap-1 mb-1">
                  {config.ideologyPreset === key && (
                    <span style={{ color: preset.color, fontWeight: 700 }}>●</span>
                  )}
                  <small className="fw-semibold">{preset.label}</small>
                </div>
                <ResponsiveContainer width="100%" height={50}>
                  <AreaChart data={preset.data} margin={{ top: 2, right: 2, bottom: 0, left: 2 }}>
                    <XAxis dataKey="x" hide />
                    <Area
                      type="monotone" dataKey="y"
                      stroke={preset.color}
                      fill={preset.color}
                      fillOpacity={config.ideologyPreset === key ? 0.4 : 0.15}
                      strokeWidth={config.ideologyPreset === key ? 2 : 1}
                      dot={false} isAnimationActive={false}
                    />
                  </AreaChart>
                </ResponsiveContainer>
                <div className="d-flex justify-content-between mt-1">
                  <small style={{ fontSize: '0.65rem', color: '#6c757d' }}>{t('scenario.leftShort')}</small>
                  <small style={{ fontSize: '0.65rem', color: '#6c757d' }}>{t('scenario.rightShort')}</small>
                </div>
                <small className="text-muted d-block mt-1" style={{ fontSize: '0.72rem' }}>{preset.desc}</small>
              </CardBody>
            </Card>
          </Col>
        ))}
      </Row>

      {/* Dissatisfaction rate — expert only */}
      {!expertMode && (
        <small className="text-muted d-block mb-3">
          <Trans i18nKey="scenario.expertModeHint" />
        </small>
      )}
      <Card style={expertMode ? undefined : { display: 'none' }}>
        <CardBody>
          <label className="mb-1 inline-block">
            {t('scenario.dissatisfactionRate')}
            <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
              {t('scenario.dissatisfactionSubtitle')}
            </span>
          </label>
          <Range
            min={0} max={1} step={0.05} value={config.dissatisfactionRate}
            onChange={(e) => onChange({ dissatisfactionRate: Number(e.target.value) })}
          />
          <small className="text-muted">{dissatisfactionLabel}</small>
          <div className="mt-2">
            <small className="text-info">
              {t('scenario.dissatisfactionHint')}
            </small>
          </div>
        </CardBody>
      </Card>
    </div>
  );
};

export default ElectorateConfig;
