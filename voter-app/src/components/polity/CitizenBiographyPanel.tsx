import React from 'react';
import { useTranslation } from 'react-i18next';
import { Spinner } from '@/components/ui/spinner';
import { usePolityCitizen, type PolityCitizen } from '../../hooks/usePolityData';
import { messageOf } from '../../lib/polity/errors';
import { usePolityCtx } from './PolityController';

// One citizen's story in the shown run: their yearly census, what they did
// (by kind, each entry a chip that moves the player to its tick, with the
// model's motive and rationale when it gave them), and what others did about
// them, counted per tick.

type Entry = PolityCitizen['sections']['roles'][number];
type Received = PolityCitizen['received'][number];

const SECTIONS = [
  ['roles', 'biography.roles'],
  ['candidacies', 'biography.candidacies'],
  ['votes', 'biography.votes'],
  ['pressure_acts', 'biography.pressureActs'],
  ['petitions', 'biography.petitions'],
  ['other', 'biography.other'],
] as const;

const CitizenBiographyPanel: React.FC<{ runKey: string; citizen: number }> = ({
  runKey,
  citizen,
}) => {
  const { t } = useTranslation('polity');
  const { setCitizen, setTick } = usePolityCtx();
  const { data, isLoading, error } = usePolityCitizen(runKey, citizen);

  const eventName = (type: string) =>
    t(`biography.eventNames.${type}`, {
      defaultValue: t(`timeline.eventNames.${type}`, { defaultValue: type }),
    });
  const motif = (entry: Entry) =>
    entry.motif === null || entry.motif === undefined
      ? null
      : t(`motifs.m${entry.motif}`, { defaultValue: entry.motif_label ?? String(entry.motif) });
  const received = (item: Received) => {
    if (item.event_type === 'vote_cast' && item.code !== null && item.code !== undefined) {
      return `${eventName(item.event_type)} (${t('biography.rank', { rank: item.code + 1 })})`;
    }
    if (item.event_type === 'pressure_action' && item.code !== null && item.code !== undefined) {
      const act = ['nothing', 'signPetition', 'launchPetition', 'mobilize', 'waitForElection'][
        item.code
      ];
      return act ? t(`map.legend.${act}`) : eventName(item.event_type);
    }
    return eventName(item.event_type);
  };
  const chip = (tick: number) => (
    <button
      type="button"
      data-testid="biography-tick"
      aria-label={t('biography.goToTick', { tick })}
      className="rounded border border-primary/40 px-1.5 font-mono text-[0.68rem] tabular-nums text-primary"
      onClick={() => setTick(tick)}
    >
      {tick}
    </button>
  );

  return (
    <aside
      data-testid="polity-biography"
      aria-labelledby="polity-biography-title"
      className="rounded-md border border-primary/25 px-3 py-2"
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <h2 id="polity-biography-title" className="font-display text-sm font-semibold">
          {t('biography.title', { id: citizen })}
        </h2>
        <button
          type="button"
          data-testid="polity-biography-close"
          aria-label={t('biography.close')}
          className="rounded border border-border px-2 py-0.5 text-xs"
          onClick={() => setCitizen(null)}
        >
          ✕
        </button>
      </div>

      {isLoading && (
        <p role="status" className="flex items-center gap-2 text-xs text-muted-foreground">
          <Spinner size="sm" />
          {t('biography.loading')}
        </p>
      )}
      {error !== null && error !== undefined && (
        <p
          role="alert"
          data-testid="polity-biography-error"
          className="text-xs text-muted-foreground"
        >
          {t('biography.error', { message: messageOf(error) })}
        </p>
      )}

      {data && (
        <div className="flex flex-col gap-3 text-xs">
          <table data-testid="biography-census" className="w-full border-collapse text-left">
            <caption className="mb-1 text-left text-sm font-semibold">
              {t('biography.census')}
            </caption>
            <thead>
              <tr className="border-b border-border">
                <th scope="col" className="px-2 py-0.5">
                  {t('biography.censusYear')}
                </th>
                <th scope="col" className="px-2 py-0.5">
                  {t('biography.censusRole')}
                </th>
                <th scope="col" className="px-2 py-0.5">
                  {t('biography.censusOffice')}
                </th>
                <th scope="col" className="px-2 py-0.5">
                  {t('biography.censusParty')}
                </th>
              </tr>
            </thead>
            <tbody>
              {data.census.map((year) => (
                <tr key={year.year}>
                  <td className="px-2 py-0.5 tabular-nums">{year.year}</td>
                  <td className="px-2 py-0.5">
                    {t(`biography.roleValues.${year.role}`, { defaultValue: year.role })}
                  </td>
                  <td className="px-2 py-0.5">
                    {t(`biography.officeValues.${year.office}`, { defaultValue: year.office })}
                  </td>
                  <td className="px-2 py-0.5 tabular-nums">{year.party ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {SECTIONS.map(([key, label]) => {
            const entries = data.sections[key];
            return (
              <section key={key} data-testid={`biography-section-${key}`}>
                <h3 className="mb-1 text-sm font-semibold">
                  {t(label)}{' '}
                  <span className="font-normal text-muted-foreground">{entries.length}</span>
                </h3>
                {entries.length === 0 ? (
                  <p className="text-muted-foreground">{t('biography.empty')}</p>
                ) : (
                  <ol className="flex flex-col gap-1">
                    {entries.map((entry, i) => (
                      <li
                        key={i}
                        data-testid="biography-entry"
                        className="flex flex-wrap items-baseline gap-1.5"
                      >
                        {chip(entry.tick)}
                        <span>{eventName(entry.event_type)}</span>
                        {entry.role !== 'actor' && (
                          <span className="text-muted-foreground">
                            (
                            {entry.role === 'target'
                              ? t('biography.asTarget')
                              : t('biography.asListed')}
                            )
                          </span>
                        )}
                        {motif(entry) && (
                          <span className="text-muted-foreground">
                            {t('biography.motif', { label: motif(entry) })}
                          </span>
                        )}
                        {entry.rationale && (
                          <q className="w-full italic text-muted-foreground">{entry.rationale}</q>
                        )}
                      </li>
                    ))}
                  </ol>
                )}
              </section>
            );
          })}

          <section data-testid="biography-received">
            <h3 className="mb-1 text-sm font-semibold">{t('biography.received')}</h3>
            {data.received.length === 0 ? (
              <p className="text-muted-foreground">{t('biography.receivedEmpty')}</p>
            ) : (
              <ol className="flex flex-col gap-1">
                {data.received.map((item, i) => (
                  <li key={i} className="flex items-baseline gap-1.5">
                    {chip(item.tick)}
                    <span>
                      {t('biography.receivedCount', { count: item.count, what: received(item) })}
                    </span>
                  </li>
                ))}
              </ol>
            )}
          </section>
        </div>
      )}
    </aside>
  );
};

export default CitizenBiographyPanel;
