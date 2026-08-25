import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Card, CardBody, CardHeader } from '@/components/ui/card';

interface EliminatedCandidatesCardProps {
  candidates: string[];
}

/** The badge row showing who's been knocked out so far — shared by every
 * elimination-round method (IRV, Coombs, …). Renders nothing when empty; the
 * caller is still expected to guard on `candidates.length > 0` itself, since
 * some callers only want the card mounted once there's something to show. */
const EliminatedCandidatesCard: React.FC<EliminatedCandidatesCardProps> = ({ candidates }) => (
  <Card className="mt-3">
    <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
      Eliminated Candidates
    </CardHeader>
    <CardBody>
      <div className="flex flex-wrap gap-2">
        {candidates.map((candidate) => (
          <Badge key={candidate} variant="secondary" className="p-2">
            {candidate}
          </Badge>
        ))}
      </div>
    </CardBody>
  </Card>
);

export default EliminatedCandidatesCard;
