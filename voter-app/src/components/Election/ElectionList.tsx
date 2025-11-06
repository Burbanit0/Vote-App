// src/components/ElectionsList.tsx
import React, { useEffect, useState, useCallback } from 'react';
import { Container, Row, Col, Form, Pagination, InputGroup, ButtonGroup, Button, Spinner, Alert, Card, DropdownButton, Dropdown } from 'react-bootstrap';
import { fetchAllElections } from '../../services/';
import { Election } from '../../types';
import { debounce } from 'lodash';
import ElectionCard from './ElectionCard';
import CreateElectionModal from './CreateElectionModal';
import useUserPermissions from '../../hooks/useUserPermisions';


const ElectionList: React.FC = () => {
  const [elections, setElections] = useState<Election[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [showCreateModal, setShowCreateModal] = useState(false);
  const { canCreateElections } = useUserPermissions();

  const [sortBy, setSortBy] = useState<'name' | 'date' | 'status'>('name');
  const [filter, setFilter] = useState<'all' | 'active' | 'completed' | 'upcoming'>('all');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  const debouncedSearch = useCallback(
    debounce((term: string) => {
      setSearchTerm(term)
      setCurrentPage(1);
    }, 300),
    []
  );

  const fetchElections = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchAllElections(currentPage, searchTerm, sortBy, sortDirection, filter); // Adjust the URL as needed
      setElections(response.elections);
      setTotalPages(response.pages);
    } catch (err) {
      setError('Failed to fetch elections.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchElections();
  }, [currentPage, searchTerm, filter, sortBy]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
    fetchElections();
  }

  const toggleSortDirection = () => {
    setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
  };

  // Generate pagination items
  const renderPaginationItems = () => {
    const items = [];
    const maxVisiblePages = 5; // Maximum number of page buttons to show
    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);

    if (endPage - startPage + 1 < maxVisiblePages) {
      startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }

    for (let page = startPage; page <= endPage; page++) {
      items.push(
        <Pagination.Item
          key={page}
          active={page === currentPage}
          onClick={() => setCurrentPage(page)}
        >
          {page}
        </Pagination.Item>
      );
    }

    return items;
  };

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'active':
        return 'success';
      case 'completed':
        return 'secondary';
      case 'upcoming':
        return 'warning';
      default:
        return 'primary';
    }
  };

  return (
      <Container className="mt-4">
      <Row className="mb-3">
        <Col>
          <div className="d-flex justify-content-between align-items-center">
            <h2>Elections</h2>
            {canCreateElections && (
              <Button
                variant="primary"
                onClick={() => setShowCreateModal(true)}
              >
                Create New Election
              </Button>
            )}
          </div>
        </Col>
      </Row>
      {/* Search Form */}
      <Row className="mb-4">
        <Col md={5}>
          <Form onSubmit={handleSearch}>
            <InputGroup>
              <Form.Control
                type="text"
                placeholder="Search elections..."
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value);
                  debouncedSearch(e.target.value);
                }}
              />
              <Button variant="primary" type="submit">
                Search
              </Button>
            </InputGroup>
          </Form>
        </Col>
        <Col md={3}>
          <DropdownButton
            id="sort-dropdown"
            title={`Sort by: ${sortBy} (${sortDirection})`}
            variant="outline-secondary"
          >
            <Dropdown.Item onClick={() => { setSortBy('name'); setSortDirection('asc');  }}>Name (A-Z)</Dropdown.Item>
            <Dropdown.Item onClick={() => { setSortBy('name'); setSortDirection('desc'); }}>Name (Z-A)</Dropdown.Item>
            <Dropdown.Item onClick={() => { setSortBy('date'); setSortDirection('asc'); }}>Date (Oldest)</Dropdown.Item>
            <Dropdown.Item onClick={() => { setSortBy('date'); setSortDirection('desc'); }}>Date (Newest)</Dropdown.Item>
            <Dropdown.Item onClick={() => { setSortBy('status'); setSortDirection('asc'); }}>Status (A-Z)</Dropdown.Item>
          </DropdownButton>
        </Col>
        <Col md={3}>
          <ButtonGroup className="w-100">
            <Button
              variant={filter === 'all' ? 'primary' : 'outline-primary'}
              onClick={() => setFilter('all')}
            >
              All
            </Button>
            <Button
              variant={filter === 'active' ? 'primary' : 'outline-primary'}
              onClick={() => setFilter('active')}
            >
              Active
            </Button>
            <Button
              variant={filter === 'completed' ? 'primary' : 'outline-primary'}
              onClick={() => setFilter('completed')}
            >
              Completed
            </Button>
            <Button
              variant={filter === 'upcoming' ? 'primary' : 'outline-primary'}
              onClick={() => setFilter('upcoming')}
            >
              Upcoming
            </Button>
          </ButtonGroup>
        </Col>
      </Row>
      
      {/* Loading and Error States */}
      {loading && (
        <Row className="justify-content-center">
          <Spinner animation="border" role="status">
            <span className="visually-hidden">Loading...</span>
          </Spinner>
        </Row>
      )}

      {error && (
        <Row>
          <Col>
            <Alert variant="danger">{error}</Alert>
          </Col>
        </Row>
      )}

      {/* Elections List */}
      {elections.length > 0 ? (
        <Row className="mt-4">
          {elections.map((election) => (
            <Col key={election.id} md={4}>
              <ElectionCard election={election}/>
            </Col>
          ))}
        </Row>
      ) : (
        !loading && (
          <Row>
            <Col>
              <Alert variant="info">No elections found</Alert>
            </Col>
          </Row>
        )
      )}

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <Row className="mt-4">
          <Col>
            <Pagination className="justify-content-center">
              <Pagination.First
                disabled={currentPage === 1}
                onClick={() => setCurrentPage(1)}
              />
              <Pagination.Prev
                disabled={currentPage === 1}
                onClick={() => setCurrentPage(currentPage - 1)}
              />

              {renderPaginationItems()}

              <Pagination.Next
                disabled={currentPage === totalPages}
                onClick={() => setCurrentPage(currentPage + 1)}
              />
              <Pagination.Last
                disabled={currentPage === totalPages}
                onClick={() => setCurrentPage(totalPages)}
              />
            </Pagination>
          </Col>
        </Row>
      )}
      <CreateElectionModal
        show={showCreateModal}
        onHide={() => setShowCreateModal(false)}
        onElectionCreated={() => {
          // Refresh the election list
          fetchElections();
        }}
      />
    </Container>
      
  );
};

export default ElectionList;