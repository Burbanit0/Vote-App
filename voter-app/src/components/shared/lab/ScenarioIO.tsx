/**
 * ScenarioIO — Export / Import the current Lab scenario.
 *
 * Bundles the ElectionContext config + the pinned perturbations into a
 * single JSON payload so the user can save an experiment ("France 2002
 * with abstention 30 % and 50 % bias pinned") and reload it later — or
 * share it with someone else.
 *
 * Pinned perturbations are presentational summaries; importing them
 * restores the cards but does NOT re-run the underlying perturber tabs
 * (the user can repin from the relevant tab if they want fresh data).
 */
import React, { useCallback, useRef, useState } from 'react';
import { Button, Toast, ToastContainer } from 'react-bootstrap';
import { useTranslation } from 'react-i18next';
import { useElection, ElectionConfig } from '../../../context/ElectionContext';
import { usePerturbations, PinnedPerturbation } from '../../../context/PerturbationsContext';

export const SCENARIO_FORMAT_VERSION = 1;

export interface ScenarioBundle {
  version:     number;
  exportedAt:  string;
  config:      ElectionConfig;
  pinned:      PinnedPerturbation[];
}

/** Build the export payload from current context state. */
export function buildScenarioBundle(
  config: ElectionConfig,
  pinned: PinnedPerturbation[],
): ScenarioBundle {
  return {
    version:    SCENARIO_FORMAT_VERSION,
    exportedAt: new Date().toISOString(),
    config,
    pinned,
  };
}

/** Validate a parsed bundle. Returns null if invalid. */
export function validateScenarioBundle(raw: unknown): ScenarioBundle | null {
  if (typeof raw !== 'object' || raw === null) return null;
  const obj = raw as Partial<ScenarioBundle>;
  if (typeof obj.version !== 'number') return null;
  if (typeof obj.config !== 'object' || obj.config === null) return null;
  const cfg = obj.config as Partial<ElectionConfig>;
  // Minimum sanity: an array of candidates with x/y/name
  if (!Array.isArray(cfg.candidates)) return null;
  for (const c of cfg.candidates) {
    if (typeof c !== 'object' || c === null) return null;
    if (typeof (c as { name?: unknown }).name !== 'string') return null;
    if (typeof (c as { x?: unknown }).x !== 'number') return null;
    if (typeof (c as { y?: unknown }).y !== 'number') return null;
  }
  if (typeof cfg.num_voters !== 'number') return null;
  if (typeof cfg.ideology !== 'string') return null;
  if (typeof cfg.seed !== 'number') return null;
  // pinned is optional; default to empty array
  const pinned = Array.isArray(obj.pinned) ? obj.pinned : [];
  return {
    version:    obj.version,
    exportedAt: typeof obj.exportedAt === 'string' ? obj.exportedAt : new Date().toISOString(),
    config:     obj.config as ElectionConfig,
    pinned:     pinned as PinnedPerturbation[],
  };
}

function downloadJSON(filename: string, payload: unknown): void {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

const ScenarioIO: React.FC = () => {
  const { t } = useTranslation();
  const { config, replaceConfig } = useElection();
  const { pinned, clearPinned, pinPerturbation } = usePerturbations();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [toast, setToast] = useState<{ variant: 'success' | 'danger'; msg: string } | null>(null);

  const handleExport = useCallback(() => {
    const bundle = buildScenarioBundle(config, pinned);
    const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    downloadJSON(`votelab-scenario-${ts}.json`, bundle);
    setToast({ variant: 'success', msg: t('scenarioIO.exportOk') });
  }, [config, pinned, t]);

  const handleImportClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      // Always reset the input so re-importing the same file fires onChange
      e.target.value = '';
      if (!file) return;
      try {
        const text = await file.text();
        const parsed = JSON.parse(text);
        const bundle = validateScenarioBundle(parsed);
        if (!bundle) {
          setToast({ variant: 'danger', msg: t('scenarioIO.importInvalid') });
          return;
        }
        replaceConfig(bundle.config);
        // Replace pinned: clear then re-add each entry. We strip id/pinnedAt
        // so pinPerturbation regenerates them (avoids id collisions).
        clearPinned();
        bundle.pinned.forEach((p) => {
          const { id: _id, pinnedAt: _pa, ...rest } = p;
          pinPerturbation(rest);
        });
        setToast({
          variant: 'success',
          msg: t('scenarioIO.importOk', { count: bundle.pinned.length }),
        });
      } catch {
        setToast({ variant: 'danger', msg: t('scenarioIO.importInvalid') });
      }
    },
    [replaceConfig, clearPinned, pinPerturbation, t]
  );

  return (
    <>
      <Button
        variant="outline-secondary" size="sm"
        onClick={handleExport}
        data-testid="scenario-export-btn"
        title={t('scenarioIO.exportTitle')}
      >
        📤 {t('scenarioIO.export')}
      </Button>
      <Button
        variant="outline-secondary" size="sm"
        onClick={handleImportClick}
        data-testid="scenario-import-btn"
        title={t('scenarioIO.importTitle')}
      >
        📥 {t('scenarioIO.import')}
      </Button>
      <input
        ref={fileInputRef}
        type="file"
        accept="application/json,.json"
        style={{ display: 'none' }}
        onChange={handleFileChange}
        data-testid="scenario-import-input"
      />
      <ToastContainer position="top-end" className="p-3" style={{ zIndex: 11000 }}>
        {toast && (
          <Toast
            bg={toast.variant === 'success' ? 'success' : 'danger'}
            onClose={() => setToast(null)}
            show
            delay={4000}
            autohide
            data-testid={`scenario-toast-${toast.variant}`}
          >
            <Toast.Body className="text-white">{toast.msg}</Toast.Body>
          </Toast>
        )}
      </ToastContainer>
    </>
  );
};

export default ScenarioIO;
