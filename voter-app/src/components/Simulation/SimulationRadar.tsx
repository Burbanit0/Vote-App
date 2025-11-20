interface RankingResult {
  voter_id: number;
  ranking: string[];
}

const preprocessRankingsForRadar = (rankings: RankingResult[]) => {
  // Get all unique candidates
  const candidates = [...new Set(rankings.flatMap((r) => r.ranking))];

  // Find the maximum ranking length (number of ranks)
  const maxRank = Math.max(...rankings.map((r) => r.ranking.length));

  // Initialize data structure to count votes per candidate and rank
  const candidateRankData: Record<string, Record<number, number>> = {};

  // Initialize the structure for each candidate
  candidates.forEach((candidate) => {
    candidateRankData[candidate] = {};
    for (let rank = 1; rank <= maxRank; rank++) {
      candidateRankData[candidate][rank] = 0;
    }
  });

  // Count how many times each candidate appears at each rank
  rankings.forEach(({ ranking }) => {
    ranking.forEach((candidate, index) => {
      const rank = index + 1; // Ranks start at 1
      candidateRankData[candidate][rank] = (candidateRankData[candidate][rank] || 0) + 1;
    });
  });

  // Normalize by total votes per candidate (to compare proportions)
  const normalizedData: Record<string, number[]> = {};

  candidates.forEach((candidate) => {
    const totalVotes = Object.values(candidateRankData[candidate]).reduce((a, b) => a + b, 0);
    normalizedData[candidate] = [];

    // For each rank, calculate the proportion of votes
    for (let rank = 1; rank <= maxRank; rank++) {
      const count = candidateRankData[candidate][rank] || 0;
      normalizedData[candidate].push(totalVotes > 0 ? count / totalVotes : 0);
    }
  });

  // Generate colors for each candidate
  const generateColor = (index: number) => {
    const hue = (index * 120) % 360; // Spread colors evenly
    return {
      borderColor: `hsl(${hue}, 70%, 50%)`,
      backgroundColor: `hsla(${hue}, 70%, 50%, 0.2)`,
    };
  };

  return {
    labels: Array.from({ length: maxRank }, (_, i) => `Rank ${i + 1}`),
    datasets: candidates.map((candidate, index) => ({
      label: candidate,
      data: normalizedData[candidate],
      ...generateColor(index),
      pointBackgroundColor: `hsl(${(index * 120) % 360}, 70%, 50%)`,
      pointBorderColor: '#fff',
      pointHoverBackgroundColor: '#fff',
      pointHoverBorderColor: `hsl(${(index * 120) % 360}, 70%, 50%)`,
    })),
  };
};

export default preprocessRankingsForRadar;
