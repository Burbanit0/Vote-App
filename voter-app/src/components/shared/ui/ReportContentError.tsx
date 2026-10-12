import React from 'react';
import { useTranslation } from 'react-i18next';
import { NEW_ISSUE_URL } from '../../../lib/repo';

// "Report a content error" (PLAN_BEYOND_CI W1.4): GitHub's issue form
// (.github/ISSUE_TEMPLATE/content-error.yml), its "where" field filled in from the
// place the reader came from: story:<story>/<step>, lab:<fiche> @ <electorate>, or
// matrix:<rule>/<criterion> for a criteria-matrix cell.
const ReportContentError: React.FC<{ where: string }> = ({ where }) => {
  const { t } = useTranslation('playground');
  return (
    <a
      data-testid="report-content-error"
      href={`${NEW_ISSUE_URL}?template=content-error.yml&where=${encodeURIComponent(where)}`}
      target="_blank"
      rel="noopener noreferrer"
      title={t('report.contentErrorTitle')}
      className="text-[0.68rem] text-muted-foreground underline-offset-2 hover:text-primary hover:underline"
    >
      {t('report.contentError')}
    </a>
  );
};

export default ReportContentError;
