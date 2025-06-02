import React, { useEffect, useState } from 'react';
import { Form, Button, Spinner, Accordion, Row, Col } from 'react-bootstrap';
import './FormStyles.css'; 
import { Scatterplot } from '../Chart/Scatterplot';
import { Hexbin } from '../Chart/Hexbin';
import { simulatePop } from '../../services/api';

interface SimulationFormProps {
  numVoters: number;
  setNumVoters: (value: number) => void;
  numCandidates: number;
  setNumCandidates: (value: number) => void;
  simulateVotes: () => void;
  loading: boolean;
}
interface party {
  name:string;
}

interface candidate {
  name: string;
  party: party;
}

interface cData {
  group: string;
  x: number;
  y: number;
  size: number;
}

interface vData {
  // group: string;
  x:number;
  y:number;
  //size: number;
}

interface formData {
  candidates: candidate[];
  parties: party[]
}

const MIN_CANDIDATES = 1;
const MAX_CANDIDATES = 10;
const MAX_PARTIES =10;

const SimulationForm: React.FC<SimulationFormProps> = ({
  numVoters,
  setNumVoters,
  numCandidates,
  setNumCandidates,
  simulateVotes,
  loading,
}) => {
  
  const [candidates, setCandidates] = useState<[]>([]);
  const [numParties, setNumParties] = useState<number>(0);
  const [showParties, setShowParties] = useState(false);
  const [partyName, setPartyName] = useState<string>("");
  const [averageAge, setAverageAge] = useState<number>(0);
  const [allo, setAllo] = useState<number>(0);
  const [candidateData, setCandidateData] = useState<cData[]>([]);
  const [voterData, setVoterData] = useState<vData[]>([]);
  const [error, setError] = useState<string | null>(null);

  const generateRandomData = (numCandidates: number): cData[] => {
    const candidateData = [];
    for (let i = 0; i < numCandidates; i++) {
      const randomX = Math.random() * 10 - 5;
      const randomY = Math.random() * 10 - 5;

      candidateData.push({
        group: `Candidate n${i + 1}`,
        x: parseFloat(randomX.toFixed(2)), // Random value between -1 and 1
        y: parseFloat(randomY.toFixed(2)), // Random value between -1 and 1
        size: Math.random() * 400, // Random size for visualization
      });
    }
    return candidateData;
  };


  useEffect(() => {
    setCandidateData(generateRandomData(numCandidates));
  }, [numCandidates])

  useEffect(() => {
    const loadVoterData = async () => {
        try {
            const votersData = await simulatePop(numVoters, averageAge);
                setVoterData(votersData);
        } catch (error) {
            setError('Failed to fetch the voters data:');
        }
    };
    loadVoterData();
  }, [numVoters, averageAge])

  return (
    <Form className="vote-form">
      <Accordion defaultActiveKey="0">
        <Accordion.Item eventKey="0">
          <Accordion.Header>Voters Information</Accordion.Header>
          <Accordion.Body>
            <Row>
              <Col>
                <Form.Group controlId="formNumVoters" className="mb-3">
                  <Form.Label>Number of Voters:</Form.Label>
                  <Form.Control
                    type="number"
                    value={numVoters}
                    onChange={(e) => setNumVoters(Number(e.target.value))}
                  />
                </Form.Group>
              </Col>
              <Col>
                <Form.Group>
                  <Form.Label>Average age of voters</Form.Label>
                  <Form.Control 
                    type="number"
                    value={averageAge}
                    onChange={(e) => setAverageAge(Number(e.target.value))}
                  />
                </Form.Group>
              </Col>
              <Col>
                <Form.Group>
                  <Form.Label>Allo</Form.Label>
                  <Form.Control
                    type="number"
                    value={allo}
                    onChange={(e) => setAllo(Number(e.target.value))}
                  />
                </Form.Group>
              </Col>
            </Row>
            <Row>
              <Col></Col>
              <Col>
                <Hexbin data={voterData} width={400} height={400} />
              </Col>
              <Col></Col>
            </Row>
          </Accordion.Body>
        </Accordion.Item>
        <Accordion.Item eventKey="1">
          <Accordion.Header> Candidates </Accordion.Header>
          <Accordion.Body>
            <Form.Group controlId="formNumCandidates" className="mb-3">
              <Form.Label>Number of Candidates:</Form.Label>
              <Form.Control
                type="number"
                value={numCandidates}
                onChange={(e) => setNumCandidates(Number(e.target.value))}
                min= {MIN_CANDIDATES}
                max= {MAX_CANDIDATES}
              />
            </Form.Group>
            <Form.Group className='mb-3'>
              <Form.Check 
                type="checkbox" 
                id="isCheck" 
                label="Is the number of candidates different of the number of political parties"
                checked={showParties}
                onChange={(e) => setShowParties(e.target.checked)}
                />
            </Form.Group>
            <Row>
              <Col></Col>
              <Col>
                <Hexbin data={candidateData} width={400} height={400} />
              </Col>
              <Col></Col>
            </Row>
          </Accordion.Body>
        </Accordion.Item>
      {showParties ? (
        <Accordion.Item eventKey="2">
          <Accordion.Header>Parties configuration</Accordion.Header>
          <Accordion.Body>
            <div>
              <Form.Group className='mb-3'>
                <Form.Label>Number of political parties</Form.Label>
                <Form.Control
                type="number"
                value={numParties}
                onChange={(e) => setNumParties(Number(e.target.value))}
                min={MIN_CANDIDATES}
                max={MAX_PARTIES}
              />
              </Form.Group>
              <div className='party-grid'>
                {Array.from({ length: numParties}, (_, index)  => (
                  <div key={index} className='party-group mb-3'>
                    <Form.Group >
                      <Form.Label>Party n°{index}</Form.Label>                  
                    </Form.Group>
                    <Form.Group controlId={`formPartyPlatform${index}`}>
                      <Form.Label>Name of the party:</Form.Label>
                      <Form.Control
                        type="text"
                        value={partyName[index] || ''}
                        onChange={(e) => setPartyName((e.target.value))}
                      />
                    </Form.Group>  
                  </div>
                ))}
              </div>
            </div>
          </Accordion.Body>
        </Accordion.Item>
      ): (
        <Accordion.Item eventKey="3">
          <Accordion.Header>Parties config</Accordion.Header>
          <Accordion.Body>
            <div className='party-grid'>
              {Array.from({ length: numCandidates}, (_, index)  => (
                  <div key={index} className='party-group mb-3'>
                    <Form.Group >
                      <Form.Label>Party n°{index}</Form.Label>                  
                    </Form.Group>
                    <Form.Group controlId={`formPartyPlatform${index}`}>
                      <Form.Label>Name of the party:</Form.Label>
                      <Form.Control
                        type="text"
                        value={partyName[index] || ''}
                        onChange={(e) => setPartyName((e.target.value))}
                      />
                    </Form.Group>  
                  </div>
                ))}
            </div>
          </Accordion.Body>
        </Accordion.Item>
      )}
        <Accordion.Item eventKey="4">
          <Accordion.Header>Candidates description</Accordion.Header>
          <Accordion.Body>
            <Form.Group className='mb-3'>
              <Form.Label>Description of the candidates</Form.Label>
            </Form.Group>
            <div className='candidate-grid'>
              {Array.from({ length: numCandidates}, (_, index)  => (
                <div key={index} className='candidate-group mb-3'>
                  <Form.Group >
                    <Form.Label>Candidate n°{index}</Form.Label>  
                  </Form.Group>
                  <Form.Group controlId={`formCandidatePlatform${index}`}>
                    <Form.Label>Candidate party:</Form.Label>
                    <Form.Select>
                      {Array.from({length: numParties}, (_, index) => (
                          <option> Partie n°{index} </option>
                      ))}
                    </Form.Select>
                  </Form.Group>  
                </div>
              ))}
            </div>
          </Accordion.Body>
        </Accordion.Item>
      </Accordion>
      <Button variant="primary" onClick={simulateVotes} disabled={loading} className="mt-3">
        {loading ? <Spinner animation="border" size="sm" /> : 'Simulate Votes'}
      </Button>
    </Form>
  );
};

export default SimulationForm;