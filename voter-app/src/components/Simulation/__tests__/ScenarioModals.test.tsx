import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ScenarioModals from '../ScenarioModals';
import { getScenario } from '../../../services/scenariosApi';

vi.mock('../../../services/scenariosApi', () => ({
  getScenario: vi.fn(),
}));

const mockScenarios = [
  { id: 1, name: 'Test Scenario', created_at: '2024-01-15T10:00:00Z', config: {} },
  { id: 2, name: 'Another Scenario', created_at: '2024-02-20T14:30:00Z', config: {} },
];

const defaultProps = {
  showSaveModal: false,
  setShowSaveModal: vi.fn(),
  saveName: '',
  setSaveName: vi.fn(),
  saving: false,
  handleSave: vi.fn(),
  showLoadModal: false,
  setShowLoadModal: vi.fn(),
  scenarioList: [],
  loadingList: false,
  handleLoad: vi.fn(),
  handleDelete: vi.fn(),
};

describe('ScenarioModals', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Save Modal', () => {
    it('renders save modal when showSaveModal is true', () => {
      render(<ScenarioModals {...defaultProps} showSaveModal={true} />);
      expect(screen.getByText('Save scenario')).toBeInTheDocument();
    });

    it('does not render save modal when showSaveModal is false', () => {
      render(<ScenarioModals {...defaultProps} showSaveModal={false} />);
      expect(screen.queryByText('Save scenario')).not.toBeInTheDocument();
    });

    it('disables save button when name is empty', () => {
      render(<ScenarioModals {...defaultProps} showSaveModal={true} saveName="" />);
      const saveBtn = screen.getByText('Save').closest('button');
      expect(saveBtn).toBeDisabled();
    });

    it('enables save button when name is not empty', () => {
      render(<ScenarioModals {...defaultProps} showSaveModal={true} saveName="My Scenario" />);
      const saveBtn = screen.getByText('Save').closest('button');
      expect(saveBtn).not.toBeDisabled();
    });

    it('shows spinner when saving', () => {
      render(
        <ScenarioModals {...defaultProps} showSaveModal={true} saveName="Test" saving={true} />
      );
      expect(screen.getByText('Saving…')).toBeInTheDocument();
    });
  });

  describe('Load Modal', () => {
    it('renders load modal when showLoadModal is true', () => {
      render(<ScenarioModals {...defaultProps} showLoadModal={true} />);
      expect(screen.getByText('Load scenario')).toBeInTheDocument();
    });

    it('shows spinner when loading list', () => {
      render(<ScenarioModals {...defaultProps} showLoadModal={true} loadingList={true} />);
      expect(document.querySelector('.animate-spin')).toBeInTheDocument();
    });

    it('shows empty message when no scenarios', () => {
      render(<ScenarioModals {...defaultProps} showLoadModal={true} scenarioList={[]} />);
      expect(screen.getByText(/No saved scenarios yet/)).toBeInTheDocument();
    });

    it('renders scenario list', () => {
      render(
        <ScenarioModals {...defaultProps} showLoadModal={true} scenarioList={mockScenarios} />
      );
      expect(screen.getByText('Test Scenario')).toBeInTheDocument();
      expect(screen.getByText('Another Scenario')).toBeInTheDocument();
    });

    it('calls getScenario and handleLoad on Load click', async () => {
      const detail = { id: 1, name: 'Test', created_at: '', config: {}, results: null };
      (getScenario as jest.Mock).mockResolvedValue(detail);
      const handleLoad = vi.fn();

      render(
        <ScenarioModals
          {...defaultProps}
          showLoadModal={true}
          scenarioList={mockScenarios}
          handleLoad={handleLoad}
        />
      );

      const loadButtons = screen.getAllByText('Load');
      fireEvent.click(loadButtons[0]);

      await waitFor(() => {
        expect(getScenario).toHaveBeenCalledWith(1);
      });
      await waitFor(() => {
        expect(handleLoad).toHaveBeenCalledWith(detail);
      });
    });

    it('calls handleDelete on Delete click', () => {
      const handleDelete = vi.fn();
      render(
        <ScenarioModals
          {...defaultProps}
          showLoadModal={true}
          scenarioList={mockScenarios}
          handleDelete={handleDelete}
        />
      );

      const deleteButtons = screen.getAllByText('✕');
      fireEvent.click(deleteButtons[0]);
      expect(handleDelete).toHaveBeenCalledWith(1);
    });
  });
});
