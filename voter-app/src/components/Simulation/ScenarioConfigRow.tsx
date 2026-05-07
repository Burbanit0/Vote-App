import React from 'react';
import { Col, Form, Row } from 'react-bootstrap';
import { IDEOLOGY_OPTIONS, ScenarioConfig } from './simulationConstants';

interface Props {
  config: ScenarioConfig;
  onChange: (patch: Partial<ScenarioConfig>) => void;
  label?: string;
}

const ScenarioConfigRow: React.FC<Props> = ({ config, onChange, label }) => (
  <Row className="g-2 align-items-end">
    {label && (
      <Col xs={12}>
        <span className="fw-semibold text-muted small">{label}</span>
      </Col>
    )}
    <Col md={4}>
      <Form.Label className="small mb-1">Candidates (comma-separated)</Form.Label>
      <Form.Control
        size="sm"
        type="text"
        value={config.candidateInput}
        onChange={(e) => onChange({ candidateInput: e.target.value })}
        placeholder="Alice, Bob, Charlie"
      />
    </Col>
    <Col md={3}>
      <Form.Label className="small mb-1">Voters</Form.Label>
      <Form.Control
        size="sm"
        type="number"
        min={100}
        max={2000}
        step={100}
        value={config.numVoters}
        onChange={(e) => onChange({ numVoters: Number(e.target.value) })}
      />
    </Col>
    <Col md={3}>
      <Form.Label className="small mb-1">Electorate distribution</Form.Label>
      <Form.Select
        size="sm"
        value={config.ideology_distribution}
        onChange={(e) => onChange({ ideology_distribution: e.target.value })}
      >
        {IDEOLOGY_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </Form.Select>
    </Col>
  </Row>
);

export default ScenarioConfigRow;
