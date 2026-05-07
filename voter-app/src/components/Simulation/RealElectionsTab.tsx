import React, { useEffect, useState } from 'react';
import { Alert, Button, Card, Col, Form, Row, Spinner } from 'react-bootstrap';
import { RealElectionResult, RealElectionSummary } from '../../types';
import { analyzeRealElection, getRealElections } from '../../services/simulationCompareApi';
import RealElectionAnalysis from './RealElectionAnalysis';

const RealElectionsTab: React.FC = () => {
  const [elections, setElections] = useState<RealElectionSummary[]>([]);
  const [selected, setSelected] = useState('');
  const [result, setResult] = useState<RealElectionResult | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getRealElections()
      .then((list) => {
        setElections(list);
        if (list.length > 0) setSelected(list[0].key);
      })
      .catch(() => {});
  }, []);

  const handleAnalyze = async () => {
    if (!selected) return;
    setLoading(true);
    try {
      setResult(await analyzeRealElection(selected, 1000));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="mb-4">
      <Card.Header>
        <strong>Real Election Analysis</strong>
        <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
          — what would each method have elected from real first-round results?
        </span>
      </Card.Header>
      <Card.Body>
        <Row className="g-3 align-items-end mb-4">
          <Col md={5}>
            <Form.Label className="small mb-1">Election</Form.Label>
            <Form.Select
              size="sm"
              value={selected}
              onChange={(e) => { setSelected(e.target.value); setResult(null); }}
            >
              {elections.length === 0 && <option value="">Loading…</option>}
              {elections.map((e) => (
                <option key={e.key} value={e.key}>
                  {e.country} — {e.name} ({e.year})
                </option>
              ))}
            </Form.Select>
          </Col>
          <Col md={2}>
            <Button
              variant="primary" size="sm" className="w-100"
              onClick={handleAnalyze}
              disabled={loading || !selected}
            >
              {loading ? <><Spinner size="sm" className="me-2" />Running…</> : 'Analyse'}
            </Button>
          </Col>
        </Row>
        {result ? (
          <RealElectionAnalysis result={result} />
        ) : (
          !loading && (
            <Alert variant="info" className="mb-0">
              Select an election above and click <strong>Analyse</strong>.
            </Alert>
          )
        )}
      </Card.Body>
    </Card>
  );
};

export default RealElectionsTab;
