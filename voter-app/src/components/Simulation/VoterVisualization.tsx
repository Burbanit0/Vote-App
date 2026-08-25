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
import { Button } from '@/components/ui/button';
import { Card, CardBody, CardHeader, CardTitle } from '@/components/ui/card';
import { Control } from '@/components/ui/form-controls';
import { Col, Container, Row } from '@/components/ui/grid';
import { useTranslation } from 'react-i18next';
import { simulateVoters } from '../../services';
import IssuePrioritiesVisualization from './IssuePrioritiesVisualization';
import { Region, Income, PartySimu, Family, Ethnicity, Religion, Employement } from '../../types';
import { useSimulation } from '../../stores/useSimuStore';

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

interface DemographicPieCardProps {
  title: string;
  data: ChartData[];
  tooltipFormatter?: (value: number) => string;
}

// One demographic breakdown, as a pie: title + 300px chart. Every slice gets
// its own <Cell>, so the <Pie>'s own `fill` never actually shows — that let
// the seven call sites drift (some passed it, some didn't) with no visible
// effect either way.
const DemographicPieCard: React.FC<DemographicPieCardProps> = ({
  title,
  data,
  tooltipFormatter,
}) => (
  <Card>
    <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
      <CardTitle>{title}</CardTitle>
    </CardHeader>
    <CardBody>
      <div style={{ height: '300px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={80}
              label
            >
              {data.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip formatter={tooltipFormatter} />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </CardBody>
  </Card>
);

const VoterVisualization: React.FC = () => {
  const { t } = useTranslation();
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
      <h1 className="text-center mb-4">{t('simulation.voterViz.pageTitle')}</h1>

      <Card className="mb-4">
        <CardBody>
          <Row className="items-center">
            <Col sm="2">
              <label className="mb-1 inline-block">{t('simulation.voterViz.numVoters')}</label>
            </Col>
            <Col sm="4">
              <Control
                type="number"
                value={numVoters}
                onChange={(e) => setNumVoters(parseInt(e.target.value) || 1000)}
                min="100"
                max="100000"
              />
            </Col>
            <Col sm="2">
              <Button variant="primary" onClick={handleUpdate} disabled={loading}>
                {loading ? t('simulation.voterViz.loading') : t('simulation.voterViz.update')}
              </Button>
            </Col>
          </Row>
        </CardBody>
      </Card>

      <Row className="mb-4">
        <Col md={6}>
          <Card>
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
              <CardTitle>{t('simulation.voterViz.ageDist')}</CardTitle>
            </CardHeader>
            <CardBody>
              <div style={{ height: '300px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={ageData()}>
                    <XAxis dataKey="range" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="count" fill="#1a56cc" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardBody>
          </Card>
        </Col>

        <Col md={6}>
          <DemographicPieCard title={t('simulation.voterViz.genderDist')} data={genderData()} />
        </Col>
      </Row>

      <Row className="mb-4">
        <Col md={6}>
          <DemographicPieCard title={t('simulation.voterViz.regionDist')} data={regionData()} />
        </Col>

        <Col md={6}>
          <DemographicPieCard title={t('simulation.voterViz.incomeDist')} data={incomeData()} />
        </Col>
      </Row>

      <Row className="mb-4">
        <Col md={6}>
          <Card>
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
              <CardTitle>{t('simulation.voterViz.politicalLean')}</CardTitle>
            </CardHeader>
            <CardBody>
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
            </CardBody>
          </Card>
        </Col>

        <Col md={6}>
          <DemographicPieCard title={t('simulation.voterViz.partyPref')} data={partyData()} />
        </Col>
      </Row>
      <Row className="mb-4">
        <Col md={6}>
          <DemographicPieCard
            title={t('simulation.voterViz.educationDist')}
            data={educationData()}
          />
        </Col>

        <Col md={6}>
          <DemographicPieCard title={t('simulation.voterViz.jobStatus')} data={employmentData()} />
        </Col>
      </Row>

      <Row className="mb-4">
        <Col md={6}>
          <DemographicPieCard
            title={t('simulation.voterViz.familyStatus')}
            data={familyData()}
            tooltipFormatter={(value: number) =>
              `${value} (${formatPercentage(value, voters.length)})`
            }
          />
        </Col>
        <Col md={6}>
          <Card>
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
              <CardTitle>{t('simulation.voterViz.ethnicityImmigration')}</CardTitle>
            </CardHeader>
            <CardBody>
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
            </CardBody>
          </Card>
        </Col>
      </Row>
      <Row className="mb-4">
        <Col md={6}>
          <Card>
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
              <CardTitle>{t('simulation.voterViz.religion')}</CardTitle>
            </CardHeader>
            <CardBody>
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
            </CardBody>
          </Card>
        </Col>
      </Row>
      <Row className="mb-4">
        <Col md={12}>
          <Card>
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
              <CardTitle>{t('simulation.voterViz.employmentXFamily')}</CardTitle>
            </CardHeader>
            <CardBody>
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
                    <Bar dataKey="count" fill="#1a56cc">
                      {employmentFamilyData.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardBody>
          </Card>
        </Col>
      </Row>

      <Row className="mb-4">
        <Col md={12}>
          <Card>
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
              <CardTitle>{t('simulation.voterViz.ethnicityXReligion')}</CardTitle>
            </CardHeader>
            <CardBody>
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
                    <Bar dataKey="count" fill="#1b5e20" name="Count">
                      {ethnicityReligionData.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardBody>
          </Card>
        </Col>
      </Row>

      {/* Tableau récapitulatif */}
      <Row className="mb-4">
        <Col md={12}>
          <Card>
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
              <CardTitle>{t('simulation.voterViz.resumeDemographic')}</CardTitle>
            </CardHeader>
            <CardBody>
              <div className="table-responsive">
                <table className="table table-striped table-bordered">
                  <thead>
                    <tr>
                      <th>{t('simulation.voterViz.category')}</th>
                      <th>{t('simulation.voterViz.employed')}</th>
                      <th>{t('simulation.voterViz.unemployed')}</th>
                      <th>{t('simulation.voterViz.selfEmployed')}</th>
                      <th>{t('simulation.voterViz.retired')}</th>
                      <th>{t('simulation.voterViz.total')}</th>
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
                                      <small className="text-muted-foreground">
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
                            <small className="text-muted-foreground">
                              ({formatPercentage(total, voters.length)})
                            </small>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </CardBody>
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
