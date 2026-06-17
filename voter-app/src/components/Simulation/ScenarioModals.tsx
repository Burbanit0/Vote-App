import React from 'react';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Modal } from '@/components/ui/modal';
import { Spinner } from '@/components/ui/spinner';
import { Table } from '@/components/ui/table';
import { Control } from '@/components/ui/form-controls';
import { ScenarioDetail, ScenarioSummary } from '../../types';
import { getScenario } from '../../services/scenariosApi';

interface Props {
  showSaveModal: boolean;
  setShowSaveModal: (v: boolean) => void;
  saveName: string;
  setSaveName: (v: string) => void;
  saving: boolean;
  handleSave: () => void;

  showLoadModal: boolean;
  setShowLoadModal: (v: boolean) => void;
  scenarioList: ScenarioSummary[];
  loadingList: boolean;
  handleLoad: (scenario: ScenarioDetail) => void;
  handleDelete: (id: number) => void;
}

const ScenarioModals: React.FC<Props> = ({
  showSaveModal,
  setShowSaveModal,
  saveName,
  setSaveName,
  saving,
  handleSave,
  showLoadModal,
  setShowLoadModal,
  scenarioList,
  loadingList,
  handleLoad,
  handleDelete,
}) => (
  <>
    <Modal show={showSaveModal} onHide={() => setShowSaveModal(false)} centered>
      <Modal.Header closeButton>
        <Modal.Title>Save scenario</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <label className="mb-1 inline-block" htmlFor="scenario-name">
          Scenario name
        </label>
        <Control
          id="scenario-name"
          type="text"
          value={saveName}
          onChange={(e) => setSaveName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleSave();
          }}
          placeholder="My scenario"
          autoFocus
        />
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={() => setShowSaveModal(false)}>
          Cancel
        </Button>
        <Button variant="success" onClick={handleSave} disabled={saving || !saveName.trim()}>
          {saving ? (
            <>
              <Spinner size="sm" className="me-2" />
              Saving…
            </>
          ) : (
            'Save'
          )}
        </Button>
      </Modal.Footer>
    </Modal>

    <Modal show={showLoadModal} onHide={() => setShowLoadModal(false)} size="lg" centered>
      <Modal.Header closeButton>
        <Modal.Title>Load scenario</Modal.Title>
      </Modal.Header>
      <Modal.Body style={{ maxHeight: '60vh', overflowY: 'auto' }}>
        {loadingList ? (
          <div className="text-center py-3">
            <Spinner />
          </div>
        ) : scenarioList.length === 0 ? (
          <Alert variant="info" className="mb-0">
            No saved scenarios yet. Run an analysis and click <strong>Save scenario</strong> to save
            one.
          </Alert>
        ) : (
          <Table className="[&_th]:p-1 [&_td]:p-1 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_th]:border [&_td]:border [&_tbody_tr:hover]:bg-muted/50">
            <thead className="table-light">
              <tr>
                <th>Name</th>
                <th>Saved</th>
                <th style={{ width: 160 }}></th>
              </tr>
            </thead>
            <tbody>
              {scenarioList.map((s) => (
                <tr key={s.id}>
                  <td className="align-middle">{s.name}</td>
                  <td className="align-middle text-muted-foreground text-sm">
                    {new Date(s.created_at).toLocaleString()}
                  </td>
                  <td className="text-center">
                    <Button
                      size="sm"
                      variant="outline-primary"
                      className="me-2"
                      onClick={() => getScenario(s.id).then((detail) => handleLoad(detail))}
                    >
                      Load
                    </Button>
                    <Button size="sm" variant="outline-danger" onClick={() => handleDelete(s.id)}>
                      ✕
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={() => setShowLoadModal(false)}>
          Close
        </Button>
      </Modal.Footer>
    </Modal>
  </>
);

export default ScenarioModals;
