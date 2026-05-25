import React, { useCallback, useMemo, useState } from 'react';
import {
  Alert, Badge, Button, Col, Form, Modal, Row, Spinner, Table,
} from 'react-bootstrap';
import { useTranslation } from 'react-i18next';

const API_BASE = process.env.VITE_API_URL || 'http://localhost:4433';

// ── Column groups ─────────────────────────────────────────────────────────────

interface ColGroup {
  key: string;
  labelKey: string;
  cols: string[];
  always?: boolean;
}

const COLUMN_GROUPS: ColGroup[] = [
  {
    key: 'identification',
    labelKey: 'export.colGroupId',
    cols: ['scenario_id', 'num_candidates', 'num_voters', 'method'],
    always: true,
  },
  {
    key: 'winners',
    labelKey: 'export.colGroupWinners',
    cols: ['winner', 'plurality_winner', 'borda_winner', 'irv_winner', 'schulze_winner', 'approval_winner', 'methods_agree'],
  },
  {
    key: 'quality',
    labelKey: 'export.colGroupQuality',
    cols: ['winner_score', 'bayesian_regret', 'condorcet_exists', 'condorcet_winner'],
  },
  {
    key: 'blank',
    labelKey: 'export.colGroupBlank',
    cols: ['blank_rate', 'blank_rule'],
  },
];

const ALL_COLS = COLUMN_GROUPS.flatMap((g) => g.cols);

// ── Types ─────────────────────────────────────────────────────────────────────

interface Props {
  show: boolean;
  onHide: () => void;
  defaultCandidates?: string[];
}

type Format = 'csv' | 'json';

interface PreviewRow {
  [col: string]: string | number;
}

// ── Simple CSV parser for preview (no quoted-field support needed) ─────────────

function parseCSVPreview(csv: string, maxRows = 5): PreviewRow[] {
  const lines = csv.split('\n').filter(Boolean);
  if (lines.length < 2) return [];
  const headers = lines[0].split(',');
  return lines.slice(1, maxRows + 1).map((line) => {
    const vals = line.split(',');
    return headers.reduce<PreviewRow>((obj, h, i) => {
      obj[h] = vals[i] ?? '';
      return obj;
    }, {});
  });
}

// ── Component ─────────────────────────────────────────────────────────────────

const DatasetExportModal: React.FC<Props> = ({ show, onHide, defaultCandidates }) => {
  const { t } = useTranslation();

  const [numScenarios,    setNumScenarios]    = useState(100);
  const [numCandidates,   setNumCandidates]   = useState(
    Math.min(8, Math.max(2, defaultCandidates?.length ?? 4))
  );
  const [numVoters,       setNumVoters]       = useState(200);
  const [seed,            setSeed]            = useState(42);
  const [ideology,        setIdeology]        = useState('random');
  const [format,          setFormat]          = useState<Format>('csv');
  const [enabledGroups,   setEnabledGroups]   = useState<Record<string, boolean>>({
    identification: true,
    winners:        true,
    quality:        true,
    blank:          false,
  });

  const [loading,         setLoading]         = useState(false);
  const [error,           setError]           = useState<string | null>(null);
  const [downloadBlob,    setDownloadBlob]    = useState<Blob | null>(null);
  const [downloadName,    setDownloadName]    = useState('');
  const [previewRows,     setPreviewRows]     = useState<PreviewRow[]>([]);
  const [previewCols,     setPreviewCols]     = useState<string[]>([]);

  const selectedCols = useMemo(
    () => ALL_COLS.filter((col) => {
      const group = COLUMN_GROUPS.find((g) => g.cols.includes(col));
      return group?.always || enabledGroups[group?.key ?? ''];
    }),
    [enabledGroups]
  );

  const toggleGroup = (key: string) =>
    setEnabledGroups((prev) => ({ ...prev, [key]: !prev[key] }));

  const filterRowCols = useCallback(
    (row: PreviewRow) =>
      Object.fromEntries(
        Object.entries(row).filter(([k]) => selectedCols.includes(k))
      ),
    [selectedCols]
  );

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    setDownloadBlob(null);
    setPreviewRows([]);

    const payload = { num_scenarios: numScenarios, num_candidates: numCandidates, num_voters: numVoters, seed, ideology };
    const endpoint = format === 'csv' ? 'simulation-dataset' : 'simulation-dataset-json';

    try {
      // Phase 4.5.a.2: export endpoints moved to FastAPI.
      const res = await fetch(`${API_BASE}/api/v2/export/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: res.statusText }));
        throw new Error(err.error ?? res.statusText);
      }

      if (format === 'csv') {
        const text = await res.text();
        const blob = new Blob(
          [text.split('\n').map((line) => {
            if (!line) return '';
            const vals = line.split(',');
            const hdrs = text.split('\n')[0].split(',');
            // Keep only selected columns
            return hdrs
              .map((h, i) => (selectedCols.includes(h) ? vals[i] : null))
              .filter((v) => v !== null)
              .join(',');
          }).join('\n')],
          { type: 'text/csv' }
        );
        setDownloadBlob(blob);
        setDownloadName(`votelab_dataset_${seed}.csv`);
        const preview = parseCSVPreview(text).map(filterRowCols);
        setPreviewRows(preview);
        setPreviewCols(selectedCols.filter((c) => text.split('\n')[0].split(',').includes(c)));
      } else {
        const json = await res.json();
        const filteredRows = (json.rows as PreviewRow[]).map((row) =>
          Object.fromEntries(Object.entries(row).filter(([k]) => selectedCols.includes(k)))
        );
        const blob = new Blob([JSON.stringify({ ...json, rows: filteredRows }, null, 2)], {
          type: 'application/json',
        });
        setDownloadBlob(blob);
        setDownloadName(`votelab_dataset_${seed}.json`);
        setPreviewRows(filteredRows.slice(0, 5));
        setPreviewCols(selectedCols.filter((c) => Object.keys(filteredRows[0] ?? {}).includes(c)));
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (!downloadBlob) return;
    const url = URL.createObjectURL(downloadBlob);
    const a = document.createElement('a');
    a.href = url;
    a.download = downloadName;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleClose = () => {
    setDownloadBlob(null);
    setPreviewRows([]);
    setError(null);
    onHide();
  };

  const estimatedSec = Math.round(numScenarios * numVoters / 50_000) + 1;

  return (
    <Modal show={show} onHide={handleClose} size="lg" centered>
      <Modal.Header closeButton>
        <Modal.Title style={{ fontSize: '1rem' }}>
          📊 {t('export.modalTitle')}
        </Modal.Title>
      </Modal.Header>

      <Modal.Body>
        {/* ── Parameters ── */}
        <Row className="g-3 mb-3">
          <Col md={6}>
            <Form.Label className="small mb-1">
              {t('export.numScenarios')} : <strong>{numScenarios}</strong>
            </Form.Label>
            <Form.Range
              min={10} max={1000} step={10} value={numScenarios}
              onChange={(e) => { setNumScenarios(Number(e.target.value)); setDownloadBlob(null); }}
            />
            <div className="d-flex justify-content-between" style={{ fontSize: '0.72rem', color: '#888' }}>
              <span>10</span><span>1 000</span>
            </div>
          </Col>

          <Col md={3}>
            <Form.Label className="small mb-1">{t('export.numCandidates')}</Form.Label>
            <Form.Control
              size="sm" type="number" min={2} max={8} value={numCandidates}
              onChange={(e) => { setNumCandidates(Number(e.target.value)); setDownloadBlob(null); }}
            />
          </Col>

          <Col md={3}>
            <Form.Label className="small mb-1">{t('export.numVoters')}</Form.Label>
            <Form.Control
              size="sm" type="number" min={10} max={2000} value={numVoters}
              onChange={(e) => { setNumVoters(Number(e.target.value)); setDownloadBlob(null); }}
            />
          </Col>

          <Col md={3}>
            <Form.Label className="small mb-1">{t('export.seed')}</Form.Label>
            <Form.Control
              size="sm" type="number" value={seed}
              onChange={(e) => { setSeed(Number(e.target.value)); setDownloadBlob(null); }}
            />
          </Col>

          <Col md={3}>
            <Form.Label className="small mb-1">{t('export.ideology')}</Form.Label>
            <Form.Select
              size="sm" value={ideology}
              onChange={(e) => { setIdeology(e.target.value); setDownloadBlob(null); }}
            >
              {['random', 'centrist', 'polarized', 'left_skewed', 'right_skewed'].map((v) => (
                <option key={v} value={v}>{t(`ideology.${v}`)}</option>
              ))}
            </Form.Select>
          </Col>

          <Col md={3}>
            <Form.Label className="small mb-1">{t('export.format')}</Form.Label>
            <div className="d-flex gap-2">
              {(['csv', 'json'] as Format[]).map((f) => (
                <Button
                  key={f}
                  size="sm"
                  variant={format === f ? 'primary' : 'outline-secondary'}
                  onClick={() => { setFormat(f); setDownloadBlob(null); }}
                  style={{ textTransform: 'uppercase', fontSize: '0.75rem', minWidth: 56 }}
                >
                  {f}
                </Button>
              ))}
            </div>
          </Col>
        </Row>

        {/* ── Column selection ── */}
        <div className="mb-3">
          <div className="small fw-semibold mb-2">{t('export.columns')}</div>
          <div className="d-flex flex-wrap gap-3">
            {COLUMN_GROUPS.map((group) => (
              <Form.Check
                key={group.key}
                type="checkbox"
                id={`col-group-${group.key}`}
                label={
                  <span className="small">
                    {t(group.labelKey)}
                    {group.always && <Badge bg="secondary" className="ms-1" style={{ fontSize: '0.6rem' }}>{t('export.required')}</Badge>}
                    <span className="text-muted ms-1" style={{ fontSize: '0.7rem' }}>
                      ({group.cols.length})
                    </span>
                  </span>
                }
                checked={group.always || enabledGroups[group.key]}
                disabled={group.always}
                onChange={() => { if (!group.always) { toggleGroup(group.key); setDownloadBlob(null); } }}
              />
            ))}
          </div>
          <div className="text-muted mt-1" style={{ fontSize: '0.75rem' }}>
            {selectedCols.length} {t('export.columnsSelected')}
          </div>
        </div>

        {/* ── Estimate + generate ── */}
        <div className="d-flex align-items-center gap-3 mb-3 flex-wrap">
          <Button
            variant="primary"
            onClick={handleGenerate}
            disabled={loading}
          >
            {loading
              ? <><Spinner size="sm" className="me-2" />{t('export.generating')}</>
              : format === 'csv' ? t('export.generateCSV') : t('export.generateJSON')}
          </Button>
          {!loading && !downloadBlob && (
            <span className="text-muted small">
              ~{estimatedSec}s {t('export.estimatedTime')}
            </span>
          )}
          {downloadBlob && (
            <Button variant="success" onClick={handleDownload}>
              ⬇ {t('export.download')} ({downloadName})
            </Button>
          )}
        </div>

        {error && <Alert variant="danger" className="py-2">{error}</Alert>}

        {/* ── Preview ── */}
        {previewRows.length > 0 && (
          <div>
            <div className="small fw-semibold mb-2">
              {t('export.preview')} <span className="text-muted fw-normal">(5 {t('export.firstRows')})</span>
            </div>
            <div style={{ overflowX: 'auto', fontSize: '0.72rem' }}>
              <Table bordered size="sm" className="mb-0" style={{ minWidth: 500 }}>
                <thead className="table-light">
                  <tr>
                    {previewCols.map((c) => <th key={c}>{c}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {previewRows.map((row, i) => (
                    <tr key={i}>
                      {previewCols.map((c) => (
                        <td key={c} style={{ whiteSpace: 'nowrap' }}>
                          {String(row[c] ?? '')}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </Table>
            </div>
            <p className="text-muted mt-1 mb-0" style={{ fontSize: '0.72rem' }}>
              {t('export.seedNote', { seed })}
            </p>
          </div>
        )}
      </Modal.Body>

      <Modal.Footer>
        <Button variant="outline-secondary" size="sm" onClick={handleClose}>
          {t('common.close')}
        </Button>
      </Modal.Footer>
    </Modal>
  );
};

export default DatasetExportModal;
