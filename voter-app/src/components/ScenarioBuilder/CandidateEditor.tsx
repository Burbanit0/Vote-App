import React, { useMemo } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardBody } from '@/components/ui/card';
import { Control, Range } from '@/components/ui/form-controls';
import { Col, Row } from '@/components/ui/grid';
import { useTranslation } from 'react-i18next';

export interface CandidateConfig {
  id: string;
  name: string;
  ideology: number;   // [-1, 1]
  economy: number;    // [0, 1]
  environment: number;
  social: number;
  isBlank: boolean;
}

interface Props {
  candidates: CandidateConfig[];
  onChange: (candidates: CandidateConfig[]) => void;
}

let _idCounter = 0;
export function newCandidate(name = '', ideology = 0): CandidateConfig {
  const pos = (ideology + 1) / 2;
  return {
    id: `c${++_idCounter}`,
    name,
    ideology,
    economy:     Math.round(pos * 100) / 100,
    environment: Math.round((1 - pos) * 100) / 100,
    social:      Math.round((1 - pos) * 100) / 100,
    isBlank: false,
  };
}

export function newBlankCandidate(): CandidateConfig {
  return { id: `blank${++_idCounter}`, name: 'Vote Blanc', ideology: 0, economy: 0.5, environment: 0.5, social: 0.5, isBlank: true };
}

const CandidateEditor: React.FC<Props> = ({ candidates, onChange }) => {
  const { t } = useTranslation();
  const hasBlank = candidates.some((c) => c.isBlank);

  const IDEOLOGY_LABELS = useMemo(() => [
    t('ideology.extremeLeft'),
    t('ideology.left'),
    t('ideology.centerLeft'),
    t('ideology.center'),
    t('ideology.centerRight'),
    t('ideology.right'),
    t('ideology.extremeRight'),
  ], [t]);

  function ideologyLabel(v: number): string {
    const idx = Math.round((v + 1) / 2 * (IDEOLOGY_LABELS.length - 1));
    return IDEOLOGY_LABELS[Math.max(0, Math.min(IDEOLOGY_LABELS.length - 1, idx))];
  }

  function ideologyColor(v: number): string {
    const t = (v + 1) / 2;
    const r = Math.round(220 * t);
    const b = Math.round(220 * (1 - t));
    return `rgb(${r},60,${b})`;
  }

  const update = (id: string, patch: Partial<CandidateConfig>) => {
    onChange(candidates.map((c) => (c.id === id ? { ...c, ...patch } : c)));
  };

  const onIdeologyChange = (id: string, val: number) => {
    const pos = (val + 1) / 2;
    update(id, {
      ideology:    val,
      economy:     Math.round(pos * 100) / 100,
      environment: Math.round((1 - pos) * 100) / 100,
      social:      Math.round((1 - pos) * 100) / 100,
    });
  };

  const remove = (id: string) => onChange(candidates.filter((c) => c.id !== id));

  const Slider = ({ label, value, onChange: onSliderChange }: { label: string; value: number; onChange: (v: number) => void }) => (
    <div className="mb-2">
      <div className="d-flex justify-content-between mb-1">
        <small className="text-muted">{label}</small>
        <small className="fw-semibold">{Math.round(value * 100)}%</small>
      </div>
      <Range min={0} max={1} step={0.05} value={value} onChange={(e) => onSliderChange(Number(e.target.value))} />
    </div>
  );

  return (
    <div>
      <p className="text-muted small mb-3">
        {t('scenario.candidateEditorIntro')}
      </p>

      {candidates.map((c) => (
        <Card key={c.id} className={`mb-3 ${c.isBlank ? 'border-warning' : ''}`}>
          <CardBody>
            {c.isBlank ? (
              <div className="d-flex align-items-center justify-content-between">
                <div className="d-flex align-items-center gap-2">
                  <Badge variant="warning" style={{ fontSize: '0.85rem' }}>{t('scenario.blankVoteBadge')}</Badge>
                  <small className="text-muted">{t('scenario.blankDescription')}</small>
                </div>
                <Button variant="outline-danger" size="sm" onClick={() => remove(c.id)}>✕</Button>
              </div>
            ) : (
              <>
                <Row className="g-2 align-items-center mb-3">
                  <Col md={5}>
                    <Control
                      size="sm"
                      placeholder={t('scenario.candidateNamePlaceholder')}
                      value={c.name}
                      onChange={(e) => update(c.id, { name: e.target.value })}
                    />
                  </Col>
                  <Col md={6}>
                    <div className="d-flex align-items-center gap-2">
                      <small className="text-nowrap" style={{ color: '#3c3cdc', minWidth: 50 }}>{t('scenario.left')}</small>
                      <Range
                        min={-1} max={1} step={0.05} value={c.ideology}
                        onChange={(e) => onIdeologyChange(c.id, Number(e.target.value))}
                      />
                      <small className="text-nowrap" style={{ color: '#dc3c3c', minWidth: 50, textAlign: 'right' }}>{t('scenario.right')}</small>
                    </div>
                    <div className="text-center mt-1">
                      <Badge style={{ backgroundColor: ideologyColor(c.ideology), fontSize: '0.72rem' }}>
                        {ideologyLabel(c.ideology)}
                      </Badge>
                    </div>
                  </Col>
                  <Col md={1} className="text-end">
                    <Button variant="outline-danger" size="sm" onClick={() => remove(c.id)}>✕</Button>
                  </Col>
                </Row>

                <Row className="g-3">
                  <Col md={4}>
                    <Slider label={t('scenario.economySlider')} value={c.economy} onChange={(v) => update(c.id, { economy: v })} />
                  </Col>
                  <Col md={4}>
                    <Slider label={t('scenario.environmentSlider')} value={c.environment} onChange={(v) => update(c.id, { environment: v })} />
                  </Col>
                  <Col md={4}>
                    <Slider label={t('scenario.socialSlider')} value={c.social} onChange={(v) => update(c.id, { social: v })} />
                  </Col>
                </Row>
              </>
            )}
          </CardBody>
        </Card>
      ))}

      <div className="d-flex gap-2">
        <Button variant="outline-primary" size="sm" onClick={() => onChange([...candidates, newCandidate()])}>
          {t('scenario.addCandidate')}
        </Button>
        {!hasBlank && (
          <Button variant="outline-warning" size="sm" onClick={() => onChange([...candidates, newBlankCandidate()])}>
            {t('scenario.addBlank')}
          </Button>
        )}
      </div>
    </div>
  );
};

export default CandidateEditor;
