import React from 'react';
import { useTranslation } from 'react-i18next';

// "Report a content error" (PLAN_BEYOND_CI W1.4): GitHub's issue form
// (.github/ISSUE_TEMPLATE/content-error.yml), its "where" field filled in from the
// place the reader came from: story:<story>/<step> or lab:<fiche>.
const NEW_ISSUE = 'https://github.com/Burbanit0/Vote-App/issues/new';

const ReportContentError: React.FC<{ where: string; className?: string }> = ({
  where,
  className = '',
}) => {
  const { t } = useTranslation('playground');
  return (
    <a
      data-testid="report-content-error"
      href={`${NEW_ISSUE}?template=content-error.yml&where=${encodeURIComponent(where)}`}
      target="_blank"
      rel="noopener noreferrer"
      title={t('report.contentErrorTitle')}
      className={`text-[0.68rem] text-muted-foreground underline-offset-2 hover:text-primary hover:underline ${className}`}
    >
      {t('report.contentError')}
    </a>
  );
};

export default ReportContentError;
