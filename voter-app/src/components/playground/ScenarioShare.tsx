import React from 'react';
import { useTranslation } from 'react-i18next';
import { Check, Link2, Undo2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { track } from '../../lib/analytics';
import { scenarioUrl } from '../../lib/scenarioLink';
import { useJourneyCtx, useStoreCtx } from './PlaygroundController';

/** How long "Link copied" stays on the button. */
const COPIED_MS = 2000;

/**
 * Copies a link to the scenario on screen: the election, the settings, the rule under
 * examination, the moment and the map lens. When the browser refuses the clipboard (an
 * insecure page, a denied permission), the link is shown in a field to copy by hand.
 */
export const ShareScenarioButton: React.FC = () => {
  const { config, playground } = useStoreCtx();
  const { leaderRule, activeMoment, lens } = useJourneyCtx();
  const { t } = useTranslation('playground');
  const [copied, setCopied] = React.useState(false);
  const [manual, setManual] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!copied) return;
    const timer = window.setTimeout(() => setCopied(false), COPIED_MS);
    return () => window.clearTimeout(timer);
  }, [copied]);

  const share = async () => {
    const url = scenarioUrl(
      { config, playground, rule: leaderRule, moment: activeMoment, lens },
      window.location
    );
    track('scenario_shared');
    try {
      await navigator.clipboard.writeText(url);
      setManual(null);
      setCopied(true);
    } catch {
      setManual(url);
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <Button
        data-testid="share-scenario"
        variant="outline"
        size="sm"
        className="gap-1.5"
        onClick={share}
      >
        {copied ? (
          <Check aria-hidden className="h-3.5 w-3.5" />
        ) : (
          <Link2 aria-hidden className="h-3.5 w-3.5" />
        )}
        {copied ? t('share.copied') : t('share.button')}
      </Button>
      <span role="status" className="sr-only">
        {copied ? t('share.copied') : ''}
      </span>
      {manual && (
        <input
          data-testid="share-scenario-manual"
          readOnly
          aria-label={t('share.manual')}
          value={manual}
          onFocus={(e) => e.currentTarget.select()}
          className="w-full rounded-md border border-input bg-background px-2 py-1 font-mono text-xs"
        />
      )}
    </div>
  );
};

/**
 * Shown after a link replaced the visitor's own scenario: a way back to it, and a way to keep
 * the one from the link and close the notice. Nothing shows when no link was opened.
 */
export const SharedScenarioNotice: React.FC = () => {
  const { sharedLink } = useJourneyCtx();
  const { t } = useTranslation('playground');
  if (!sharedLink) return null;
  return (
    <div
      data-testid="shared-scenario-notice"
      role="status"
      className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-primary/40 bg-primary/5 p-3 text-sm"
    >
      <p>{t('share.opened')}</p>
      <div className="flex gap-2">
        <Button
          data-testid="shared-scenario-restore"
          variant="outline"
          size="sm"
          className="gap-1.5"
          onClick={sharedLink.restore}
        >
          <Undo2 aria-hidden className="h-3.5 w-3.5" />
          {t('share.restore')}
        </Button>
        <Button
          data-testid="shared-scenario-keep"
          variant="ghost"
          size="sm"
          onClick={sharedLink.dismiss}
        >
          {t('share.keep')}
        </Button>
      </div>
    </div>
  );
};
