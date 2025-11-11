import React, { useState, useEffect } from 'react';
import {
  Container, Row, Col, Card, Table, Form, Button, Alert,
  Tabs, Tab, Spinner, Modal, ProgressBar, Badge, Pagination
} from 'react-bootstrap';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer,
  Cell, PieChart, Pie
} from 'recharts';
import { simulateUtility, getUtilityMatrix, getVoterSegments } from '../../services';
import { CandidateSimu, VoterSimu } from '../../types';
import { useSimulation } from '../../context/SimuContext';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8',
               '#A4DE6C', '#D0ED57', '#FF6B6B', '#AA96DA', '#FF9FF3'];

interface UtilityResult {
  voterId: number;
  candidateId: number;
  voterName?: string;
  candidateName: string;
  candidateParty: string;
  utility: number;
  breakdown: Record<string, number>;
  willVote: boolean;
}

interface UtilityMatrix {
  voter_ids: number[];
  candidate_ids: number[];
  values: number[][];
}

interface UtilityStats {
  average_utility: number;
  vote_shares: Record<string, { name: string; share: number }>;
}

interface VoterSegment {
  label: string;
  count: number;
  average_utility: number;
  top_candidate: {
    name: string;
    utility: number;
  } | null;
}

const UtilityVisualization: React.FC = () => {
  // State with proper initial values
  const [currentPage, setCurrentPage] = useState(1);
  const { voters, candidates, issues } = useSimulation();
  const [utilityResults, setUtilityResults] = useState<UtilityResult[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedVoter, setSelectedVoter] = useState<VoterSimu | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState<CandidateSimu | null>(null);
  const [showModal, setShowModal] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<string>('matrix');
  const [utilityMatrix, setUtilityMatrix] = useState<UtilityMatrix | null>(null);
  const [utilityStats, setUtilityStats] = useState<UtilityStats | null>(null);
  const [voterSegments, setVoterSegments] = useState<Record<string, VoterSegment> | null>(null);

  const [votersPerPage, setVotersPerPage] = useState(20);

  const getCurrentVoters = () => {
    const indexOfLastVoter = currentPage * votersPerPage;
    const indexOfFirstVoter = indexOfLastVoter - votersPerPage;
    return voters.slice(indexOfFirstVoter, indexOfLastVoter);
  };

  // Simulate utility data
  const simulateData = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await simulateUtility(issues, voters, candidates);
      if (result?.success) {
        setUtilityResults(result.utility_results || []);
      } else {
        throw new Error(result?.message || "Unknown error");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to simulate utility data');
      console.error("Error simulating utility:", err);
    } finally {
      setLoading(false);
    }
  };

  // Calculate utility matrix
  const calculateMatrix = async () => {
    if (voters.length === 0 || candidates.length === 0) return;

    setLoading(true);
    try {
      const result = await getUtilityMatrix(voters, candidates, issues);
      if (result?.success) {
        setUtilityMatrix(result.matrix || null);
        setUtilityStats(result.stats || null);
      } else {
        throw new Error(result?.message || "Unknown error");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to calculate utility matrix');
      console.error("Error calculating utility matrix:", err);
    } finally {
      setLoading(false);
    }
  };

  // Calculate voter segments
  const calculateSegments = async () => {
    if (voters.length === 0 || candidates.length === 0) return;

    setLoading(true);
    try {
      const result = await getVoterSegments(voters, candidates, issues);
      if (result?.success) {
        setVoterSegments(result.segments || null);
      } else {
        throw new Error(result?.message || "Unknown error");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to calculate voter segments');
      console.error("Error calculating voter segments:", err);
    } finally {
      setLoading(false);
    }
  };

  // Calculate all analyses when data changes
  useEffect(() => {
    if (voters.length > 0 && candidates.length > 0) {
      calculateMatrix();
      calculateSegments();
    }
  }, [voters, candidates]);

  // Formatters
  const formatPercentage = (value: number) => `${(value * 100).toFixed(1)}%`;
  const formatNumber = (value: number, decimals = 2) => value.toFixed(decimals);

  // Prepare data for visualizations with safety checks
  const prepareCandidatePerformance = () => {
    if (!utilityStats) return [];

    try {
      return Object.entries(utilityStats.vote_shares).map(([candidateId, data]) => {
        const candidate = candidates.find(c => c.id === parseInt(candidateId));
        return {
          candidateId: parseInt(candidateId),
          candidateName: candidate?.name || `Candidate ${parseInt(candidateId) + 1}`,
          candidateParty: candidate?.party || 'Unknown',
          averageUtility: utilityStats.average_utility,
          voteShare: (data.share * 100) || 0
        };
      });
    } catch (e) {
      console.error("Error preparing candidate performance data:", e);
      return [];
    }
  };

  const prepareVoterSegmentsData = () => {
    if (!voterSegments) return [];

    try {
      return Object.entries(voterSegments).map(([key, segment]) => ({
        segment: segment.label,
        count: segment.count || 0,
        averageUtility: segment.average_utility || 0,
        topCandidate: segment.top_candidate?.name || 'None'
      }));
    } catch (e) {
      console.error("Error preparing voter segments data:", e);
      return [];
    }
  };

  const prepareUtilityDistribution = () => {
    if (!utilityMatrix) return [];

    try {
      return utilityMatrix.candidate_ids.map((candidateId, candidateIndex) => {
        const candidate = candidates.find(c => c.id === candidateId);
        const candidateData = utilityMatrix.values.map(row => row[candidateIndex]);

        const bins = Array(10).fill(0).map((_, i) => ({
          bin: `${(i * 0.2).toFixed(1)}-${((i + 1) * 0.2).toFixed(1)}`,
          count: 0
        }));

        candidateData.forEach(utility => {
          if (typeof utility === 'number') {
            const binIndex = Math.min(Math.floor(utility / 0.2), 9);
            bins[binIndex].count++;
          }
        });

        return {
          candidateId,
          candidateName: candidate?.name || `Candidate ${candidateId + 1}`,
          bins: bins.filter(b => b.count > 0)
        };
      });
    } catch (e) {
      console.error("Error preparing utility distribution data:", e);
      return [];
    }
  };

  // Find utility result for specific voter-candidate pair
  const findUtilityResult = (voterId: number, candidateId: number) => {
    return utilityResults.find(r => r.voterId === voterId && r.candidateId === candidateId);
  };

  return (
    <Container className="my-4">
      <h1 className="text-center mb-4">Analyse des Scores d'Utilité</h1>

      {/* Configuration Form */}
      <Card className="mb-4">
        <Card.Header>
          <Card.Title>Paramètres de Simulation</Card.Title>
        </Card.Header>
        <Card.Body>
          <Form onSubmit={(e) => { e.preventDefault(); simulateData(); }}>
            <Row className="mb-3 align-items-center">
                <Form.Group as={Col} md={3}>
                    <Form.Label>Votants par page</Form.Label>
                    <Form.Select
                    value={votersPerPage}
                    onChange={(e) => {
                        setVotersPerPage(parseInt(e.target.value));
                        setCurrentPage(1); // Réinitialiser à la première page
                    }}
                    >
                    <option value="10">10</option>
                    <option value="20">20</option>
                    <option value="50">50</option>
                    <option value="100">100</option>
                    </Form.Select>
                </Form.Group>
            </Row>

            <div className="d-grid gap-2 d-md-flex justify-content-md-end">
              <Button variant="primary" type="submit" disabled={loading}>
                {loading ? (
                  <>
                    <Spinner as="span" animation="border" size="sm" role="status" aria-hidden="true" />
                    {' '}Chargement...
                  </>
                ) : 'Générer et Analyser'}
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
      {utilityResults.length > 0 ? (
        <Tabs
          activeKey={activeTab}
          onSelect={(k) => setActiveTab(k || 'matrix')}
          className="mb-3"
        >
          {/* Utility Matrix */}
          <Tab eventKey="matrix" title="Matrice d'Utilité">
            <Card className="mb-4">
                <Card.Header>
                <Card.Title>Matrice des Scores d'Utilité</Card.Title>
                </Card.Header>
                <Card.Body>
                {utilityMatrix ? (
                    <>
                    <div className="table-responsive mb-3">
                        <Table bordered hover>
                        <thead>
                            <tr>
                            <th>Votant\Candidat</th>
                            {candidates.map(candidate => (
                                <th key={candidate.id} className="text-center">
                                <div>{candidate.name.split(' ')[0]}</div>
                                <Badge bg={
                                    candidate.party === 'Green' ? 'success' :
                                    candidate.party === 'Conservative' ? 'primary' :
                                    candidate.party === 'Liberal' ? 'warning' : 'secondary'
                                }>
                                    {candidate.party}
                                </Badge>
                                </th>
                            ))}
                            </tr>
                        </thead>
                        <tbody>
                            {getCurrentVoters().map(voter => (
                            <tr key={voter.id}>
                                <td>
                                <div>Votant {voter.id + 1}</div>
                                <small className="text-muted">
                                    {voter.age} ans, {voter.gender}, {voter.education}
                                </small>
                                </td>
                                {candidates.map(candidate => {
                                const utility = utilityMatrix.values[voter.id]?.[candidates.indexOf(candidate)] || 0;
                                const result = findUtilityResult(voter.id, candidate.id);
                                return (
                                    <td
                                    key={candidate.id}
                                    className="text-center"
                                    style={{
                                        backgroundColor: `rgba(0, 123, 255, ${0.1 + 0.4 * utility})`,
                                        cursor: 'pointer'
                                    }}
                                    onClick={() => {
                                        setSelectedVoter(voter);
                                        setSelectedCandidate(candidate);
                                        setShowModal(true);
                                    }}
                                    >
                                    {utility.toFixed(2)}
                                    {result?.willVote && (
                                        <div className="text-success">✓</div>
                                    )}
                                    </td>
                                );
                                })}
                            </tr>
                            ))}
                        </tbody>
                        </Table>
                    </div>

                    {/* Ajoutez la pagination ici */}
                    <Pagination className="justify-content-center">
                        <Pagination.First
                            onClick={() => setCurrentPage(1)}
                            disabled={currentPage === 1}
                        />
                        <Pagination.Prev
                            onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                            disabled={currentPage === 1}
                        />

                        {/* Afficher max 5 pages autour de la page actuelle */}
                        {Array.from({ length: Math.ceil(voters.length / votersPerPage) }, (_, i) => i + 1)
                            .filter(number =>
                            number === 1 ||
                            number === Math.ceil(voters.length / votersPerPage) ||
                            (number >= currentPage - 2 && number <= currentPage + 2)
                            )
                            .map(number => (
                            <Pagination.Item
                                key={number}
                                active={number === currentPage}
                                onClick={() => setCurrentPage(number)}
                            >
                                {number}
                            </Pagination.Item>
                            ))}

                        {/* Ajouter "..." si nécessaire */}
                        {currentPage + 2 < Math.ceil(voters.length / votersPerPage) - 1 && <Pagination.Ellipsis disabled />}
                        {currentPage - 2 > 2 && <Pagination.Ellipsis disabled />}

                        <Pagination.Next
                            onClick={() => setCurrentPage(prev => Math.min(Math.ceil(voters.length / votersPerPage), prev + 1))}
                            disabled={currentPage === Math.ceil(voters.length / votersPerPage)}
                        />
                        <Pagination.Last
                            onClick={() => setCurrentPage(Math.ceil(voters.length / votersPerPage))}
                            disabled={currentPage === Math.ceil(voters.length / votersPerPage)}
                        />
                        </Pagination>

                    <div className="text-center mt-2">
                        <small className="text-muted">
                        Affichage des votants {currentPage * votersPerPage - votersPerPage + 1} à {
                            Math.min(currentPage * votersPerPage, voters.length)
                        } sur {voters.length}
                        </small>
                    </div>
                    </>
                ) : (
                    <Alert variant="info">Calcul de la matrice en cours...</Alert>
                )}
                </Card.Body>
            </Card>
            </Tab>

          {/* Candidate Performance */}
          <Tab eventKey="performance" title="Performance des Candidats">
            <Row>
              <Col md={6}>
                <Card className="mb-4">
                  <Card.Header>
                    <Card.Title>Performance Moyenne des Candidats</Card.Title>
                  </Card.Header>
                  <Card.Body>
                    {prepareCandidatePerformance().length > 0 ? (
                      <div style={{ height: '400px' }}>
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            data={prepareCandidatePerformance()}
                            margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                          >
                            <XAxis dataKey="candidateName" angle={-45} textAnchor="end" height={100} interval={0} />
                            <YAxis />
                            <Tooltip
                              formatter={(value: number, name: string) =>
                                name.includes('Utility') ? formatNumber(value, 2) :
                                formatPercentage(value)
                              }
                            />
                            <Legend />
                            <Bar dataKey="averageUtility" name="Utilité moyenne" fill="#8884d8" />
                            <Bar dataKey="voteShare" name="Part des voix" fill="#82ca9d" />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    ) : (
                      <Alert variant="info">Aucune donnée de performance disponible</Alert>
                    )}
                  </Card.Body>
                </Card>
              </Col>

              <Col md={6}>
                <Card className="mb-4">
                  <Card.Header>
                    <Card.Title>Statistiques Globales</Card.Title>
                  </Card.Header>
                  <Card.Body>
                    {utilityStats && (
                      <>
                        <h5>Utilité Moyenne: {formatNumber(utilityStats.average_utility, 2)}</h5>
                        <Table striped bordered hover className="mt-3">
                          <thead>
                            <tr>
                              <th>Candidat</th>
                              <th>Parti</th>
                              <th>Part des voix</th>
                            </tr>
                          </thead>
                          <tbody>
                            {Object.entries(utilityStats.vote_shares).map(([candidateId, data]) => {
                              const candidate = candidates.find(c => c.id === parseInt(candidateId));
                              return (
                                <tr key={candidateId}>
                                  <td>{candidate?.name || `Candidat ${parseInt(candidateId) + 1}`}</td>
                                  <td>
                                    <Badge bg={
                                      candidate?.party === 'Green' ? 'success' :
                                      candidate?.party === 'Conservative' ? 'primary' :
                                      candidate?.party === 'Liberal' ? 'warning' : 'secondary'
                                    }>
                                      {candidate?.party || 'Inconnu'}
                                    </Badge>
                                  </td>
                                  <td>{formatPercentage(data.share)}</td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </Table>
                      </>
                    )}
                  </Card.Body>
                </Card>
              </Col>
            </Row>
          </Tab>

          {/* Voter Segments */}
          <Tab eventKey="segments" title="Segments de Votants">
            <Row>
              <Col md={6}>
                <Card className="mb-4">
                  <Card.Header>
                    <Card.Title>Utilité par Segment</Card.Title>
                  </Card.Header>
                  <Card.Body>
                    {prepareVoterSegmentsData().length > 0 ? (
                      <div style={{ height: '400px' }}>
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            data={prepareVoterSegmentsData()}
                            margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                          >
                            <XAxis dataKey="segment" angle={-45} textAnchor="end" height={100} interval={0} />
                            <YAxis />
                            <Tooltip
                              formatter={(value: number, name: string) =>
                                name === 'Utilité moyenne' ? formatNumber(value, 2) : value
                              }
                            />
                            <Legend />
                            <Bar dataKey="averageUtility" name="Utilité moyenne" fill="#8884d8" />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    ) : (
                      <Alert variant="info">Aucune donnée de segment disponible</Alert>
                    )}
                  </Card.Body>
                </Card>
              </Col>

              <Col md={6}>
                <Card className="mb-4">
                  <Card.Header>
                    <Card.Title>Candidat Préféré par Segment</Card.Title>
                  </Card.Header>
                  <Card.Body>
                    {prepareVoterSegmentsData().length > 0 ? (
                      <div style={{ height: '400px' }}>
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie
                              data={prepareVoterSegmentsData().map(seg => ({
                                name: seg.segment,
                                value: seg.count,
                                topCandidate: seg.topCandidate
                              }))}
                              dataKey="value"
                              nameKey="name"
                              cx="50%"
                              cy="50%"
                              outerRadius={80}
                              fill="#8884d8"
                              label={({ name, topCandidate }) =>
                                `${name}\nPréfère: ${topCandidate}`}
                            >
                              {prepareVoterSegmentsData().map((_, index) => (
                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                              ))}
                            </Pie>
                            <Tooltip
                              formatter={(value: number, name: string, props: any) => {
                                const segment = prepareVoterSegmentsData()[props.dataIndex];
                                return segment ? [
                                  `${segment.segment}`,
                                  `Nombre: ${value}`,
                                  `Préfère: ${segment.topCandidate}`,
                                  `Utilité: ${formatNumber(segment.averageUtility, 2)}`
                                ] : ['Données non disponibles'];
                              }}
                            />
                            <Legend />
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                    ) : (
                      <Alert variant="info">Aucune donnée de segment disponible</Alert>
                    )}
                  </Card.Body>
                </Card>
              </Col>
            </Row>
          </Tab>

          {/* Utility Distribution */}
          <Tab eventKey="distribution" title="Distribution des Scores">
            <Card>
              <Card.Header>
                <Card.Title>Distribution des Scores d'Utilité par Candidat</Card.Title>
              </Card.Header>
              <Card.Body>
                {prepareUtilityDistribution().length > 0 ? (
                  prepareUtilityDistribution().map((candidateData, index) => (
                    <div key={index} className="mb-4">
                      <h5>{candidateData.candidateName}</h5>
                      {candidateData.bins.length > 0 ? (
                        <div style={{ height: '200px' }}>
                          <ResponsiveContainer width="100%" height="100%">
                            <BarChart
                              data={candidateData.bins}
                              margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                            >
                              <XAxis dataKey="bin" />
                              <YAxis />
                              <Tooltip />
                              <Legend />
                              <Bar dataKey="count" fill={COLORS[index % COLORS.length]} />
                            </BarChart>
                          </ResponsiveContainer>
                        </div>
                      ) : (
                        <Alert variant="info">Aucune donnée de distribution disponible pour ce candidat</Alert>
                      )}
                    </div>
                  ))
                ) : (
                  <Alert variant="info">Aucune donnée de distribution disponible</Alert>
                )}
              </Card.Body>
            </Card>
          </Tab>
        </Tabs>
      ) : (
        <Alert variant="info">
          Utilisez le formulaire ci-dessus pour générer des votants et des candidats et calculer les scores d'utilité.
        </Alert>
      )}

      {/* Utility Breakdown Modal */}
      <Modal
        show={showModal}
        onHide={() => setShowModal(false)}
        size="lg"
      >
        {selectedVoter && selectedCandidate && (
          <>
            <Modal.Header closeButton>
              <Modal.Title>
                Détail du Score d'Utilité: Votant {selectedVoter.id + 1} → {selectedCandidate.name}
              </Modal.Title>
            </Modal.Header>
            <Modal.Body>
              <Row>
                <Col md={6}>
                  <Card className="mb-3">
                    <Card.Body>
                      <h6>Profil du Votant</h6>
                      <Table borderless size="sm">
                        <tbody>
                          <tr>
                            <th>Âge:</th>
                            <td>{selectedVoter.age} ans</td>
                          </tr>
                          <tr>
                            <th>Genre:</th>
                            <td>{selectedVoter.gender}</td>
                          </tr>
                          <tr>
                            <th>Éducation:</th>
                            <td>{selectedVoter.education}</td>
                          </tr>
                          <tr>
                            <th>Revenu:</th>
                            <td>{selectedVoter.income}</td>
                          </tr>
                          <tr>
                            <th>Région:</th>
                            <td>{selectedVoter.region}</td>
                          </tr>
                          <tr>
                            <th>Orientation:</th>
                            <td>
                              <ProgressBar
                                now={((selectedVoter.political_lean + 1) / 2) * 100}
                                label={`${formatNumber(selectedVoter.political_lean, 2)}`}
                                variant={selectedVoter.political_lean < 0 ? 'success' : 'danger'}
                              />
                            </td>
                          </tr>
                        </tbody>
                      </Table>
                    </Card.Body>
                  </Card>
                </Col>

                <Col md={6}>
                  <Card className="mb-3">
                    <Card.Body>
                      <h6>Profil du Candidat</h6>
                      <Table borderless size="sm">
                        <tbody>
                          <tr>
                            <th>Parti:</th>
                            <td>
                              <Badge bg={
                                selectedCandidate.party === 'Green' ? 'success' :
                                selectedCandidate.party === 'Conservative' ? 'primary' :
                                selectedCandidate.party === 'Liberal' ? 'warning' : 'secondary'
                              }>
                                {selectedCandidate.party}
                              </Badge>
                            </td>
                          </tr>
                          <tr>
                            <th>Orientation:</th>
                            <td>
                              <ProgressBar
                                now={((selectedCandidate.party_lean + 1) / 2) * 100}
                                label={`${formatNumber(selectedCandidate.party_lean, 2)}`}
                                variant={selectedCandidate.party_lean < 0 ? 'success' : 'danger'}
                              />
                            </td>
                          </tr>
                        </tbody>
                      </Table>
                    </Card.Body>
                  </Card>
                </Col>
              </Row>

              <Row>
                <Col md={12}>
                  <Card>
                    <Card.Body>
                      <h6>Décomposition du Score d'Utilité</h6>
                      {(() => {
                        const result = utilityResults.find(
                          r => r.voterId === selectedVoter.id && r.candidateId === selectedCandidate.id
                        );

                        if (!result) return <Alert variant="warning">Données d'utilité non disponibles</Alert>;

                        const data = Object.entries(result.breakdown)
                          .map(([key, value]) => ({
                            name: key.replace('_', ' '),
                            value,
                            color: key === 'scandal_penalty' ? '#dc3545' :
                                   key === 'gender_bonus' ? '#AA96DA' :
                                   COLORS[Object.keys(result.breakdown).indexOf(key) % COLORS.length]
                          }))
                          .filter(item => item.value !== 0);

                        const total = data.reduce((sum, item) => sum + item.value, 0);

                        return (
                          <>
                            <h4 className="text-center">
                              Score Total: {formatNumber(result.utility, 2)}
                              {result.willVote && (
                                <Badge bg="success" className="ms-2">Votera pour ce candidat</Badge>
                              )}
                            </h4>

                            {data.length > 0 ? (
                              <>
                                <div style={{ height: '200px' }}>
                                  <ResponsiveContainer width="100%" height="100%">
                                    <BarChart
                                      layout="vertical"
                                      data={data}
                                    >
                                      <XAxis type="number" domain={[-0.5, 0.5]} />
                                      <YAxis dataKey="name" type="category" width={150} />
                                      <Tooltip
                                        formatter={(value: number) => formatNumber(value, 3)}
                                      />
                                      {data.map((item, index) => (
                                        <Bar
                                          key={item.name}
                                          dataKey="value"
                                          stackId="a"
                                          fill={item.color}
                                        >
                                          <Cell fill={item.color} />
                                        </Bar>
                                      ))}
                                    </BarChart>
                                  </ResponsiveContainer>
                                </div>

                                <Table striped bordered className="mt-3">
                                  <thead>
                                    <tr>
                                      <th>Composante</th>
                                      <th>Valeur</th>
                                      <th>Poids</th>
                                      <th>Contribution</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {data.map((item, index) => (
                                      <tr key={index}>
                                        <td>{item.name}</td>
                                        <td>{formatNumber(item.value, 3)}</td>
                                        <td>
                                          {item.name === 'issue_score' && '60%'}
                                          {item.name === 'loyalty_bonus' && '20%'}
                                          {item.name === 'charisma_effect' && '15%'}
                                          {(item.name === 'scandal_penalty' || item.name === 'mood_effect' || item.name === 'gender_bonus') && 'Variable'}
                                        </td>
                                        <td>
                                          {formatNumber(item.value / total * 100, 1)}%
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </Table>
                              </>
                            ) : (
                              <Alert variant="info">Aucune composante d'utilité disponible</Alert>
                            )}
                          </>
                        );
                      })()}
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

export default UtilityVisualization;
