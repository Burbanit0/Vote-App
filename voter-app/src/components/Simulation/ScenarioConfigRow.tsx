import React from 'react';
import { Control, Select } from '@/components/ui/form-controls';
import { Col, Row } from '@/components/ui/grid';
import { IDEOLOGY_OPTIONS, ScenarioConfig } from './simulationConstants';
import { useTranslation } from 'react-i18next';

interface Props {
  config: ScenarioConfig;
  onChange: (patch: Partial<ScenarioConfig>) => void;
  /** Optional visible label for side-by-side scenario comparison (A / B). */
  label?: string;
  /** DOM id prefix — use distinct values when two rows appear on the same page. */
  idPrefix?: string;
}

const ScenarioConfigRow: React.FC<Props> = ({
  config,
  onChange,
  label,
  idPrefix = 'scenario',
}) => {
  const { t } = useTranslation();

  const candidatesId   = `${idPrefix}-candidates`;
  const votersId       = `${idPrefix}-voters`;
  const distributionId = `${idPrefix}-distribution`;

  return (
    <Row className="g-2 align-items-end">
      {label && (
        <Col xs={12}>
          <span className="fw-semibold text-muted small">{label}</span>
        </Col>
      )}
      <Col md={4}>
        <label htmlFor={candidatesId} className="mb-1 inline-block small mb-1">
          {t('simulation.candidatesLabel', { defaultValue: 'Candidates (comma-separated)' })}
        </label>
        <Control
          id={candidatesId}
          size="sm"
          type="text"
          value={config.candidateInput}
          onChange={(e) => onChange({ candidateInput: e.target.value })}
          placeholder="Alice, Bob, Charlie"
        />
      </Col>
      <Col md={3}>
        <label htmlFor={votersId} className="mb-1 inline-block small mb-1">
          {t('simulation.votersLabel', { defaultValue: 'Voters' })}
        </label>
        <Control
          id={votersId}
          size="sm"
          type="number"
          min={100}
          max={2000}
          step={100}
          value={config.numVoters}
          onChange={(e) => onChange({ numVoters: Number(e.target.value) })}
          aria-describedby={`${votersId}-hint`}
        />
        <small className="block text-sm text-muted-foreground" id={`${votersId}-hint`}>
          100 – 2 000
        </small>
      </Col>
      <Col md={3}>
        <label htmlFor={distributionId} className="mb-1 inline-block small mb-1">
          {t('simulation.distributionLabel', { defaultValue: 'Electorate distribution' })}
        </label>
        <Select
          id={distributionId}
          size="sm"
          value={config.ideology_distribution}
          onChange={(e) => onChange({ ideology_distribution: e.target.value })}
        >
          {IDEOLOGY_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {t(o.labelKey)}
            </option>
          ))}
        </Select>
      </Col>
    </Row>
  );
};

export default ScenarioConfigRow;
