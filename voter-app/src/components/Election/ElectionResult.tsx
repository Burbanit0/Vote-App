// components/ElectionResults.tsx
import React, { useState, useEffect } from 'react';
import { Card, Tabs, Tab, Table, Alert, Spinner } from 'react-bootstrap';
import { Bar } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js';
import { fetchElectionResults } from '../../services';

// Register ChartJS components
ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

interface ElectionResult {
  candidate: string;
  votes: number;
}

interface ElectionResults {
  [key: string]: ElectionResult[];
}

interface ElectionResultsProps {
  electionId: number;
}

const ElectionResults: React.FC<ElectionResultsProps> = ({ electionId }) => {
  const [results, setResults] = useState<ElectionResults | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [electionDetails, setElectionDetails] = useState({
    name: '',
    votingMethod: '',
    totalVotes: 0,
    startDate: '',
    endDate: ''
  });

  useEffect(() => {
    const fetchResults = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const response = await fetchElectionResults(electionId);
        setResults(response.results);
        setElectionDetails({
          name: response.election_name,
          votingMethod: response.voting_method,
          totalVotes: response.total_votes,
          startDate: response.start_date,
          endDate: response.end_date
        });
      } catch (err) {
        setError('Failed to fetch election results');
        console.error('Error fetching election results:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchResults();
  }, [electionId]);

  if (isLoading) {
    return (
      <Card>
        <Card.Body className="text-center">
          <Spinner animation="border" role="status">
            <span className="visually-hidden">Loading...</span>
          </Spinner>
        </Card.Body>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <Card.Body>
          <Alert variant="danger">{error}</Alert>
        </Card.Body>
      </Card>
    );
  }

  if (!results) {
    return (
      <Card>
        <Card.Body>
          <Alert variant="info">No results available for this election</Alert>
        </Card.Body>
      </Card>
    );
  }

  const votingMethods = Object.keys(results).filter(method => method !== 'overall');

  return (
    <Card>
      <Card.Body>
        <Card.Title>Election Results: {electionDetails.name}</Card.Title>

        <Card.Text className="mb-3">
          <strong>Voting Method:</strong> {electionDetails.votingMethod}<br/>
          <strong>Total Votes:</strong> {electionDetails.totalVotes}<br/>
          <strong>Period:</strong> {new Date(electionDetails.startDate).toLocaleString()} to {new Date(electionDetails.endDate).toLocaleString()}
        </Card.Text>

        <Tabs defaultActiveKey="overall" id="results-tabs" className="mb-3">
          <Tab eventKey="overall" title="Overall Results">
            <div className="mt-3">
              <h5>Overall Results</h5>
              <div className="mb-4">
                <Table striped bordered hover>
                  <thead>
                    <tr>
                      <th>Candidate</th>
                      <th>Votes</th>
                      <th>Percentage</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results['overall'].map((result, index) => (
                      <tr key={index}>
                        <td>{result.candidate}</td>
                        <td>{result.votes}</td>
                        <td>{((result.votes / electionDetails.totalVotes) * 100).toFixed(2)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </div>

              <div style={{ height: '400px' }}>
                <Bar
                  data={{
                    labels: results['overall'].map(result => result.candidate),
                    datasets: [{
                      label: 'Votes',
                      data: results['overall'].map(result => result.votes),
                      backgroundColor: 'rgba(54, 162, 235, 0.5)',
                      borderColor: 'rgba(54, 162, 235, 1)',
                      borderWidth: 1
                    }]
                  }}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                      y: {
                        beginAtZero: true
                      }
                    },
                    plugins: {
                      title: {
                        display: true,
                        text: 'Overall Voting Results'
                      }
                    }
                  }}
                />
              </div>
            </div>
          </Tab>

          {votingMethods.map(method => (
            <Tab key={method} eventKey={method} title={method.charAt(0).toUpperCase() + method.slice(1)}>
              <div className="mt-3">
                <h5>{method.charAt(0).toUpperCase() + method.slice(1)} Results</h5>
                <div className="mb-4">
                  <Table striped bordered hover>
                    <thead>
                      <tr>
                        <th>Candidate</th>
                        <th>Votes</th>
                        <th>Percentage</th>
                      </tr>
                    </thead>
                    <tbody>
                      {results[method].map((result, index) => {
                        const methodTotal = results[method].reduce((sum, r) => sum + r.votes, 0);
                        return (
                          <tr key={index}>
                            <td>{result.candidate}</td>
                            <td>{result.votes}</td>
                            <td>{((result.votes / methodTotal) * 100).toFixed(2)}%</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </Table>
                </div>

                <div style={{ height: '400px' }}>
                  <Bar
                    data={{
                      labels: results[method].map(result => result.candidate),
                      datasets: [{
                        label: 'Votes',
                        data: results[method].map(result => result.votes),
                        backgroundColor: 'rgba(75, 192, 192, 0.5)',
                        borderColor: 'rgba(75, 192, 192, 1)',
                        borderWidth: 1
                      }]
                    }}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      scales: {
                        y: {
                          beginAtZero: true
                        }
                      },
                      plugins: {
                        title: {
                          display: true,
                          text: `${method.charAt(0).toUpperCase() + method.slice(1)} Voting Results`
                        }
                      }
                    }}
                  />
                </div>
              </div>
            </Tab>
          ))}
        </Tabs>
      </Card.Body>
    </Card>
  );
};

export default ElectionResults;
