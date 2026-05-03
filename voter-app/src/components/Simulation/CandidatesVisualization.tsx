import React, { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Form,
  Button,
  Table,
  Alert,
  Tabs,
  Tab,
  Spinner,
  Modal,
  Container,
} from 'react-bootstrap';
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
import { useSimulation } from '../../context/SimuContext';

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
      <h1 className="text-center mb-4">Simulation et Visualisation des Candidats</h1>

      {/* Configuration Form */}
      <Card className="mb-4">
        <Card.Header>
          <Card.Title>Paramètres de Simulation</Card.Title>
        </Card.Header>
        <Card.Body>
          <Form onSubmit={handleSubmit}>
            <Row className="mb-3">
              <Form.Group as={Col} md={3}>
                <Form.Label>Nombre de candidats</Form.Label>
                <Form.Control
                  type="number"
                  min="1"
                  max="20"
                  value={numCandidates}
                  onChange={(e) => setNumCandidates(parseInt(e.target.value) || 1)}
                />
              </Form.Group>

              <Form.Group as={Col} md={5}>
                <Form.Label>Enjeux politiques</Form.Label>
                <Form.Control
                  type="text"
                  value={issues.join(', ')}
                  onChange={(e) => setIssues(e.target.value.split(',').map((i) => i.trim()))}
                  placeholder="economy, environment, healthcare, ..."
                />
              </Form.Group>

              <Form.Group as={Col} md={4}>
                <Form.Label>Partis politiques</Form.Label>
                <Form.Control
                  type="text"
                  value={parties.join(', ')}
                  onChange={(e) => setParties(e.target.value.split(',').map((p) => p.trim()))}
                  placeholder="Green, Conservative, Liberal, ..."
                />
              </Form.Group>
            </Row>

            <div className="d-grid gap-2 d-md-flex justify-content-md-end">
              <Button variant="primary" type="submit" disabled={loading}>
                {loading ? (
                  <>
                    <Spinner
                      as="span"
                      animation="border"
                      size="sm"
                      role="status"
                      aria-hidden="true"
                    />{' '}
                    Génération en cours...
                  </>
                ) : (
                  'Générer les candidats'
                )}
              </Button>
            </div>
          </Form>
        </Card.Body>
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
          <Tab eventKey="summary" title="Résumé">
            <Card className="mb-4">
              <Card.Header>
                <Card.Title>Table of Candidats</Card.Title>
              </Card.Header>
              <Card.Body>
                <div className="table-responsive">
                  <Table striped bordered hover>
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>Parti</th>
                        <th>Orientation</th>
                        <th>Charisme</th>
                        <th>Popularity</th>
                        <th>Experience</th>
                        <th>Scandales</th>
                        <th>Fonds</th>
                        <th>Actions</th>
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
                                className="progress-bar bg-info"
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
                                className="progress-bar bg-warning"
                                role="progressbar"
                                style={{ width: `${candidate.popularity * 100}%` }}
                              >
                                {formatNumber(candidate.popularity * 100)}%
                              </div>
                            </div>
                          </td>
                          <td>{candidate.experience} ans</td>
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
                              Détails
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                </div>
              </Card.Body>
            </Card>
          </Tab>

          {/* Policy Analysis Tab */}
          <Tab eventKey="policies" title="Analyse des Politiques">
            <Row>
              <Col md={6}>
                <Card className="mb-4">
                  <Card.Header>
                    <Card.Title>Importance Moyenne des Enjeux</Card.Title>
                  </Card.Header>
                  <Card.Body>
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
                            formatter={(value: number) => [`${value.toFixed(1)}%`, 'Importance']}
                          />
                          <Legend />
                          <Bar dataKey="value" fill="#8884d8">
                            {preparePolicyData().map((_, index) => (
                              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </Card.Body>
                </Card>
              </Col>

              <Col md={6}>
                <Card className="mb-4">
                  <Card.Header>
                    <Card.Title>Comparaison par Parti</Card.Title>
                  </Card.Header>
                  <Card.Body>
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
                  </Card.Body>
                </Card>
              </Col>
            </Row>

            <Card>
              <Card.Header>
                <Card.Title>Comparaison des Candidats (Radar)</Card.Title>
              </Card.Header>
              <Card.Body>
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
              </Card.Body>
            </Card>
          </Tab>

          {/* Statistics Tab */}
          <Tab eventKey="stats" title="Statistiques">
            <Row>
              <Col md={6}>
                <Card className="mb-4">
                  <Card.Header>
                    <Card.Title>Statistiques par Parti</Card.Title>
                  </Card.Header>
                  <Card.Body>
                    <div className="table-responsive" style={{ maxHeight: '400px' }}>
                      <Table striped bordered hover>
                        <thead>
                          <tr>
                            <th style={{ minWidth: '120px' }}>Parti</th>
                            <th style={{ minWidth: '80px' }}>Candidats</th>
                            <th style={{ minWidth: '100px' }}>Charisme</th>
                            <th style={{ minWidth: '100px' }}>Popularité</th>
                            <th style={{ minWidth: '100px' }}>Expérience</th>
                            <th style={{ minWidth: '80px' }}>Scandales</th>
                            <th style={{ minWidth: '120px' }}>Fonds</th>
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
                              <td>{formatNumber(party.experience, 0)} ans</td>
                              <td>{formatNumber(party.scandals, 1)}</td>
                              <td>{formatCurrency(party.funds)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </Table>
                    </div>
                  </Card.Body>
                </Card>
              </Col>

              <Col md={6}>
                <Card className="mb-4">
                  <Card.Header>
                    <Card.Title>Corrélations</Card.Title>
                  </Card.Header>
                  <Card.Body>
                    <h6>Charisme vs Popularité</h6>
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
                          <Bar dataKey="charisma" fill="#8884d8" name="Charisme" />
                          <Bar dataKey="popularity" fill="#82ca9d" name="Popularité" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </Card.Body>
                </Card>
              </Col>
            </Row>
          </Tab>
        </Tabs>
      ) : (
        <Alert variant="info">Utilisez le formulaire ci-dessus pour générer des candidats.</Alert>
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
                    <Card.Body>
                      <h6>Informations Générales</h6>
                      <Table borderless size="sm">
                        <tbody>
                          <tr>
                            <th>Parti:</th>
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
                            <th>Orientation:</th>
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
                            <th>Charisme:</th>
                            <td>{formatNumber(selectedCandidate.charisma * 100)}%</td>
                          </tr>
                          <tr>
                            <th>Popularité:</th>
                            <td>{formatNumber(selectedCandidate.popularity * 100)}%</td>
                          </tr>
                          <tr>
                            <th>Expérience:</th>
                            <td>{selectedCandidate.experience} ans</td>
                          </tr>
                          <tr>
                            <th>Scandales:</th>
                            <td>{selectedCandidate.scandals}</td>
                          </tr>
                          <tr>
                            <th>Fonds de campagne:</th>
                            <td>{formatCurrency(selectedCandidate.campaign_funds)}</td>
                          </tr>
                        </tbody>
                      </Table>
                    </Card.Body>
                  </Card>

                  <Card>
                    <Card.Body>
                      <h6>Priorités Politiques</h6>
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
                              formatter={(value: number) => [`${value.toFixed(1)}%`, 'Priorité']}
                            />
                            <Bar dataKey="value" fill="#8884d8" />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </Card.Body>
                  </Card>
                </Col>

                <Col md={6}>
                  <Card className="h-100">
                    <Card.Body>
                      <h6>Profil Politique (Radar)</h6>
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
                    </Card.Body>
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
