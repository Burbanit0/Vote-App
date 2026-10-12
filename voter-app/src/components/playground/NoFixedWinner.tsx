import React from 'react';
import { useTranslation } from 'react-i18next';

/** "No fixed winner", for the random ballot wherever a winner would be shown. */
const NoFixedWinner: React.FC<{ className?: string }> = ({ className }) => {
  const { t } = useTranslation('playground');
  return (
    <strong
      data-testid="no-fixed-winner"
      title={t('strip.noFixedWinnerTitle')}
      className={className}
    >
      {t('strip.noFixedWinner')}
    </strong>
  );
};

export default NoFixedWinner;
