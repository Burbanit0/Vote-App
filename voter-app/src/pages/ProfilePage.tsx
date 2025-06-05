import React from 'react';
import { Col, Container, Row } from 'react-bootstrap';
import Profile from '../components/User/Profile';
import UserElectionList from '../components/User/UserElectionList';

const ProfilePage: React.FC = () => {

    return (
        <Container>
            <Row>
                <Profile/>
            </Row>
            <Row>
                <Col>
                    <UserElectionList/>
                </Col>
            </Row>
        </Container>
    )
}

export default ProfilePage;