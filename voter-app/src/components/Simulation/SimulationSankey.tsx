interface RankingResult {
  voter_id: number;
  ranking: string[];
}

const preprocessRankingsForSankey = (rankings: RankingResult[]) => {
  // Count first choices
  const firstChoices: Record<string, number> = {};
  rankings.forEach(({ ranking }) => {
    const firstChoice = ranking[0];
    firstChoices[firstChoice] = (firstChoices[firstChoice] || 0) + 1;
  });

  // Simulate instant-runoff rounds
  const candidates = [...new Set(rankings.flatMap((r) => r.ranking))];
  let remainingCandidates = [...candidates];
  let currentRoundVotes: Record<string, number> = { ...firstChoices };
  const transitions: [string, string, number][] = [];

  // Initial "Start" node connections
  Object.entries(currentRoundVotes).forEach(([candidate, count]) => {
    transitions.push([`Start`, `R:1-${candidate}`, count]);
  });

  let round = 1;

  // Simulate elimination rounds
  while (remainingCandidates.length > 1) {
    round++;

    // Find candidate with fewest votes to eliminate
    const votesThisRound = { ...currentRoundVotes };
    const minVotes = Math.min(...Object.values(votesThisRound));
    const eliminated = Object.entries(votesThisRound)
      .filter(([candidate]) => remainingCandidates.includes(candidate))
      .find(([_, votes]) => votes === minVotes)?.[0];

    if (!eliminated) break;

    // Remove eliminated candidate
    remainingCandidates = remainingCandidates.filter((c) => c !== eliminated);

    // Calculate vote redistribution
    const nextRoundVotes: Record<string, number> = {};

    rankings.forEach(({ ranking }) => {
      // Find the highest-ranked remaining candidate for this voter
      const nextChoice = ranking.find((c) => remainingCandidates.includes(c));

      if (nextChoice) {
        const currentChoice =
          ranking.find((c) => c === eliminated) || ranking.find((c) => currentRoundVotes[c]);

        if (currentChoice) {
          const key = `R:${round - 1}-${currentChoice}->R:${round}-${nextChoice}`;
          const existing = transitions.find(
            (t) => t[0] === `R:${round - 1}-${currentChoice}` && t[1] === `R:${round}-${nextChoice}`
          );
          if (existing) {
            existing[2] += 1;
          } else {
            transitions.push([`R:${round - 1}-${currentChoice}`, `R:${round}-${nextChoice}`, 1]);
          }
        }
      }
    });

    // Update votes for next round
    currentRoundVotes = {};
    rankings.forEach(({ ranking }) => {
      const nextChoice = ranking.find((c) => remainingCandidates.includes(c));
      if (nextChoice) {
        currentRoundVotes[nextChoice] = (currentRoundVotes[nextChoice] || 0) + 1;
      }
    });
  }

  // Add final round connections to "Winner" node
  if (remainingCandidates.length === 1) {
    const winner = remainingCandidates[0];
    Object.entries(currentRoundVotes).forEach(([candidate, count]) => {
      if (candidate === winner) {
        transitions.push([`R:${round}-${candidate}`, `Winner: ${winner}`, count]);
      }
    });
  }

  // Format data for Google Sankey
  const data = [['From', 'To', 'Weight'], ...transitions];

  return data;
};

export default preprocessRankingsForSankey;
