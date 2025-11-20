// ParticipationPoints.tsx
import React, { useState, useEffect } from 'react';
import { Card, ProgressBar, Alert } from 'react-bootstrap';
import { ParticipationData } from '../../types';
import { getParticipation } from '../../services';

const ParticipationPoints: React.FC = () => {
  const [data, setData] = useState<ParticipationData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await getParticipation();
        setData(response);
      } catch (err) {
        setError('Failed to fetch participation data');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  const getLevelColor = (level: string) => {
    switch (level.toLowerCase()) {
      case 'beginner':
        return 'info';
      case 'active':
        return 'primary';
      case 'expert':
        return 'success';
      case 'master':
        return 'warning';
      case 'legend':
        return 'danger';
      default:
        return 'secondary';
    }
  };

  if (isLoading) {
    return <div>Loading participation data...</div>;
  }

  if (error) {
    return <Alert variant="danger">{error}</Alert>;
  }

  if (!data) {
    return <div>No participation data available</div>;
  }

  const progress = Math.min(100, (data.points / data.nextLevel) * 100);

  return (
    <Card>
      <Card.Body>
        <Card.Title>Your Participation</Card.Title>
        <Card.Text>
          You have <strong>{data.points}</strong> participation points.
        </Card.Text>
        <Card.Text>
          Level: <strong className={`text-${getLevelColor(data.level)}`}>{data.level}</strong>
        </Card.Text>
        <ProgressBar
          now={progress}
          label={`${data.points}/${data.nextLevel}`}
          variant={getLevelColor(data.level)}
        />
        <Card.Text className="mt-2">
          {progress >= 100
            ? 'You reached this level!'
            : `You need ${data.nextLevel - data.points} more points to reach the next level.`}
        </Card.Text>
      </Card.Body>
    </Card>
  );
};

export default ParticipationPoints;
