import React, { ChangeEvent } from 'react';
import { Form, Button, Container, Row, Col, Card, Accordion, Table, OverlayTrigger, Tooltip, Spinner } from 'react-bootstrap';

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
  setFormData: (value:SimulationFormData) => void;
}

const SimulationForm: React.FC<SimulationFormProps> = ({
  simulateVotes,
  loading,
  formData,
  setFormData
  }) => {

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, checked } = e.target;
    if (name === "simulationType") {
        let updatedTypes = [...formData.simulationType];
        if (checked) {
            updatedTypes.push(value);
        } else {
            updatedTypes = updatedTypes.filter(type => type !== value);
        }
        setFormData({ ...formData, simulationType: updatedTypes });
    } else {
    setFormData({ ...formData, [name]: name === 'populationSize' || name === 'turnoutRate' ? parseFloat(value) : value });
    }
  };

  const handleDemographicChange = (category: DemographicCategory, subCategory: string, e: React.ChangeEvent<HTMLInputElement>) => {
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
    if (formData.candidates.length > 1) { // Ensure at least one candidate remains
        const newCandidates = [...formData.candidates];
        newCandidates.pop(); // Remove the last candidate
        setFormData({ ...formData, candidates: newCandidates });
    } else {
        alert("You must have at least one candidate.");
    }
  };

  const renderWeightTooltip = (candidate: string) => (
    <Tooltip id={`tooltip-${candidate}`}>
      Set the influence weight for <strong>{candidate}</strong>. Higher values mean this group is more likely to prefer this candidate.
    </Tooltip>
  );

  return (
    <Container className="mt-4">
      <Card>
        <Card.Header as="h4">Voting Simulation Form</Card.Header>
        <Card.Body>
          <Form className="vote-form">
            <Form.Group as={Row} className="mb-3">
              <Form.Label column sm={2}>Simulation Type</Form.Label>
              <Col sm={10}>
                <Form.Check
                type="checkbox"
                id="simulationType-votes"
                name="simulationType"
                value="votes"
                label="Standard Votes"
                checked={formData.simulationType.includes("votes")}
                onChange={handleInputChange}
                />
                <Form.Check
                type="checkbox"
                id="simulationType-ranked"
                name="simulationType"
                value="ranked"
                label="Ranked Choice"
                checked={formData.simulationType.includes("ranked")}
                onChange={handleInputChange}
                />
                <Form.Check
                type="checkbox"
                id="simulationType-scores"
                name="simulationType"
                value="scores"
                label="Score-Based (0-5)"
                checked={formData.simulationType.includes("scores")}
                onChange={handleInputChange}
                />
              </Col>
            </Form.Group>

            <Form.Group as={Row} className="mb-3">
              <Form.Label column sm={2}>Population Size</Form.Label>
              <Col sm={10}>
                <Form.Control
                  type="number"
                  name="populationSize"
                  value={formData.populationSize}
                  onChange={() => handleInputChange}
                />
              </Col>
            </Form.Group>

            <Form.Group as={Row} className="mb-3">
              <Form.Label column sm={2}>Turnout Rate</Form.Label>
              <Col sm={10}>
                <Form.Control
                  type="number"
                  step="0.01"
                  name="turnoutRate"
                  value={formData.turnoutRate}
                  onChange={() => handleInputChange}
                />
              </Col>
            </Form.Group>

            <Form.Group as={Row} className="mb-3">
              <Form.Label column sm={2}>Candidates</Form.Label>
              <Col sm={10}>
                {formData.candidates.map((candidate: Candidate, index: number) => (
                  <Form.Control
                    key={index}
                    type="text"
                    value={candidate}
                    onChange={(e: ChangeEvent<HTMLInputElement>) => handleCandidateChange(index, e)}
                    className="mb-2"
                  />
                ))}
                <Button variant="secondary" onClick={addCandidate}>Add Candidate</Button>
                <Button variant="danger" 
                        onClick={removeCandidate} 
                        disabled={formData.candidates.length <= 1}>
                    Remove last Candidate
                </Button>
              </Col>
            </Form.Group>

            <Card className="mb-3">
                <Card.Header as="h5">Demographics</Card.Header>
                <Card.Body>
                <Accordion defaultActiveKey="0">
                {Object.entries(formData.demographics).map(([category, subCategories], index) => (
                    <Accordion.Item eventKey={index.toString()} key={category}>
                        <Accordion.Header>
                            {category.charAt(0).toUpperCase() + category.slice(1)}
                        </Accordion.Header>
                        <Accordion.Body>
                            <Form.Group as={Row} className="mb-3" key={category}>
                                {Object.entries(subCategories).map(([subCategory, value]) => (
                                    <Form.Group as={Row}>
                                        <Form.Label column sm={2}> 
                                            {subCategory} 
                                        </Form.Label>
                                        <Col sm={10}>
                                            <Form.Control
                                            key={subCategory}
                                            type="number"
                                            step="0.01"
                                            placeholder={subCategory}
                                            value={value}
                                            onChange={(e: ChangeEvent<HTMLInputElement>) => handleDemographicChange(category as DemographicCategory, subCategory, e)}
                                            className="mb-2"
                                            />
                                        </Col>
                                    </Form.Group>
                                ))}
                            </Form.Group>
                        </Accordion.Body>
                    </Accordion.Item>
                ))}
                </Accordion>
                </Card.Body>
            </Card>

            <Card className="mb-3">
              <Card.Header as="h5" className="bg-light">Influence Weights</Card.Header>
              <Card.Body>
                <Accordion defaultActiveKey="0">
                  {Object.entries(formData.influenceWeights).map(([category, subCategories], index) => (
                    <Accordion.Item eventKey={index.toString()} key={category}>
                      <Accordion.Header>
                        {category.charAt(0).toUpperCase() + category.slice(1)}
                      </Accordion.Header>
                      <Accordion.Body>
                        {Object.entries(subCategories).map(([subCategory, candidates]) => (
                          <Accordion>
                            <Accordion.Header>
                                <strong>{subCategory.charAt(0).toUpperCase() + subCategory.slice(1)}</strong>
                            </Accordion.Header>
                            <Accordion.Body>
                                <Card key={subCategory} className="mb-3">
                                <Card.Body>
                                <Table bordered hover>
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
                                            <Col className='mt-2'>
                                                <OverlayTrigger
                                                placement="top"
                                                overlay={renderWeightTooltip(candidate)}
                                                >
                                                <Form.Range
                                                    min="0.1"
                                                    max="5"
                                                    step="0.1"
                                                    value={candidates[candidate] || 1.0}
                                                    onChange={(e) => handleInfluenceWeightChange(category, subCategory, candidate, e)}
                                                />
                                                </OverlayTrigger>
                                            </Col>
                                            <Col className='mt-2'>
                                                <Form.Text>
                                                    {candidates[candidate]?.toFixed(1) || '1.0'}
                                                </Form.Text>
                                            </Col>
                                            
                                        </td>
                                        <td>
                                            {candidate === 'No Vote' ?
                                            'Likelihood of abstaining or casting a blank vote.' :
                                            `Influence of ${subCategory} ${category} on ${candidate}'s preference.`}
                                        </td>
                                        </tr>
                                    ))}
                                    </tbody>
                                </Table>
                                </Card.Body>
                                </Card>
                            </Accordion.Body>
                            </Accordion>
                          
                        ))}
                      </Accordion.Body>
                    </Accordion.Item>
                  ))}
                </Accordion>
              </Card.Body>
            </Card>
            <Button variant="primary" onClick={simulateVotes} disabled={loading} className="mt-3">
              {loading ? <Spinner animation="border" size="sm" /> : 'Run Simulation'}
            </Button>
          </Form>
        </Card.Body>
      </Card>
    </Container>
  );
};

export default SimulationForm;