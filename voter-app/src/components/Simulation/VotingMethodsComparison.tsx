// VotingMethodsComparison.tsx
import React from 'react';
import { Accordion } from 'react-bootstrap';
import VotingMethodVisualizations from './VotingMethodVisualizations';

type VotingMethodKey =
  | 'plurality'
  | 'borda'
  | 'irv'
  | 'approval'
  | 'condorcet'
  | 'two_round'
  | 'coombs'
  | 'score'
  | 'bucklin'
  | 'minimax'
  | 'schulze'
  | 'kemeny_young';

interface VotingMethod {
  key: VotingMethodKey;
  name: string;
  winnerKey: `${VotingMethodKey}_winner`;
}

interface VotingMethodsComparisonProps {
  rankings: Array<{ voter_id: number; ranking: string[] }>;
  candidates: string[];
  winners: {
    condorcet_winner?: string;
    two_round_winner?: string;
    borda_winner?: string;
    plurality_winner?: string;
    approval_winner?: string;
    irv_winner?: string;
    coombs_winner?: string;
    score_winner?: string;
    bucklin_winner?: string;
    minimax_winner?: string;
    schulze_winner?: string;
    kemeny_young_winner?: string;
  };
}

const VotingMethodsComparison: React.FC<VotingMethodsComparisonProps> = ({
  rankings,
  candidates,
  winners
}) => {
  // List of all voting methods with their display names and keys
   const votingMethods: VotingMethod[] = [
    { key: 'plurality', name: 'Plurality', winnerKey: 'plurality_winner' },
    { key: 'borda', name: 'Borda Count', winnerKey: 'borda_winner' },
    { key: 'irv', name: 'Instant Runoff Voting', winnerKey: 'irv_winner' },
    { key: 'approval', name: 'Approval Voting', winnerKey: 'approval_winner' },
    { key: 'condorcet', name: 'Condorcet', winnerKey: 'condorcet_winner' },
    { key: 'two_round', name: 'Two-Round System', winnerKey: 'two_round_winner' },
    { key: 'coombs', name: "Coombs' Method", winnerKey: 'coombs_winner' },
    { key: 'score', name: 'Score Voting', winnerKey: 'score_winner' },
    { key: 'bucklin', name: 'Bucklin Voting', winnerKey: 'bucklin_winner' },
    { key: 'minimax', name: 'Minimax', winnerKey: 'minimax_winner' },
    { key: 'schulze', name: 'Schulze Method', winnerKey: 'schulze_winner' },
    { key: 'kemeny_young', name: 'Kemeny-Young', winnerKey: 'kemeny_young_winner' }
  ];

  return (
    <div className="mt-4">
      <h3>Voting Method Comparison</h3>

      {/* Summary of winners */}
      <div className="card mb-4">
        <div className="card-header">
          <h5>Winners Summary</h5>
        </div>
        <div className="card-body">
          <div className="row">
            {votingMethods.map((method) => (
              winners[method.winnerKey] && (
                <div key={method.key} className="col-md-4 mb-3">
                  <div className="card h-100">
                    <div className="card-body">
                      <h6 className="card-title">{method.name}</h6>
                      <p className="card-text">
                        <strong>Winner:</strong> {winners[method.winnerKey]}
                      </p>
                    </div>
                  </div>
                </div>
              )
            ))}
          </div>
        </div>
      </div>

      {/* Detailed visualizations for each method */}
      <Accordion defaultActiveKey="0" alwaysOpen>
        {votingMethods.map((method, index) => (
          <Accordion.Item key={method.key} eventKey={index.toString()}>
            <Accordion.Header>
              {method.name} {winners[method.winnerKey] && ` - Winner: ${winners[method.winnerKey]}`}
            </Accordion.Header>
            <Accordion.Body>
              <VotingMethodVisualizations
                method={method.key}
                rankings={rankings}
                candidates={candidates}
              />
            </Accordion.Body>
          </Accordion.Item>
        ))}
      </Accordion>
    </div>
  );
};

export default VotingMethodsComparison;
