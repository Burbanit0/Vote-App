import React, { useEffect, useState } from 'react';
import { Alert, Badge, Button, Card, Col, Form, Row, Spinner } from 'react-bootstrap';
import { RealElectionResult, RealElectionSummary } from '../../types';
import { analyzeRealElection, getRealElections } from '../../services/simulationCompareApi';
import RealElectionAnalysis from './RealElectionAnalysis';

const RealElectionsTab: React.FC = () => {
  const [elections, setElections] = useState<RealElectionSummary[]>([]);
  const [selected, setSelected] = useState('');
  const [result, setResult] = useState<RealElectionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [blankVote, setBlankVote] = useState(false);
  const [blankLoading, setBlankLoading] = useState(false);

  useEffect(() => {
    getRealElections()
      .then((list) => {
        setElections(list);
        if (list.length > 0) setSelected(list[0].key);
      })
      .catch(() => {});
  }, []);

  const handleAnalyze = async (withBlank = false) => {
    if (!selected) return;
    if (withBlank) {
      setBlankLoading(true);
    } else {
      setLoading(true);
      setBlankVote(false);
    }
    try {
      setResult(await analyzeRealElection(selected, 1000, withBlank));
    } finally {
      setLoading(false);
      setBlankLoading(false);
    }
  };

  const handleToggleBlankVote = async (enabled: boolean) => {
    setBlankVote(enabled);
    if (!result) return; // no analysis yet
    await handleAnalyze(enabled);
  };

  return (
    <Card className="mb-4">
      <Card.Header>
        <strong>Analyse des élections réelles</strong>
        <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
          — quelle méthode aurait élu un vainqueur différent ?
        </span>
      </Card.Header>
      <Card.Body>
        <Row className="g-3 align-items-end mb-4">
          <Col md={5}>
            <Form.Label className="small mb-1">Élection</Form.Label>
            <Form.Select
              size="sm"
              value={selected}
              onChange={(e) => { setSelected(e.target.value); setResult(null); setBlankVote(false); }}
            >
              {elections.length === 0 && <option value="">Chargement…</option>}
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
              onClick={() => handleAnalyze(false)}
              disabled={loading || !selected}
            >
              {loading ? <><Spinner size="sm" className="me-2" />Analyse…</> : 'Analyser'}
            </Button>
          </Col>
        </Row>

        {result ? (
          <RealElectionAnalysis
            result={result}
            blankVoteEnabled={blankVote}
            blankLoading={blankLoading}
            onToggleBlankVote={handleToggleBlankVote}
          />
        ) : (
          !loading && (
            <Alert variant="info" className="mb-0">
              Sélectionnez une élection ci-dessus et cliquez sur <strong>Analyser</strong>.
            </Alert>
          )
        )}
      </Card.Body>
    </Card>
  );
};

export default RealElectionsTab;
