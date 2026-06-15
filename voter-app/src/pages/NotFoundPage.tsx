/**
 * NotFoundPage — catch-all 404 for unknown / removed routes (e.g. the retired
 * /campaign, /blank-contagion, /constitutional-crisis paths). Renders a clean,
 * on-brand fallback instead of a blank screen.
 */
import React from 'react';
import { Link } from 'react-router';
import { useTranslation } from 'react-i18next';
import { useMetaTags } from '../hooks/useMetaTags';

const NotFoundPage: React.FC = () => {
  const { t } = useTranslation();
  useMetaTags({ title: '404 — Vote Lab', description: 'Page introuvable / Page not found.' });

  return (
    <div
      data-style="tailwind"
      className="mx-auto flex w-full max-w-[640px] flex-col items-center px-3 py-16 text-center"
    >
      <div className="text-6xl font-bold text-muted-foreground">404</div>
      <h1 className="mt-3 text-2xl font-semibold">{t('notFound.title', 'Page introuvable')}</h1>
      <p className="mt-2 text-muted-foreground">
        {t(
          'notFound.message',
          "Cette page n'existe pas (ou plus). Elle a peut-être été déplacée dans l'Election Lab."
        )}
      </p>
      <div className="mt-6 flex flex-wrap justify-center gap-3">
        <Link
          to="/"
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground no-underline transition-colors hover:bg-primary/90"
        >
          🏠 {t('notFound.home', "Retour à l'accueil")}
        </Link>
        <Link
          to="/playground"
          className="rounded-md border border-border px-4 py-2 text-sm font-medium no-underline transition-colors hover:bg-accent"
        >
          🎛 {t('notFound.playground', 'Playground')}
        </Link>
      </div>
    </div>
  );
};

export default NotFoundPage;
