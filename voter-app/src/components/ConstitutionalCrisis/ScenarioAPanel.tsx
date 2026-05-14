import React, { useState } from 'react';
import { Alert, Badge, Button, Card, Spinner, Table } from 'react-bootstrap';
import { useTranslation } from 'react-i18next';
import CandidateEditor, { CandidateConfig } from '../ScenarioBuilder/CandidateEditor';
import { ConstitutionalResult, ScenarioMethodResult } from '../../services/simulationCompareApi';

const COLORS = ['#4e79a7', '#e15759', '#59a14f', '#f28e2b', '#76b7b2', '#edc948'];

interface Props {
  initialCandidates: CandidateConfig[];
  result: ConstitutionalResult | null;
  loading: boolean;
  onRun: (round2Candidates: CandidateConfig[]) => void;
}

function WinnerBadge({ winner, colorMap }: { winner: string | null; colorMap: Record<string, string> }) {
  const { t } = useTranslation();
  if (!winner) return <span className="text-muted">—</span>;
  if (winner === 'Blank') return <Badge bg="warning" text="dark">{t('common.blankBadge')}</Badge>;
  return <Badge style={{ backgroundColor: colorMap[winner] ?? '#999', fontSize: '0.75rem' }}>{winner}</Badge>;
}

const ScenarioAPanel: React.FC<Props> = ({ initialCandidates, result, loading, onRun }) => {
  const { t } = useTranslation();
  const realInitial = initialCandidates.filter((c) => !c.isBlank);
  const [round2Candidates, setRound2Candidates] = useState<CandidateConfig[]>(
    realInitial.map((c) => ({ ...c }))
  );

  const colorMap: Record<string, string> = Object.fromEntries(
    [...realInitial, ...round2Candidates.filter((c) => !c.isBlank)].map((c, i) => [c.name, COLORS[i % COLORS.length]])
  );

  // Candidates from round 1 who must change position (> 0.08 move required)
  const disqualified = new Set(realInitial.map((c) => c.name));
  const moved = new Set(
    round2Candidates
      .filter((c) => !c.isBlank)
      .filter((c2) => {
        const c1 = realInitial.find((c) => c.name === c2.name);
        return !c1 || Math.abs(c1.ideology - c2.ideology) >= 0.08;
      })
      .map((c) => c.name)
  );
  const stillBlocked = round2Candidates
    .filter((c) => !c.isBlank && disqualified.has(c.name) && !moved.has(c.name))
    .map((c) => c.name);

  const canRun = round2Candidates.filter((c) => !c.isBlank).length >= 2 && stillBlocked.length === 0;

  const methods = result ? Object.keys(result.round1?.methods ?? {}) : [];

  return (
    <div>
      <p className="text-muted small mb-3" dangerouslySetInnerHTML={{ __html: t('crisis.scenarioADesc') }} />

      {/* Round 2 candidate editor */}
      <Card className="mb-3">
        <Card.Header className="fw-semibold">
          {t('crisis.scenarioAEditors')}
          {stillBlocked.length > 0 && (
            <Badge bg="danger" className="ms-2">{t('crisis.scenarioABlocked', { count: stillBlocked.length })}</Badge>
          )}
        </Card.Header>
        <Card.Body>
          {stillBlocked.length > 0 && (
            <Alert variant="warning" className="py-2 mb-3" style={{ fontSize: '0.85rem' }}>
              {t('crisis.scenarioAAlert', { names: stillBlocked.join(', '), must: stillBlocked.length > 1 ? 'ils doivent' : 'il doit' })}
            </Alert>
          )}
          <CandidateEditor candidates={round2Candidates} onChange={setRound2Candidates} />
        </Card.Body>
      </Card>

      <div className="mb-4">
        <Button variant="success" onClick={() => onRun(round2Candidates)} disabled={loading || !canRun}>
          {loading ? <><Spinner size="sm" className="me-2" />{t('crisis.simulating')}</> : t('crisis.runRound2')}
        </Button>
        {!canRun && stillBlocked.length > 0 && (
          <small className="text-danger ms-3">{t('crisis.scenarioAHint')}</small>
        )}
      </div>

      {/* Results comparison */}
      {result?.round1 && result?.round2 && (
        <>
          <Table bordered size="sm" className="mb-3">
            <thead className="table-light">
              <tr>
                <th style={{ minWidth: 160 }}>{t('common.method')}</th>
                <th className="text-center">{t('crisis.round1')}</th>
                <th className="text-center">{t('crisis.round2')}</th>
                <th className="text-center">{t('common.changed')}</th>
              </tr>
            </thead>
            <tbody>
              {methods.map((m) => {
                const w1 = (result.round1!.methods[m] as ScenarioMethodResult)?.blank_rule_applied?.winner ?? result.round1!.methods[m]?.winner ?? null;
                const w2 = (result.round2!.methods[m] as ScenarioMethodResult)?.blank_rule_applied?.winner ?? result.round2!.methods[m]?.winner ?? null;
                const changed = w1 !== w2;
                return (
                  <tr key={m} style={changed ? { backgroundColor: '#e8f4e8' } : undefined}>
                    <td className="ps-2 fw-semibold">{t(`methods.${m}.label`)}</td>
                    <td className="text-center"><WinnerBadge winner={w1} colorMap={colorMap} /></td>
                    <td className="text-center"><WinnerBadge winner={w2} colorMap={colorMap} /></td>
                    <td className="text-center">
                      {changed ? <span style={{ color: '#198754' }}>{t('crisis.newWinner')}</span> : <span className="text-muted">{t('crisis.same')}</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </Table>

          <Card className="border-0" style={{ backgroundColor: '#f8f9fa' }}>
            <Card.Body>
              <small className="fw-semibold">{t('crisis.analysis')}</small>
              <p className="mb-0 mt-1 text-muted" style={{ fontSize: '0.85rem' }}>{result.conclusion}</p>
            </Card.Body>
          </Card>
        </>
      )}
    </div>
  );
};

export default ScenarioAPanel;
