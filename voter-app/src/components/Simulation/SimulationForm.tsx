import React, { ChangeEvent } from 'react';
import { Accordion } from '@/components/ui/accordion';
import { Button } from '@/components/ui/button';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Check, Control, Range } from '@/components/ui/form-controls';
import { Col, Container } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import { Table } from '@/components/ui/table';
import { OverlayTrigger, Tooltip } from '@/components/ui/tooltip-overlay';

type Candidate = string;
type SimulationType = string;

type DemographicCategory = 'age' | 'gender' | 'location' | 'education' | 'income' | 'ideology';

type DemographicSubCategory = {
  [key: string]: number;
};

type InfluenceWeights = {
  [category: string]: {
    [subCategory: string]: {
      [candidate: string]: number;
    };
  };
};

export interface SimulationFormData {
  simulationType: SimulationType[];
  populationSize: number;
  candidates: Candidate[];
  turnoutRate: number;
  demographics: Record<DemographicCategory, DemographicSubCategory>;
  influenceWeights: InfluenceWeights;
}

interface SimulationFormProps {
  simulateVotes: () => void;
  loading: boolean;
  formData: SimulationFormData;
  setFormData: (value: SimulationFormData) => void;
}

const SimulationForm: React.FC<SimulationFormProps> = ({
  simulateVotes,
  loading,
  formData,
  setFormData,
}) => {
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, checked } = e.target;
    if (name === 'simulationType') {
      let updatedTypes = [...formData.simulationType];
      if (checked) {
        updatedTypes.push(value);
      } else {
        updatedTypes = updatedTypes.filter((type) => type !== value);
      }
      setFormData({ ...formData, simulationType: updatedTypes });
    } else {
      setFormData({
        ...formData,
        [name]: name === 'populationSize' || name === 'turnoutRate' ? parseFloat(value) : value,
      });
    }
  };

  const handleDemographicChange = (
    category: DemographicCategory,
    subCategory: string,
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const newDemographics = { ...formData.demographics };
    newDemographics[category][subCategory] = parseFloat(e.target.value);
    setFormData({ ...formData, demographics: newDemographics });
  };

  const handleInfluenceWeightChange = (
    category: string,
    subCategory: string,
    candidate: string,
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const newInfluenceWeights = { ...formData.influenceWeights };
    if (!newInfluenceWeights[category]) {
      newInfluenceWeights[category] = {};
    }
    if (!newInfluenceWeights[category][subCategory]) {
      newInfluenceWeights[category][subCategory] = {};
    }
    newInfluenceWeights[category][subCategory][candidate] = parseFloat(e.target.value);
    setFormData({ ...formData, influenceWeights: newInfluenceWeights });
  };

  const handleCandidateChange = (index: number, e: ChangeEvent<HTMLInputElement>) => {
    const newCandidates = [...formData.candidates];
    newCandidates[index] = e.target.value;
    setFormData({ ...formData, candidates: newCandidates });
  };

  const addCandidate = () => {
    setFormData({ ...formData, candidates: [...formData.candidates, ''] });
  };

  const removeCandidate = () => {
    if (formData.candidates.length > 1) {
      // Ensure at least one candidate remains
      const newCandidates = [...formData.candidates];
      newCandidates.pop(); // Remove the last candidate
      setFormData({ ...formData, candidates: newCandidates });
    } else {
      alert('You must have at least one candidate.');
    }
  };

  const renderWeightTooltip = (candidate: string) => (
    <Tooltip id={`tooltip-${candidate}`}>
      Set the influence weight for <strong>{candidate}</strong>. Higher values mean this group is
      more likely to prefer this candidate.
    </Tooltip>
  );

  return (
    <Container className="mt-4">
      <Card>
        <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
          Voting Simulation Form
        </CardHeader>
        <CardBody>
          <form className="vote-form">
            <div className="mb-3">
              <label className="mb-1 inline-block" htmlFor="simulationType-votes">
                Simulation Type
              </label>
              <Col sm={10}>
                <Check
                  type="checkbox"
                  id="simulationType-votes"
                  name="simulationType"
                  value="votes"
                  label="Standard Votes"
                  checked={formData.simulationType.includes('votes')}
                  onChange={handleInputChange}
                />
                <Check
                  type="checkbox"
                  id="simulationType-ranked"
                  name="simulationType"
                  value="ranked"
                  label="Ranked Choice"
                  checked={formData.simulationType.includes('ranked')}
                  onChange={handleInputChange}
                />
                <Check
                  type="checkbox"
                  id="simulationType-scores"
                  name="simulationType"
                  value="scores"
                  label="Score-Based (0-5)"
                  checked={formData.simulationType.includes('scores')}
                  onChange={handleInputChange}
                />
              </Col>
            </div>

            <div className="mb-3">
              <label className="mb-1 inline-block" htmlFor="populationSize">
                Population Size
              </label>
              <Col sm={10}>
                <Control
                  type="number"
                  id="populationSize"
                  name="populationSize"
                  value={formData.populationSize}
                  onChange={() => handleInputChange}
                />
              </Col>
            </div>

            <div className="mb-3">
              <label className="mb-1 inline-block" htmlFor="turnoutRate">
                Turnout Rate
              </label>
              <Col sm={10}>
                <Control
                  type="number"
                  step="0.01"
                  id="turnoutRate"
                  name="turnoutRate"
                  value={formData.turnoutRate}
                  onChange={() => handleInputChange}
                />
              </Col>
            </div>

            <div className="mb-3">
              <label className="mb-1 inline-block" htmlFor="candidate-0">
                Candidates
              </label>
              <Col sm={10}>
                {formData.candidates.map((candidate: Candidate, index: number) => (
                  <Control
                    key={index}
                    id={`candidate-${index}`}
                    type="text"
                    value={candidate}
                    onChange={(e: ChangeEvent<HTMLInputElement>) => handleCandidateChange(index, e)}
                    className="mb-2"
                  />
                ))}
                <Button variant="secondary" onClick={addCandidate}>
                  Add Candidate
                </Button>
                <Button
                  variant="danger"
                  onClick={removeCandidate}
                  disabled={formData.candidates.length <= 1}
                >
                  Remove last Candidate
                </Button>
              </Col>
            </div>

            <Card className="mb-3">
              <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
                Demographics
              </CardHeader>
              <CardBody>
                <Accordion defaultActiveKey="0">
                  {Object.entries(formData.demographics).map(([category, subCategories], index) => (
                    <Accordion.Item eventKey={index.toString()} key={category}>
                      <Accordion.Header>
                        {category.charAt(0).toUpperCase() + category.slice(1)}
                      </Accordion.Header>
                      <Accordion.Body>
                        <div className="mb-3" key={category}>
                          {Object.entries(subCategories).map(([subCategory, value]) => (
                            <div key={subCategory}>
                              <label className="mb-1 inline-block">{subCategory}</label>
                              <Col sm={10}>
                                <Control
                                  key={subCategory}
                                  type="number"
                                  step="0.01"
                                  placeholder={subCategory}
                                  value={value}
                                  onChange={(e: ChangeEvent<HTMLInputElement>) =>
                                    handleDemographicChange(
                                      category as DemographicCategory,
                                      subCategory,
                                      e
                                    )
                                  }
                                  className="mb-2"
                                />
                              </Col>
                            </div>
                          ))}
                        </div>
                      </Accordion.Body>
                    </Accordion.Item>
                  ))}
                </Accordion>
              </CardBody>
            </Card>

            <Card className="mb-3">
              <CardHeader className="block space-y-0 border-b border-border px-4 py-2 bg-slate-100">
                Influence Weights
              </CardHeader>
              <CardBody>
                <Accordion defaultActiveKey="0">
                  {Object.entries(formData.influenceWeights).map(
                    ([category, subCategories], index) => (
                      <Accordion.Item eventKey={index.toString()} key={category}>
                        <Accordion.Header>
                          {category.charAt(0).toUpperCase() + category.slice(1)}
                        </Accordion.Header>
                        <Accordion.Body>
                          {Object.entries(subCategories).map(([subCategory, candidates]) => (
                            <Accordion key={subCategory}>
                              <Accordion.Header>
                                <strong>
                                  {subCategory.charAt(0).toUpperCase() + subCategory.slice(1)}
                                </strong>
                              </Accordion.Header>
                              <Accordion.Body>
                                <Card key={subCategory} className="mb-3">
                                  <CardBody>
                                    <Table className="[&_th]:p-2 [&_td]:p-2 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_th]:border [&_td]:border [&_tbody_tr:hover]:bg-muted/50">
                                      <thead>
                                        <tr>
                                          <th>Candidate</th>
                                          <th>Weight</th>
                                          <th>Description</th>
                                        </tr>
                                      </thead>
                                      <tbody>
                                        {formData.candidates.map((candidate: Candidate) => (
                                          <tr key={candidate}>
                                            <td>{candidate}</td>
                                            <td>
                                              <Col className="mt-2">
                                                <OverlayTrigger
                                                  placement="top"
                                                  overlay={renderWeightTooltip(candidate)}
                                                >
                                                  <Range
                                                    min="0.1"
                                                    max="5"
                                                    step="0.1"
                                                    value={candidates[candidate] || 1.0}
                                                    onChange={(e) =>
                                                      handleInfluenceWeightChange(
                                                        category,
                                                        subCategory,
                                                        candidate,
                                                        e
                                                      )
                                                    }
                                                  />
                                                </OverlayTrigger>
                                              </Col>
                                              <Col className="mt-2">
                                                <small className="block text-sm text-muted-foreground">
                                                  {candidates[candidate]?.toFixed(1) || '1.0'}
                                                </small>
                                              </Col>
                                            </td>
                                            <td>
                                              {candidate === 'No Vote'
                                                ? 'Likelihood of abstaining or casting a blank vote.'
                                                : `Influence of ${subCategory} ${category} on ${candidate}'s preference.`}
                                            </td>
                                          </tr>
                                        ))}
                                      </tbody>
                                    </Table>
                                  </CardBody>
                                </Card>
                              </Accordion.Body>
                            </Accordion>
                          ))}
                        </Accordion.Body>
                      </Accordion.Item>
                    )
                  )}
                </Accordion>
              </CardBody>
            </Card>
            <Button variant="primary" onClick={simulateVotes} disabled={loading} className="mt-3">
              {loading ? <Spinner size="sm" /> : 'Run Simulation'}
            </Button>
          </form>
        </CardBody>
      </Card>
    </Container>
  );
};

export default SimulationForm;
