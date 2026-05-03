import React, { useState, useEffect } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
} from 'recharts';
import { Container, Row, Col, Form, Button, Card } from 'react-bootstrap';
import { simulateVoters } from '../../services';
import IssuePrioritiesVisualization from './IssuePrioritiesVisualization';
import { Region, Income, PartySimu, Family, Ethnicity, Religion, Employement } from '../../types';
import { useSimulation } from '../../context/SimuContext';

// Interface compatible avec Recharts
interface ChartData {
  [key: string]: number | string;
}

interface CrossTabulationData {
  [key: string]: {
    [key: string]: number;
  };
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

const VoterVisualization: React.FC = () => {
  const { voters, setVoters } = useSimulation();
  const [numVoters, setNumVoters] = useState<number>(1000);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    fetchVoters();
  }, []);

  const fetchVoters = async () => {
    setLoading(true);
    try {
      const response = await simulateVoters(numVoters);
      setVoters(response.voters);
    } catch (error) {
      console.error('Error fetching voters:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = () => {
    fetchVoters();
  };

  // Age distribution
  const ageData = (): ChartData[] => {
    const bins = Array(10)
      .fill(0)
      .map((_, i) => ({
        range: `${20 + i * 8}-${27 + i * 8}`,
        count: 0,
      }));
    voters.forEach((voter) => {
      const binIndex = Math.min(Math.floor((voter.age - 18) / 8), 9);
      bins[binIndex].count++;
    });
    return bins;
  };

  const employmentData = (): ChartData[] => {
    const counts: Record<Employement, number> = {
      employed: 0,
      unemployed: 0,
      self_employed: 0,
      retired: 0,
    };

    voters.forEach((voter) => {
      if (voter.employment_status in counts) {
        counts[voter.employment_status]++;
      }
    });

    return Object.entries(counts).map(([status, count]) => ({
      name: status.replace('_', ' '),
      value: count,
    }));
  };

  // Family
  const familyData = (): ChartData[] => {
    const counts: Record<Family, number> = {
      single: 0,
      with_children: 0,
      retired: 0,
    };

    voters.forEach((voter) => {
      if (voter.family_status in counts) {
        counts[voter.family_status]++;
      }
    });

    return Object.entries(counts).map(([status, count]) => ({
      name: status.replace('_', ' '),
      value: count,
    }));
  };

  const ethnicityData = (): ChartData[] => {
    const counts: Record<Ethnicity, number> = {
      native: 0,
      immigrant: 0,
    };

    voters.forEach((voter) => {
      if (voter.ethnicity_immigration in counts) {
        counts[voter.ethnicity_immigration]++;
      }
    });

    return Object.entries(counts).map(([status, count]) => ({
      name: status.replace('_', ' '),
      value: count,
    }));
  };

  const religionData = (): ChartData[] => {
    const counts: Record<Religion, number> = {
      religious: 0,
      non_religious: 0,
    };

    voters.forEach((voter) => {
      if (voter.religion in counts) {
        counts[voter.religion]++;
      }
    });

    return Object.entries(counts).map(([status, count]) => ({
      name: status.replace('_', ' '),
      value: count,
    }));
  };

  // Gender distribution
  const genderData = (): ChartData[] => {
    const counts = { male: 0, female: 0 };
    voters.forEach((voter) => {
      counts[voter.gender]++;
    });
    return Object.entries(counts).map(([gender, count]) => ({
      name: gender,
      value: count,
    }));
  };

  // Education distribution
  const educationData = (): ChartData[] => {
    const educationLevels = ['none', 'high_school', 'bachelor', 'master', 'phd'];
    const counts: Record<string, number> = {
      none: 0,
      high_school: 0,
      bachelor: 0,
      master: 0,
      phd: 0,
    };

    voters.forEach((voter) => {
      counts[voter.education]++;
    });

    return educationLevels.map((level) => ({
      name: level.replace('_', ' '),
      value: counts[level],
    }));
  };

  // Region distribution
  const regionData = (): ChartData[] => {
    const counts: Record<Region, number> = { urban: 0, suburban: 0, rural: 0 };
    voters.forEach((voter) => {
      counts[voter.region]++;
    });
    return Object.entries(counts).map(([region, count]) => ({
      name: region,
      value: count,
    }));
  };

  // Income distribution
  const incomeData = (): ChartData[] => {
    const counts: Record<Income, number> = { low: 0, middle: 0, high: 0 };
    voters.forEach((voter) => {
      counts[voter.income]++;
    });
    return Object.entries(counts).map(([income, count]) => ({
      name: income,
      value: count,
    }));
  };

  // Political lean distribution
  const politicalLeanData = (): ChartData[] => {
    // Create the initial bins
    const initialBins = Array.from({ length: 10 }, (_, i) => ({
      range: `${(-1 + i * 0.2).toFixed(1)}-${(-0.8 + i * 0.2).toFixed(1)}`,
      count: 0,
    }));

    // Count votes in each bin without mutation
    return voters.reduce((bins, voter) => {
      const binIndex = Math.min(Math.floor((voter.political_lean + 1) * 5), 9);
      return bins.map((bin, i) => (i === binIndex ? { ...bin, count: bin.count + 1 } : bin));
    }, initialBins);
  };

  // Party distribution
  const partyData = (): ChartData[] => {
    const counts: Record<PartySimu, number> = {
      Green: 0,
      Conservative: 0,
      Liberal: 0,
      Independent: 0,
    };
    voters.forEach((voter) => {
      counts[voter.preferred_party]++;
    });
    return Object.entries(counts).map(([party, count]) => ({
      name: party,
      value: count,
    }));
  };

  // Cross-tabulation: Emploi x Statut familial
  const prepareEmploymentFamilyCrossTab = (): CrossTabulationData => {
    const crossTab: CrossTabulationData = {};

    voters.forEach((voter) => {
      if (!crossTab[voter.employment_status]) {
        crossTab[voter.employment_status] = {};
      }
      if (!crossTab[voter.employment_status][voter.family_status]) {
        crossTab[voter.employment_status][voter.family_status] = 0;
      }
      crossTab[voter.employment_status][voter.family_status]++;
    });

    return crossTab;
  };

  // Cross-tabulation: Ethnicité x Religion
  const prepareEthnicityReligionCrossTab = (): CrossTabulationData => {
    const crossTab: CrossTabulationData = {};

    voters.forEach((voter) => {
      if (!crossTab[voter.ethnicity_immigration]) {
        crossTab[voter.ethnicity_immigration] = {};
      }
      if (!crossTab[voter.ethnicity_immigration][voter.religion]) {
        crossTab[voter.ethnicity_immigration][voter.religion] = 0;
      }
      crossTab[voter.ethnicity_immigration][voter.religion]++;
    });

    return crossTab;
  };

  // Formatage des données pour les graphiques de cross-tabulation
  const formatCrossTabData = (crossTab: CrossTabulationData) => {
    const result = [];
    for (const [primaryKey, secondaryData] of Object.entries(crossTab)) {
      for (const [secondaryKey, count] of Object.entries(secondaryData)) {
        result.push({
          primary: primaryKey.replace('_', ' '),
          secondary: secondaryKey.replace('_', ' '),
          count: count,
        });
      }
    }
    return result;
  };

  // Formatage des nombres
  const formatPercentage = (value: number, total: number) => {
    return total > 0 ? `${((value / total) * 100).toFixed(1)}%` : '0%';
  };

  const employmentFamilyData = formatCrossTabData(prepareEmploymentFamilyCrossTab());
  const ethnicityReligionData = formatCrossTabData(prepareEthnicityReligionCrossTab());

  return (
    <Container className="my-4">
      <h1 className="text-center mb-4">Voter Population Visualization</h1>

      <Card className="mb-4">
        <Card.Body>
          <Form.Group as={Row} className="align-items-center">
            <Form.Label column sm="2">
              Number of Voters:
            </Form.Label>
            <Col sm="4">
              <Form.Control
                type="number"
                value={numVoters}
                onChange={(e) => setNumVoters(parseInt(e.target.value) || 1000)}
                min="100"
                max="100000"
              />
            </Col>
            <Col sm="2">
              <Button variant="primary" onClick={handleUpdate} disabled={loading}>
                {loading ? 'Loading...' : 'Update'}
              </Button>
            </Col>
          </Form.Group>
        </Card.Body>
      </Card>

      <Row className="mb-4">
        <Col md={6}>
          <Card>
            <Card.Header>
              <Card.Title>Age Distribution</Card.Title>
            </Card.Header>
            <Card.Body>
              <div style={{ height: '300px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={ageData()}>
                    <XAxis dataKey="range" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="count" fill="#8884d8" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card.Body>
          </Card>
        </Col>

        <Col md={6}>
          <Card>
            <Card.Header>
              <Card.Title>Gender Distribution</Card.Title>
            </Card.Header>
            <Card.Body>
              <div style={{ height: '300px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={genderData()}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      fill="#8884d8"
                      label
                    >
                      {genderData().map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      <Row className="mb-4">
        <Col md={6}>
          <Card>
            <Card.Header>
              <Card.Title>Region Distribution</Card.Title>
            </Card.Header>
            <Card.Body>
              <div style={{ height: '300px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={regionData()}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      fill="#8884d8"
                      label
                    >
                      {regionData().map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </Card.Body>
          </Card>
        </Col>

        <Col md={6}>
          <Card>
            <Card.Header>
              <Card.Title>Income Distribution</Card.Title>
            </Card.Header>
            <Card.Body>
              <div style={{ height: '300px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={incomeData()}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      fill="#8884d8"
                      label
                    >
                      {incomeData().map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      <Row className="mb-4">
        <Col md={6}>
          <Card>
            <Card.Header>
              <Card.Title>Political Lean Distribution</Card.Title>
            </Card.Header>
            <Card.Body>
              <div style={{ height: '300px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={politicalLeanData()}>
                    <XAxis dataKey="range" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="count" fill="#ffc658" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card.Body>
          </Card>
        </Col>

        <Col md={6}>
          <Card>
            <Card.Header>
              <Card.Title>Party Preference Distribution</Card.Title>
            </Card.Header>
            <Card.Body>
              <div style={{ height: '300px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={partyData()}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      fill="#8884d8"
                      label
                    >
                      {partyData().map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>
      <Row className="mb-4">
        <Col md={6}>
          <Card>
            <Card.Header>
              <Card.Title>Education Distribution</Card.Title>
            </Card.Header>
            <Card.Body>
              <div style={{ height: '300px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={educationData()}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      fill="#8884d8"
                      label
                    >
                      {educationData().map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </Card.Body>
          </Card>
        </Col>

        <Col md={6}>
          <Card>
            <Card.Header>
              <Card.Title>Job Status</Card.Title>
            </Card.Header>
            <Card.Body>
              <div style={{ height: '300px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={employmentData()}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      label
                    >
                      {employmentData().map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      <Row className="mb-4">
        <Col md={6}>
          <Card>
            <Card.Header>
              <Card.Title>Statut Familial</Card.Title>
            </Card.Header>
            <Card.Body>
              <div style={{ height: '300px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={familyData()}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      label
                    >
                      {familyData().map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value: number) =>
                        `${value} (${formatPercentage(value, voters.length)})`
                      }
                    />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </Card.Body>
          </Card>
        </Col>
        <Col md={6}>
          <Card>
            <Card.Header>
              <Card.Title>Ethnicity et Immigration</Card.Title>
            </Card.Header>
            <Card.Body>
              <div style={{ height: '300px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={ethnicityData()}>
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip
                      formatter={(value: number) =>
                        `${value} (${formatPercentage(value, voters.length)})`
                      }
                    />
                    <Legend />
                    <Bar dataKey="value">
                      {ethnicityData().map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>
      <Row className="mb-4">
        <Col md={6}>
          <Card>
            <Card.Header>
              <Card.Title>Religion</Card.Title>
            </Card.Header>
            <Card.Body>
              <div style={{ height: '300px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={religionData()}>
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip
                      formatter={(value: number) =>
                        `${value} (${formatPercentage(value, voters.length)})`
                      }
                    />
                    <Legend />
                    <Bar dataKey="value">
                      {religionData().map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>
      <Row className="mb-4">
        <Col md={12}>
          <Card>
            <Card.Header>
              <Card.Title>Employment × Family status</Card.Title>
            </Card.Header>
            <Card.Body>
              <div style={{ height: '400px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={employmentFamilyData}
                    margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                  >
                    <XAxis dataKey="primary" />
                    <YAxis />
                    <Tooltip
                      formatter={(value: number) =>
                        `${value} (${formatPercentage(value, voters.length)})`
                      }
                    />
                    <Legend />
                    <Bar dataKey="count" fill="#8884d8">
                      {employmentFamilyData.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      <Row className="mb-4">
        <Col md={12}>
          <Card>
            <Card.Header>
              <Card.Title>Ethnicity × Religion</Card.Title>
            </Card.Header>
            <Card.Body>
              <div style={{ height: '400px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={ethnicityReligionData}
                    margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                  >
                    <XAxis dataKey="primary" />
                    <YAxis />
                    <Tooltip
                      formatter={(value: number) =>
                        `${value} (${formatPercentage(value, voters.length)})`
                      }
                    />
                    <Legend />
                    <Bar dataKey="count" fill="#82ca9d" name="Count">
                      {ethnicityReligionData.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* Tableau récapitulatif */}
      <Row className="mb-4">
        <Col md={12}>
          <Card>
            <Card.Header>
              <Card.Title>Resume Demographic</Card.Title>
            </Card.Header>
            <Card.Body>
              <div className="table-responsive">
                <table className="table table-striped table-bordered">
                  <thead>
                    <tr>
                      <th>Category</th>
                      <th>Employed</th>
                      <th>Jobless</th>
                      <th>Independant</th>
                      <th>Retired</th>
                      <th>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {['single', 'with_children', 'retired'].map((familyStatus) => {
                      const statusData = employmentFamilyData.filter(
                        (d) => d.secondary === familyStatus.replace('_', ' ')
                      );
                      const total = statusData.reduce((sum, item) => sum + item.count, 0);

                      return (
                        <tr key={familyStatus}>
                          <td>{familyStatus.replace('_', ' ')}</td>
                          {['employed', 'unemployed', 'self employed', 'retired'].map(
                            (employmentStatus) => {
                              const item = statusData.find(
                                (d) => d.primary === employmentStatus.replace('_', ' ')
                              );
                              return (
                                <td key={employmentStatus}>
                                  {item ? (
                                    <>
                                      {item.count}{' '}
                                      <small className="text-muted">
                                        ({formatPercentage(item.count, voters.length)})
                                      </small>
                                    </>
                                  ) : (
                                    '0'
                                  )}
                                </td>
                              );
                            }
                          )}
                          <td>
                            {total}{' '}
                            <small className="text-muted">
                              ({formatPercentage(total, voters.length)})
                            </small>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      <Row className="mb-4">
        <IssuePrioritiesVisualization voters={voters} />
      </Row>
    </Container>
  );
};

export default VoterVisualization;
