import React, { useEffect, useState } from 'react';
import { Alert, Button, Card, Col, Form, Row, Spinner, Tab, Tabs } from 'react-bootstrap';
import { Trans, useTranslation } from 'react-i18next';
import { RealElectionResult, RealElectionSummary } from '../../types';
import { analyzeRealElection, getRealElections } from '../../services/simulationCompareApi';
import RealElectionAnalysis from './RealElectionAnalysis';
import BlankVoteTimeSeries from '../research/BlankVoteTimeSeries';

const RealElectionsTab: React.FC = () => {
  const { t } = useTranslation();
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
    if (!result) return;
    await handleAnalyze(enabled);
  };

  return (
    <Card className="mb-4">
      <Card.Header>
        <strong>{t('simulation.realElections.title')}</strong>
        <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
          {t('simulation.realElections.subtitle')}
        </span>
      </Card.Header>
      <Card.Body>
        <Tabs defaultActiveKey="analysis" className="mb-3">
          {/* ── Tab 1: Election analysis ── */}
          <Tab eventKey="analysis" title="Analyse de l'élection">
            <Row className="g-3 align-items-end mb-4">
              <Col md={5}>
                <Form.Label htmlFor="real-election-select" className="small mb-1">
                  {t('simulation.realElections.electionLabel')}
                </Form.Label>
                <Form.Select
                  id="real-election-select"
                  size="sm"
                  value={selected}
                  onChange={(e) => { setSelected(e.target.value); setResult(null); setBlankVote(false); }}
                >
                  {elections.length === 0 && (
                    <option value="">{t('simulation.realElections.loadingOption')}</option>
                  )}
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
                  {loading
                    ? <><Spinner size="sm" className="me-2" />{t('simulation.realElections.analyzing')}</>
                    : t('simulation.realElections.analyze')}
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
                  <Trans i18nKey="simulation.realElections.prompt" />
                </Alert>
              )
            )}
          </Tab>

          {/* ── Tab 2: Time series ── */}
          <Tab
            eventKey="timeseries"
            title={
              <span>
                📈 Évolution historique
              </span>
            }
          >
            <BlankVoteTimeSeries />
          </Tab>
        </Tabs>
      </Card.Body>
    </Card>
  );
};

export default RealElectionsTab;
