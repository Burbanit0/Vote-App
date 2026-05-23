/**
 * PinToCentralButton — small reusable button each Perturber panel can render
 * to push its current result into the LabCentralView's pinned list.
 *
 * Usage in any Perturber panel:
 *
 *   <PinToCentralButton
 *     type="abstention"
 *     icon="📉"
 *     label="Abstention 30% (Le Pen +5%)"
 *     summary="Vainqueur: Jospin (3/5 méthodes changent)"
 *     methodsChanged={3}
 *     disabled={!data}
 *   />
 */
import React from 'react';
import { Button } from 'react-bootstrap';
import { useTranslation } from 'react-i18next';
import { usePerturbations } from '../../context/PerturbationsContext';

interface Props {
  type:            string;
  icon:            string;
  label:           string;
  summary:         string;
  methodsChanged?: number;
  disabled?:       boolean;
}

const PinToCentralButton: React.FC<Props> = ({
  type, icon, label, summary, methodsChanged, disabled,
}) => {
  const { t } = useTranslation();
  const { isPinned, pinPerturbation, unpinPerturbation } = usePerturbations();
  const pinned = isPinned(type);

  return (
    <Button
      size="sm"
      variant={pinned ? 'success' : 'outline-primary'}
      disabled={disabled}
      onClick={() => {
        if (pinned) {
          unpinPerturbation(type);
        } else {
          pinPerturbation({ type, icon, label, summary, methodsChanged });
        }
      }}
      style={{ fontSize: '0.72rem', whiteSpace: 'nowrap' }}
      data-testid={`pin-btn-${type}`}
    >
      {pinned ? '✓ ' + t('lab.pinnedCentral') : '📌 ' + t('lab.pinToCentral')}
    </Button>
  );
};

export default PinToCentralButton;
