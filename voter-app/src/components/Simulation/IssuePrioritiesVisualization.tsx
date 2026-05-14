import React, { useState } from 'react';
import { Card, Row, Col, Form } from 'react-bootstrap';
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

interface IssuePrioritiesVisualizationProps {
  voters: Array<{
    age: number;
    region: string;
    income: string;
    gender: string;
    education: string;
    political_lean: number;
    issue_priorities: Record<string, number>;
    party_loyalty: number;
    preferred_party: string;
    likelihood_to_vote: number;
    mood: number;
  }>;
}

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

const IssuePrioritiesVisualization: React.FC<IssuePrioritiesVisualizationProps> = ({ voters }) => {
  const { t } = useTranslation();
  const [selectedGroup, setSelectedGroup] = useState<
    'age' | 'region' | 'income' | 'gender' | 'education'
  >('education');
  const [showRadar, setShowRadar] = useState(true);

  // Préparer les données pour le bar chart (moyennes par groupe)
  const prepareGroupData = () => {
    if (voters.length === 0) return { data: [], issues: [] };

    // Créer des groupes d'âge pour la visualisation
    if (selectedGroup === 'age') {
      const ageGroups = [
        { name: '18-24', min: 18, max: 24 },
        { name: '25-34', min: 25, max: 34 },
        { name: '35-44', min: 35, max: 44 },
        { name: '45-54', min: 45, max: 54 },
        { name: '55-64', min: 55, max: 64 },
        { name: '65+', min: 65, max: 120 },
      ];

      const issues = Object.keys(voters[0].issue_priorities);

      return {
        data: ageGroups
          .map((group) => {
            const groupVoters = voters.filter(
              (voter) => voter.age >= group.min && voter.age <= group.max
            );
            if (groupVoters.length === 0) return null;

            const avgPriorities: Record<string, number> = {};
            issues.forEach((issue) => {
              avgPriorities[issue] =
                groupVoters.reduce((sum, voter) => sum + (voter.issue_priorities[issue] || 0), 0) /
                groupVoters.length;
            });

            return { group: group.name, ...avgPriorities };
          })
          .filter(Boolean) as Array<Record<string, number> & { group: string }>,
        issues,
      };
    }

    // Pour les autres groupes
    const groupValues = [...new Set(voters.map((voter) => voter[selectedGroup]))] as string[];
    const issues = Object.keys(voters[0].issue_priorities);

    return {
      data: groupValues
        .map((groupValue) => {
          const groupVoters = voters.filter((voter) => voter[selectedGroup] === groupValue);
          if (groupVoters.length === 0) return null;

          const avgPriorities: Record<string, number> = {};
          issues.forEach((issue) => {
            avgPriorities[issue] =
              groupVoters.reduce((sum, voter) => sum + (voter.issue_priorities[issue] || 0), 0) /
              groupVoters.length;
          });

          return { group: groupValue, ...avgPriorities };
        })
        .filter(Boolean) as Array<Record<string, number> & { group: string }>,
      issues,
    };
  };

  // Préparer les données pour le radar chart
  const prepareRadarData = () => {
    if (voters.length === 0) return { average: null, profiles: [] };

    const issues = Object.keys(voters[0].issue_priorities);

    // Profil moyen
    const averageProfile: Record<string, number> = {};
    issues.forEach((issue) => {
      averageProfile[issue] =
        voters.reduce((sum, voter) => sum + (voter.issue_priorities[issue] || 0), 0) /
        voters.length;
    });

    // Profils par groupe d'âge
    const ageGroups = [
      { name: '18-29', min: 18, max: 29 },
      { name: '30-44', min: 30, max: 44 },
      { name: '45-59', min: 45, max: 59 },
      { name: '60+', min: 60, max: 120 },
    ];

    const profiles = ageGroups
      .map((group) => {
        const groupVoters = voters.filter(
          (voter) => voter.age >= group.min && voter.age <= group.max
        );
        if (groupVoters.length === 0) return null;

        const profile: Record<string, number> = {};
        issues.forEach((issue) => {
          profile[issue] =
            groupVoters.reduce((sum, voter) => sum + (voter.issue_priorities[issue] || 0), 0) /
            groupVoters.length;
        });
        return { name: group.name, ...profile };
      })
      .filter(Boolean) as Array<Record<string, number> & { name: string }>;

    return {
      average: { name: 'Moyenne', ...averageProfile },
      profiles,
    };
  };

  const { data: groupData, issues } = prepareGroupData();
  const { average, profiles } = prepareRadarData();

  // Données pour le radar chart
  const radarData = average ? [average, ...profiles] : [];

  // Données pour le bar chart simple
  const priorityRanking =
    issues
      ?.map((issue) => ({
        issue: issue.replace('_', ' '),
        average:
          voters.reduce((sum, voter) => sum + (voter.issue_priorities[issue] || 0), 0) /
          voters.length,
      }))
      .sort((a, b) => b.average - a.average) || [];

  return (
    <Card className="mb-4">
      <Card.Header>
        <Card.Title>{t('simulation.issuePriorities.title')}</Card.Title>
      </Card.Header>
      <Card.Body>
        <Form.Group as={Row} className="mb-3 align-items-center">
          <Form.Label column sm={2}>
            {t('simulation.issuePriorities.groupBy')}
          </Form.Label>
          <Col sm={3}>
            <Form.Select
              value={selectedGroup}
              onChange={(e) =>
                setSelectedGroup(
                  e.target.value as 'age' | 'region' | 'income' | 'gender' | 'education'
                )
              }
            >
              <option value="education">{t('simulation.issuePriorities.groupEducation')}</option>
              <option value="age">{t('simulation.issuePriorities.groupAge')}</option>
              <option value="region">{t('simulation.issuePriorities.groupRegion')}</option>
              <option value="income">{t('simulation.issuePriorities.groupIncome')}</option>
              <option value="gender">{t('simulation.issuePriorities.groupGender')}</option>
            </Form.Select>
          </Col>
          <Col sm={3}>
            <Form.Check
              type="switch"
              id="radar-switch"
              label={t('simulation.issuePriorities.showRadar')}
              checked={showRadar}
              onChange={() => setShowRadar(!showRadar)}
            />
          </Col>
        </Form.Group>

        <Row>
          <Col md={showRadar ? 6 : 12}>
            <Card>
              <Card.Header>
                <Card.Title>
                  {t('simulation.issuePriorities.avgPrioritiesBy')}{' '}
                  {{
                    age: t('simulation.issuePriorities.byAgeGroup'),
                    region: t('simulation.issuePriorities.byRegion'),
                    income: t('simulation.issuePriorities.byIncome'),
                    gender: t('simulation.issuePriorities.byGender'),
                    education: t('simulation.issuePriorities.byEducation'),
                  }[selectedGroup]}
                </Card.Title>
              </Card.Header>
              <Card.Body>
                {groupData.length > 0 ? (
                  <div style={{ height: '400px' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        layout="vertical"
                        data={groupData}
                        margin={{ top: 20, right: 30, left: 50, bottom: 5 }}
                      >
                        <XAxis type="number" domain={[0, 0.3]} />
                        <YAxis dataKey="group" type="category" />
                        <Tooltip
                          formatter={(value: number) => [
                            `${(value * 100).toFixed(1)}%`,
                            t('simulation.issuePriorities.priority'),
                          ]}
                        />
                        <Legend />
                        {issues?.map((issue, index) => (
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
                ) : (
                  <p className="text-center text-muted">Pas de données disponibles</p>
                )}
              </Card.Body>
            </Card>
          </Col>

          {showRadar && (
            <Col md={6}>
              <Card>
                <Card.Header>
                  <Card.Title>{t('simulation.issuePriorities.ageProfilesTitle')}</Card.Title>
                </Card.Header>
                <Card.Body>
                  {radarData.length > 0 ? (
                    <div style={{ height: '400px' }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <RadarChart data={radarData}>
                          <PolarGrid />
                          <PolarAngleAxis dataKey="name" />
                          <PolarRadiusAxis angle={30} domain={[0, 0.3]} />
                          {issues?.map((issue, index) => (
                            <Radar
                              key={issue}
                              dataKey={issue}
                              stroke={COLORS[index % COLORS.length]}
                              fill={COLORS[index % COLORS.length]}
                              fillOpacity={0.6}
                              name={issue.replace('_', ' ')}
                            />
                          ))}
                          <Legend />
                          <Tooltip
                            formatter={(value: number) => [
                              `${(value * 100).toFixed(1)}%`,
                            t('simulation.issuePriorities.priority'),
                          ]}
                        />
                      </RadarChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                  <p className="text-center text-muted">{t('simulation.issuePriorities.noData')}</p>
                  )}
                </Card.Body>
              </Card>
            </Col>
          )}
        </Row>

        <Row className="mt-4">
          <Col md={12}>
            <Card>
              <Card.Header>
                <Card.Title>{t('simulation.issuePriorities.globalRankingTitle')}</Card.Title>
              </Card.Header>
              <Card.Body>
                {priorityRanking.length > 0 ? (
                  <div style={{ height: '300px' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={priorityRanking}
                        margin={{ top: 20, right: 30, left: 20, bottom: 50 }}
                      >
                        <XAxis
                          dataKey="issue"
                          angle={-45}
                          textAnchor="end"
                          height={100}
                          interval={0}
                        />
                        <YAxis
                          domain={[0, 0.3]}
                          tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
                        />
                        <Tooltip
                          formatter={(value: number) => [
                            `${(value * 100).toFixed(1)}%`,
                            t('simulation.issuePriorities.avgPriority'),
                          ]}
                        />
                        <Bar dataKey="average">
                          {priorityRanking.map((_, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <p className="text-center text-muted">Pas de données disponibles</p>
                )}
              </Card.Body>
            </Card>
          </Col>
        </Row>
      </Card.Body>
    </Card>
  );
};

export default IssuePrioritiesVisualization;
