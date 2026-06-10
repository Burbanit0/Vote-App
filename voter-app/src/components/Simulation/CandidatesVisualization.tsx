import React, { useState } from 'react';
import { Alert } from '@/components/ui/alert';
import { Tab, Tabs } from '@/components/ui/bootstrap-tabs';
import { Button } from '@/components/ui/button';
import { Card, CardBody, CardHeader, CardTitle } from '@/components/ui/card';
import { Control } from '@/components/ui/form-controls';
import { Col, Container, Row } from '@/components/ui/grid';
import { Modal } from '@/components/ui/modal';
import { Spinner } from '@/components/ui/spinner';
import { Table } from '@/components/ui/table';
import { useTranslation } from 'react-i18next';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Cell,
} from 'recharts';
import { simulateCandidates } from '../../services';
import { CandidateSimu } from '../../types';
import { useSimulation } from '../../stores/useSimuStore';

const COLORS = [
  '#0088FE',
  '#00C49F',
  '#FFBB28',
  '#FF8042',
  '#8884D8',
  '#A4DE6C',
  '#D0ED57',
  '#FF6B6B',
  '#AA96DA',
  '#FF9FF3',
];

const CandidatesVisualization: React.FC = () => {
  const { t } = useTranslation();
  // State
  const { candidates, setCandidates, issues, setIssues } = useSimulation();
  const [numCandidates, setNumCandidates] = useState<number>(4);
  const [parties, setParties] = useState<string[]>([
    'Green',
    'Conservative',
    'Liberal',
    'Independent',
  ]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [showCandidateModal, setShowCandidateModal] = useState<boolean>(false);
  const [selectedCandidate, setSelectedCandidate] = useState<CandidateSimu | null>(null);
  const [activeTab, setActiveTab] = useState<string>('summary');

  // Fetch candidates
  const fetchCandidates = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await simulateCandidates(numCandidates, issues, parties);
      setCandidates(response.candidates);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch candidates');
      console.error('Error fetching candidates:', err);
    } finally {
      setLoading(false);
    }
  };

  // Handle form submission
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchCandidates();
  };

  // Prepare data for charts
  const preparePolicyData = () => {
    if (candidates.length === 0) return [];

    const policyAverages: Record<string, number> = {};
    issues.forEach((issue) => {
      policyAverages[issue] =
        candidates.reduce((sum, candidate) => sum + (candidate.policies[issue] || 0), 0) /
        candidates.length;
    });

    return Object.entries(policyAverages)
      .map(([issue, value]) => ({
        name: issue.replace('_', ' '),
        value: value * 100, // Convert to percentage
      }))
      .sort((a, b) => b.value - a.value);
  };

  const prepareCandidateComparison = () => {
    return candidates.map((candidate) => {
      const policyValues: Record<string, number> = {};
      issues.forEach((issue) => {
        policyValues[issue] = (candidate.policies[issue] || 0) * 100;
      });
      return {
        name: candidate.name,
        ...policyValues,
        charisma: candidate.charisma * 100,
        popularity: candidate.popularity * 100,
        experience: candidate.experience,
      };
    });
  };

  const preparePartyComparison = () => {
    const partyData: Record<
      string,
      { count: number; policies: Record<string, number>; stats: Record<string, number> }
    > = {};

    // Initialize
    parties.forEach((party) => {
      partyData[party] = {
        count: 0,
        policies: Object.fromEntries(issues.map((issue) => [issue, 0])),
        stats: { charisma: 0, popularity: 0, experience: 0, scandals: 0, funds: 0 },
      };
    });

    // Aggregate data
    candidates.forEach((candidate) => {
      const party = candidate.party;
      if (partyData[party]) {
        partyData[party].count++;
        issues.forEach((issue) => {
          partyData[party].policies[issue] += candidate.policies[issue] || 0;
        });
        partyData[party].stats.charisma += candidate.charisma;
        partyData[party].stats.popularity += candidate.popularity;
        partyData[party].stats.experience += candidate.experience;
        partyData[party].stats.scandals += candidate.scandals;
        partyData[party].stats.funds += candidate.campaign_funds;
      }
    });

    // Calculate averages
    return Object.entries(partyData)
      .map(([party, data]) => {
        const avgPolicies: Record<string, number> = {};
        issues.forEach((issue) => {
          avgPolicies[issue] = (data.policies[issue] / data.count) * 100;
        });

        return {
          party,
          count: data.count,
          ...avgPolicies,
          charisma: (data.stats.charisma / data.count) * 100,
          popularity: (data.stats.popularity / data.count) * 100,
          experience: data.stats.experience / data.count,
          scandals: data.stats.scandals / data.count,
          funds: data.stats.funds / data.count,
        };
      })
      .filter((item) => item.count > 0);
  };

  // Format number for display
  const formatNumber = (value: number, decimals = 1) => {
    return value.toFixed(decimals).replace('.', ',');
  };

  // Format currency
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 0,
    }).format(value);
  };

  return (
    <Container className="my-4">
      <h1 className="text-center mb-4">{t('simulation.candidatesViz.pageTitle')}</h1>

      {/* Configuration Form */}
      <Card className="mb-4">
        <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
          <CardTitle>{t('simulation.candidatesViz.configTitle')}</CardTitle>
        </CardHeader>
        <CardBody>
          <form onSubmit={handleSubmit}>
            <Row className="mb-3">
              <Col md={3}>
                <label className="mb-1 inline-block">
                  {t('simulation.candidatesViz.numCandidates')}
                </label>
                <Control
                  type="number"
                  min="1"
                  max="20"
                  value={numCandidates}
                  onChange={(e) => setNumCandidates(parseInt(e.target.value) || 1)}
                />
              </Col>

              <Col md={5}>
                <label className="mb-1 inline-block">
                  {t('simulation.candidatesViz.politicalIssues')}
                </label>
                <Control
                  type="text"
                  value={issues.join(', ')}
                  onChange={(e) => setIssues(e.target.value.split(',').map((i) => i.trim()))}
                  placeholder={t('simulation.candidatesViz.issuesPlaceholder')}
                />
              </Col>

              <Col md={4}>
                <label className="mb-1 inline-block">
                  {t('simulation.candidatesViz.politicalParties')}
                </label>
                <Control
                  type="text"
                  value={parties.join(', ')}
                  onChange={(e) => setParties(e.target.value.split(',').map((p) => p.trim()))}
                  placeholder={t('simulation.candidatesViz.partiesPlaceholder')}
                />
              </Col>
            </Row>

            <div className="grid gap-2 md:flex md:justify-end">
              <Button variant="primary" type="submit" disabled={loading}>
                {loading ? (
                  <>
                    <Spinner size="sm" role="status" aria-hidden="true" />{' '}
                    {t('simulation.candidatesViz.generating')}
                  </>
                ) : (
                  t('simulation.candidatesViz.generate')
                )}
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>

      {/* Error Alert */}
      {error && (
        <Alert variant="danger" onClose={() => setError(null)} dismissible>
          {error}
        </Alert>
      )}

      {/* Main Content */}
      {candidates.length > 0 ? (
        <Tabs activeKey={activeTab} onSelect={(k) => setActiveTab(k || 'summary')} className="mb-3">
          {/* Summary Tab */}
          <Tab eventKey="summary" title={t('simulation.candidatesViz.tabSummary')}>
            <Card className="mb-4">
              <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
                <CardTitle>{t('simulation.candidatesViz.tabSummary')}</CardTitle>
              </CardHeader>
              <CardBody>
                <div className="table-responsive">
                  <Table className="[&_th]:p-2 [&_td]:p-2 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_th]:border [&_td]:border [&_tbody_tr:nth-child(odd)]:bg-muted/40 [&_tbody_tr:hover]:bg-muted/50">
                    <thead>
                      <tr>
                        <th>{t('simulation.candidatesViz.nameCol')}</th>
                        <th>{t('simulation.candidatesViz.partyCol')}</th>
                        <th>{t('simulation.candidatesViz.orientationCol')}</th>
                        <th>{t('simulation.candidatesViz.charismaCol')}</th>
                        <th>{t('simulation.candidatesViz.popularityCol')}</th>
                        <th>{t('simulation.candidatesViz.experienceCol')}</th>
                        <th>{t('simulation.candidatesViz.scandalsCol')}</th>
                        <th>{t('simulation.candidatesViz.fundsCol')}</th>
                        <th>{t('simulation.candidatesViz.actionsCol')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {candidates.map((candidate, index) => (
                        <tr key={index}>
                          <td>{candidate.name}</td>
                          <td>
                            <span
                              className={`badge bg-${
                                candidate.party === 'Green'
                                  ? 'success'
                                  : candidate.party === 'Conservative'
                                    ? 'primary'
                                    : candidate.party === 'Liberal'
                                      ? 'warning'
                                      : 'secondary'
                              }`}
                            >
                              {candidate.party}
                            </span>
                          </td>
                          <td>
                            <div className="progress" style={{ height: '20px' }}>
                              <div
                                className="progress-bar"
                                role="progressbar"
                                style={{
                                  width: `${((candidate.party_lean + 1) / 2) * 100}%`,
                                  backgroundColor: candidate.party_lean < 0 ? '#198754' : '#dc3545',
                                }}
                              >
                                {formatNumber(candidate.party_lean, 2)}
                              </div>
                            </div>
                          </td>
                          <td>
                            <div className="progress" style={{ height: '20px' }}>
                              <div
                                className="progress-bar bg-[#0dcaf0]"
                                role="progressbar"
                                style={{ width: `${candidate.charisma * 100}%` }}
                              >
                                {formatNumber(candidate.charisma * 100)}%
                              </div>
                            </div>
                          </td>
                          <td>
                            <div className="progress" style={{ height: '20px' }}>
                              <div
                                className="progress-bar bg-[#ffc107]"
                                role="progressbar"
                                style={{ width: `${candidate.popularity * 100}%` }}
                              >
                                {formatNumber(candidate.popularity * 100)}%
                              </div>
                            </div>
                          </td>
                          <td>
                            {candidate.experience} {t('simulation.candidatesViz.years')}
                          </td>
                          <td>
                            <span
                              className={`badge bg-${candidate.scandals > 0 ? 'danger' : 'secondary'}`}
                            >
                              {candidate.scandals}
                            </span>
                          </td>
                          <td>{formatCurrency(candidate.campaign_funds)}</td>
                          <td>
                            <Button
                              variant="outline-primary"
                              size="sm"
                              onClick={() => {
                                setSelectedCandidate(candidate);
                                setShowCandidateModal(true);
                              }}
                            >
                              {t('simulation.candidatesViz.details')}
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                </div>
              </CardBody>
            </Card>
          </Tab>

          {/* Policy Analysis Tab */}
          <Tab eventKey="policies" title={t('simulation.candidatesViz.tabPolicies')}>
            <Row>
              <Col md={6}>
                <Card className="mb-4">
                  <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
                    <CardTitle>{t('simulation.candidatesViz.avgImportance')}</CardTitle>
                  </CardHeader>
                  <CardBody>
                    <div style={{ height: '400px' }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={preparePolicyData()}
                          margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                        >
                          <XAxis
                            dataKey="name"
                            angle={-45}
                            textAnchor="end"
                            height={100}
                            interval={0}
                          />
                          <YAxis />
                          <Tooltip
                            formatter={(value: number) => [
                              `${value.toFixed(1)}%`,
                              t('simulation.candidatesViz.importance'),
                            ]}
                          />
                          <Legend />
                          <Bar dataKey="value" fill="#1a56cc">
                            {preparePolicyData().map((_, index) => (
                              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </CardBody>
                </Card>
              </Col>

              <Col md={6}>
                <Card className="mb-4">
                  <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
                    <CardTitle>{t('simulation.candidatesViz.partyComparison')}</CardTitle>
                  </CardHeader>
                  <CardBody>
                    <div style={{ height: '400px' }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={preparePartyComparison()}
                          margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                        >
                          <XAxis dataKey="party" />
                          <YAxis />
                          <Tooltip />
                          <Legend />
                          {issues.slice(0, 5).map((issue, index) => (
                            <Bar
                              key={issue}
                              dataKey={issue}
                              stackId="a"
                              fill={COLORS[index % COLORS.length]}
                              name={issue.replace('_', ' ')}
                            />
                          ))}
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </CardBody>
                </Card>
              </Col>
            </Row>

            <Card>
              <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
                <CardTitle>{t('simulation.candidatesViz.candidateRadar')}</CardTitle>
              </CardHeader>
              <CardBody>
                <div style={{ height: '500px' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart data={prepareCandidateComparison()}>
                      <PolarGrid />
                      <PolarAngleAxis dataKey="name" />
                      <PolarRadiusAxis angle={30} domain={[0, 100]} />
                      {issues.slice(0, 5).map((issue, index) => (
                        <Radar
                          key={issue}
                          dataKey={issue}
                          stroke={COLORS[index % COLORS.length]}
                          fill={COLORS[index % COLORS.length]}
                          fillOpacity={0.2}
                          name={issue.replace('_', ' ')}
                        />
                      ))}
                      <Legend />
                      <Tooltip />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              </CardBody>
            </Card>
          </Tab>

          {/* Statistics Tab */}
          <Tab eventKey="stats" title={t('simulation.candidatesViz.tabStats')}>
            <Row>
              <Col md={6}>
                <Card className="mb-4">
                  <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
                    <CardTitle>{t('simulation.candidatesViz.partyStatsTitle')}</CardTitle>
                  </CardHeader>
                  <CardBody>
                    <div className="table-responsive" style={{ maxHeight: '400px' }}>
                      <Table className="[&_th]:p-2 [&_td]:p-2 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_th]:border [&_td]:border [&_tbody_tr:nth-child(odd)]:bg-muted/40 [&_tbody_tr:hover]:bg-muted/50">
                        <thead>
                          <tr>
                            <th style={{ minWidth: '120px' }}>
                              {t('simulation.candidatesViz.partyCol')}
                            </th>
                            <th style={{ minWidth: '80px' }}>
                              {t('simulation.candidatesViz.candidatesCount')}
                            </th>
                            <th style={{ minWidth: '100px' }}>
                              {t('simulation.candidatesViz.charismaCol')}
                            </th>
                            <th style={{ minWidth: '100px' }}>
                              {t('simulation.candidatesViz.popularityCol')}
                            </th>
                            <th style={{ minWidth: '100px' }}>
                              {t('simulation.candidatesViz.experienceCol')}
                            </th>
                            <th style={{ minWidth: '80px' }}>
                              {t('simulation.candidatesViz.scandalsCol')}
                            </th>
                            <th style={{ minWidth: '120px' }}>
                              {t('simulation.candidatesViz.fundsCol')}
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {preparePartyComparison().map((party, index) => (
                            <tr key={index}>
                              <td>
                                <span
                                  className={`badge bg-${
                                    party.party === 'Green'
                                      ? 'success'
                                      : party.party === 'Conservative'
                                        ? 'primary'
                                        : party.party === 'Liberal'
                                          ? 'warning'
                                          : 'secondary'
                                  }`}
                                >
                                  {party.party}
                                </span>
                              </td>
                              <td>{party.count}</td>
                              <td>{formatNumber(party.charisma)}%</td>
                              <td>{formatNumber(party.popularity)}%</td>
                              <td>
                                {formatNumber(party.experience, 0)}{' '}
                                {t('simulation.candidatesViz.years')}
                              </td>
                              <td>{formatNumber(party.scandals, 1)}</td>
                              <td>{formatCurrency(party.funds)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </Table>
                    </div>
                  </CardBody>
                </Card>
              </Col>

              <Col md={6}>
                <Card className="mb-4">
                  <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
                    <CardTitle>{t('simulation.candidatesViz.correlationsTitle')}</CardTitle>
                  </CardHeader>
                  <CardBody>
                    <h6>{t('simulation.candidatesViz.charismaVsPopularity')}</h6>
                    <div style={{ height: '300px' }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={candidates.map((c) => ({
                            name: c.name.split(' ')[0],
                            charisma: c.charisma * 100,
                            popularity: c.popularity * 100,
                          }))}
                          margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                        >
                          <XAxis dataKey="name" />
                          <YAxis />
                          <Tooltip />
                          <Legend />
                          <Bar
                            dataKey="charisma"
                            fill="#1a56cc"
                            name={t('simulation.candidatesViz.charisma')}
                          />
                          <Bar
                            dataKey="popularity"
                            fill="#1b5e20"
                            name={t('simulation.candidatesViz.popularity')}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </CardBody>
                </Card>
              </Col>
            </Row>
          </Tab>
        </Tabs>
      ) : (
        <Alert variant="info">{t('simulation.candidatesViz.emptyState')}</Alert>
      )}

      {/* Candidate Details Modal */}
      <Modal show={showCandidateModal} onHide={() => setShowCandidateModal(false)} size="lg">
        {selectedCandidate && (
          <>
            <Modal.Header closeButton>
              <Modal.Title>{selectedCandidate.name}</Modal.Title>
            </Modal.Header>
            <Modal.Body>
              <Row>
                <Col md={6}>
                  <Card className="mb-3">
                    <CardBody>
                      <h6>{t('simulation.candidatesViz.generalInfo')}</h6>
                      <Table className="[&_th]:p-1 [&_td]:p-1 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle">
                        <tbody>
                          <tr>
                            <th>{t('simulation.candidatesViz.party')}:</th>
                            <td>
                              <span
                                className={`badge bg-${
                                  selectedCandidate.party === 'Green'
                                    ? 'success'
                                    : selectedCandidate.party === 'Conservative'
                                      ? 'primary'
                                      : selectedCandidate.party === 'Liberal'
                                        ? 'warning'
                                        : 'secondary'
                                }`}
                              >
                                {selectedCandidate.party}
                              </span>
                            </td>
                          </tr>
                          <tr>
                            <th>{t('simulation.candidatesViz.orientation')}:</th>
                            <td>
                              <div className="progress" style={{ height: '10px' }}>
                                <div
                                  className="progress-bar"
                                  role="progressbar"
                                  style={{
                                    width: `${((selectedCandidate.party_lean + 1) / 2) * 100}%`,
                                    backgroundColor:
                                      selectedCandidate.party_lean < 0 ? '#198754' : '#dc3545',
                                  }}
                                ></div>
                              </div>
                              {formatNumber(selectedCandidate.party_lean, 2)}
                            </td>
                          </tr>
                          <tr>
                            <th>{t('simulation.candidatesViz.charisma')}:</th>
                            <td>{formatNumber(selectedCandidate.charisma * 100)}%</td>
                          </tr>
                          <tr>
                            <th>{t('simulation.candidatesViz.popularity')}:</th>
                            <td>{formatNumber(selectedCandidate.popularity * 100)}%</td>
                          </tr>
                          <tr>
                            <th>{t('simulation.candidatesViz.experience')}:</th>
                            <td>
                              {selectedCandidate.experience} {t('simulation.candidatesViz.years')}
                            </td>
                          </tr>
                          <tr>
                            <th>{t('simulation.candidatesViz.scandals')}:</th>
                            <td>{selectedCandidate.scandals}</td>
                          </tr>
                          <tr>
                            <th>{t('simulation.candidatesViz.campaignFunds')}:</th>
                            <td>{formatCurrency(selectedCandidate.campaign_funds)}</td>
                          </tr>
                        </tbody>
                      </Table>
                    </CardBody>
                  </Card>

                  <Card>
                    <CardBody>
                      <h6>{t('simulation.candidatesViz.politicalPriorities')}</h6>
                      <div style={{ height: '250px' }}>
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            layout="vertical"
                            data={Object.entries(selectedCandidate.policies)
                              .map(([issue, value]) => ({
                                issue: issue.replace('_', ' '),
                                value: value * 100,
                              }))
                              .sort((a, b) => b.value - a.value)}
                          >
                            <XAxis type="number" domain={[0, 100]} />
                            <YAxis dataKey="issue" type="category" width={120} />
                            <Tooltip
                              formatter={(value: number) => [
                                `${value.toFixed(1)}%`,
                                t('simulation.candidatesViz.priority'),
                              ]}
                            />
                            <Bar dataKey="value" fill="#1a56cc" />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </CardBody>
                  </Card>
                </Col>

                <Col md={6}>
                  <Card className="h-full">
                    <CardBody>
                      <h6>{t('simulation.candidatesViz.politicalProfile')}</h6>
                      <div style={{ height: '400px' }}>
                        <ResponsiveContainer width="100%" height="100%">
                          <RadarChart
                            data={[
                              {
                                name: selectedCandidate.name,
                                ...Object.fromEntries(
                                  Object.entries(selectedCandidate.policies).map(
                                    ([issue, value]) => [issue.replace('_', ' '), value * 100]
                                  )
                                ),
                              },
                            ]}
                          >
                            <PolarGrid />
                            <PolarAngleAxis dataKey="name" />
                            <PolarRadiusAxis angle={30} domain={[0, 100]} />
                            {Object.keys(selectedCandidate.policies).map((issue, index) => (
                              <Radar
                                key={issue}
                                dataKey={issue.replace('_', ' ')}
                                stroke={COLORS[index % COLORS.length]}
                                fill={COLORS[index % COLORS.length]}
                                fillOpacity={0.6}
                              />
                            ))}
                            <Legend />
                            <Tooltip />
                          </RadarChart>
                        </ResponsiveContainer>
                      </div>
                    </CardBody>
                  </Card>
                </Col>
              </Row>
            </Modal.Body>
          </>
        )}
      </Modal>
    </Container>
  );
};

export default CandidatesVisualization;
