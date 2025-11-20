// useScoreVotingResults.ts
import { useMemo } from 'react';
import { ScoreVote, ScoreVotingResults } from '../../types';

export function useScoreVotingResults(
  scores: ScoreVote[],
  candidates: string[]
): ScoreVotingResults {
  return useMemo(() => {
    // 1. Simple Score Voting
    const simpleScoreResult = calculateSimpleScore(scores, candidates);

    // 2. STAR Voting
    const starVotingResult = calculateSTARVoting(scores, candidates);

    // 3. Median Voting
    const medianVotingResult = calculateMedianVoting(scores, candidates);

    // 4. Mean-Median Hybrid
    const meanMedianHybridResult = calculateMeanMedianHybrid(scores, candidates);

    // 5. Variance-Based
    const varianceBasedResult = calculateVarianceBased(scores, candidates);

    // 6. Score Distribution Analysis
    const scoreDistributionResult = calculateScoreDistribution(scores, candidates);

    // 7. Bayesian Regret
    const bayesianRegretResult = calculateBayesianRegret(scores, candidates);

    return {
      simple_score: simpleScoreResult,
      star_voting: starVotingResult,
      median_voting: medianVotingResult,
      mean_median_hybrid: meanMedianHybridResult,
      variance_based: varianceBasedResult,
      score_distribution: scoreDistributionResult,
      bayesian_regret: bayesianRegretResult,
    };
  }, [scores, candidates]);
}

function calculateSimpleScore(scores: ScoreVote[], candidates: string[]) {
  const candidateScores = candidates.reduce(
    (acc, candidate) => {
      acc[candidate] = { sum: 0, count: 0 };
      return acc;
    },
    {} as Record<string, { sum: number; count: number }>
  );

  scores.forEach(({ scores: voterScores }) => {
    candidates.forEach((candidate) => {
      if (candidate in voterScores) {
        candidateScores[candidate].sum += voterScores[candidate];
        candidateScores[candidate].count++;
      }
    });
  });

  const averages = candidates.map((candidate) => {
    const { sum, count } = candidateScores[candidate];
    return {
      candidate,
      average: count > 0 ? sum / count : 0,
    };
  });

  // Sort by average score (descending)
  averages.sort((a, b) => b.average - a.average);

  const details = averages.reduce(
    (acc, { candidate, average }) => {
      acc[candidate] = average;
      return acc;
    },
    {} as Record<string, number>
  );

  return {
    method: 'Simple Score',
    winner: averages.length > 0 ? averages[0].candidate : undefined,
    details,
  };
}

function calculateSTARVoting(scores: ScoreVote[], candidates: string[]) {
  // First round: calculate average scores
  const candidateScores = candidates.reduce(
    (acc, candidate) => {
      acc[candidate] = { sum: 0, count: 0 };
      return acc;
    },
    {} as Record<string, { sum: number; count: number }>
  );

  scores.forEach(({ scores: voterScores }) => {
    candidates.forEach((candidate) => {
      if (candidate in voterScores) {
        candidateScores[candidate].sum += voterScores[candidate];
        candidateScores[candidate].count++;
      }
    });
  });

  const averages = candidates.map((candidate) => {
    const { sum, count } = candidateScores[candidate];
    return {
      candidate,
      average: count > 0 ? sum / count : 0,
    };
  });

  // Sort by average score (descending)
  averages.sort((a, b) => b.average - a.average);

  const firstRound = averages.reduce(
    (acc, { candidate, average }) => {
      acc[candidate] = average;
      return acc;
    },
    {} as Record<string, number>
  );

  // Take top two candidates for runoff
  let runoffResult = null;
  let winner = averages[0]?.candidate;

  if (averages.length >= 2) {
    const [first, second] = averages;
    let votes1 = 0;
    let votes2 = 0;
    let tied = 0;

    scores.forEach(({ scores: voterScores }) => {
      const score1 = voterScores[first.candidate] || 0;
      const score2 = voterScores[second.candidate] || 0;

      if (score1 > score2) {
        votes1++;
      } else if (score2 > score1) {
        votes2++;
      } else {
        tied++;
      }
    });

    runoffResult = {
      candidate1: first.candidate,
      candidate2: second.candidate,
      votes1,
      votes2,
      tied,
      total_voters: scores.length,
    };

    winner = votes1 > votes2 ? first.candidate : second.candidate;
  }

  return {
    method: 'STAR Voting',
    winner,
    details: {
      first_round: firstRound,
      runoff: runoffResult,
    },
  };
}

function calculateMedianVoting(scores: ScoreVote[], candidates: string[]) {
  const candidateScores = candidates.reduce(
    (acc, candidate) => {
      acc[candidate] = [];
      return acc;
    },
    {} as Record<string, number[]>
  );

  scores.forEach(({ scores: voterScores }) => {
    candidates.forEach((candidate) => {
      if (candidate in voterScores) {
        candidateScores[candidate].push(voterScores[candidate]);
      }
    });
  });

  const medians = candidates.map((candidate) => {
    const scoresList = candidateScores[candidate];
    if (scoresList.length === 0) return { candidate, median: 0 };

    scoresList.sort((a, b) => a - b);
    const mid = Math.floor(scoresList.length / 2);
    const median =
      scoresList.length % 2 !== 0 ? scoresList[mid] : (scoresList[mid - 1] + scoresList[mid]) / 2;

    return { candidate, median };
  });

  // Sort by median score (descending)
  medians.sort((a, b) => b.median - a.median);

  const details = medians.reduce(
    (acc, { candidate, median }) => {
      acc[candidate] = median;
      return acc;
    },
    {} as Record<string, number>
  );

  return {
    method: 'Median Voting',
    winner: medians.length > 0 ? medians[0].candidate : undefined,
    details,
  };
}

function calculateMeanMedianHybrid(scores: ScoreVote[], candidates: string[]) {
  const candidateStats = candidates.reduce(
    (acc, candidate) => {
      acc[candidate] = { sum: 0, count: 0, scores: [] as number[] };
      return acc;
    },
    {} as Record<string, { sum: number; count: number; scores: number[] }>
  );

  scores.forEach(({ scores: voterScores }) => {
    candidates.forEach((candidate) => {
      if (candidate in voterScores) {
        const score = voterScores[candidate];
        candidateStats[candidate].sum += score;
        candidateStats[candidate].count++;
        candidateStats[candidate].scores.push(score);
      }
    });
  });

  const results = candidates.map((candidate) => {
    const { sum, count, scores } = candidateStats[candidate];
    const mean = count > 0 ? sum / count : 0;

    if (scores.length === 0) {
      return { candidate, mean, median: 0, combined: 0 };
    }

    scores.sort((a, b) => a - b);
    const mid = Math.floor(scores.length / 2);
    const median = scores.length % 2 !== 0 ? scores[mid] : (scores[mid - 1] + scores[mid]) / 2;

    // Combined score (50% mean, 50% median)
    const combined = 0.5 * mean + 0.5 * median;

    return { candidate, mean, median, combined };
  });

  // Sort by combined score (descending)
  results.sort((a, b) => b.combined - a.combined);

  return {
    method: 'Mean-Median Hybrid',
    winner: results.length > 0 ? results[0].candidate : undefined,
    details: results,
  };
}

function calculateVarianceBased(scores: ScoreVote[], candidates: string[]) {
  const candidateStats = candidates.reduce(
    (acc, candidate) => {
      acc[candidate] = { sum: 0, sumSq: 0, count: 0 };
      return acc;
    },
    {} as Record<string, { sum: number; sumSq: number; count: number }>
  );

  scores.forEach(({ scores: voterScores }) => {
    candidates.forEach((candidate) => {
      if (candidate in voterScores) {
        const score = voterScores[candidate];
        candidateStats[candidate].sum += score;
        candidateStats[candidate].sumSq += score * score;
        candidateStats[candidate].count++;
      }
    });
  });

  const results = candidates.map((candidate) => {
    const { sum, sumSq, count } = candidateStats[candidate];
    const mean = count > 0 ? sum / count : 0;
    const variance = count > 1 ? sumSq / count - mean * mean : 0;
    const stdDev = Math.sqrt(Math.max(0, variance));

    // Weighted score that balances mean and consistency (lower variance is better)
    const weightedScore = mean - 0.5 * stdDev;

    return {
      candidate,
      mean,
      variance,
      stdDev,
      weighted_score: weightedScore,
    };
  });

  // Sort by weighted score (descending)
  results.sort((a, b) => b.weighted_score - a.weighted_score);

  return {
    method: 'Variance-Based',
    winner: results.length > 0 ? results[0].candidate : undefined,
    details: results,
  };
}

function calculateScoreDistribution(scores: ScoreVote[], candidates: string[]) {
  // Define score bins (0-0.5, 0.5-1, ..., 4.5-5)
  const bins = [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5];
  const candidateDistributions = candidates.reduce(
    (acc, candidate) => {
      acc[candidate] = new Array(bins.length - 1).fill(0);
      return acc;
    },
    {} as Record<string, number[]>
  );

  // Count scores in each bin
  scores.forEach(({ scores: voterScores }) => {
    candidates.forEach((candidate) => {
      if (candidate in voterScores) {
        const score = voterScores[candidate];
        // Find the appropriate bin
        for (let i = 0; i < bins.length - 1; i++) {
          if (score >= bins[i] && score < bins[i + 1]) {
            candidateDistributions[candidate][i]++;
            break;
          }
        }
      }
    });
  });

  const results = candidates.map((candidate) => {
    const distribution = candidateDistributions[candidate];
    const total = distribution.reduce((a, b) => a + b, 0);
    const percentages = distribution.map((count) => (total > 0 ? count / total : 0));

    // Find mode (most common score range)
    let maxIndex = 0;
    let maxValue = 0;
    distribution.forEach((count, index) => {
      if (count > maxValue) {
        maxValue = count;
        maxIndex = index;
      }
    });
    const modeRange = `${bins[maxIndex]}-${bins[maxIndex + 1]}`;

    return {
      candidate,
      distribution,
      percentages,
      total,
      modeRange,
    };
  });

  return {
    method: 'Score Distribution Analysis',
    details: results,
  };
}

function calculateBayesianRegret(scores: ScoreVote[], candidates: string[]) {
  // Calculate utilities (normalized scores)
  const utilities = candidates.reduce(
    (acc, candidate) => {
      acc[candidate] = [];
      return acc;
    },
    {} as Record<string, number[]>
  );

  scores.forEach(({ scores: voterScores }) => {
    candidates.forEach((candidate) => {
      if (candidate in voterScores) {
        // Normalize to 0-1 range
        utilities[candidate].push(voterScores[candidate] / 5);
      }
    });
  });

  // Calculate expected regret for each candidate
  const regrets = candidates.map((candidate) => {
    let totalRegret = 0;

    scores.forEach(({ scores: voterScores }) => {
      // Find the utility of the voter's most preferred candidate
      const bestUtility = Math.max(...Object.values(voterScores)) / 5;
      const currentUtility = (voterScores[candidate] || 0) / 5;

      // Regret is the difference between best possible and current
      totalRegret += bestUtility - currentUtility;
    });

    const avgRegret = totalRegret / scores.length;
    const avgUtility =
      utilities[candidate].reduce((a, b) => a + b, 0) / utilities[candidate].length;

    return {
      candidate,
      avgUtility,
      avgRegret,
    };
  });

  // Sort by average regret (ascending - lower regret is better)
  regrets.sort((a, b) => a.avgRegret - b.avgRegret);

  return {
    method: 'Bayesian Regret',
    winner: regrets.length > 0 ? regrets[0].candidate : undefined,
    details: regrets,
  };
}
