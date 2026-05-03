import React from 'react';
import { Container } from 'react-bootstrap';
import PartyList from '../components/Party/PartyList';

const PartyPage: React.FC = () => {
  return (
    <Container>
      <PartyList />
    </Container>
  );
};

export default PartyPage;
