import React from 'react';
import { useTranslation } from 'react-i18next';
import { Spinner } from '@/components/ui/spinner';
import { usePolityCitizen, type PolityCitizen } from '../../hooks/usePolityData';
import { censusSpans, groupEntries } from '../../lib/polity/biography';
import { messageOf } from '../../lib/polity/errors';
import { PRESSURE_KEYS } from '../../lib/polity/macroSeries';
import { usePolityCtx } from './PolityController';

// One citizen's story in the shown run: their yearly census, what they did
// (by kind, each entry a chip that moves the player to its tick, with the
// model's motive and rationale when it gave them), and what others did about
// them, counted per tick.

type Entry = PolityCitizen['sections']['roles'][number];
type Received = PolityCitizen['received'][number];

const SECTIONS = [
  ['roles', 'biography.roles'],
  ['turns', 'biography.turns'],
  ['candidacies', 'biography.candidacies'],
  ['votes', 'biography.votes'],
  ['pressure_acts', 'biography.pressureActs'],
  ['petitions', 'biography.petitions'],
  ['other', 'biography.other'],
] as const;

const CENSUS_COLUMNS = ['censusYear', 'censusRole', 'censusOffice', 'censusParty'] as const;

// An agent's turn (ADR-014) or forum post (ADR-016, 017): what they said, how they moved, what they noted for
// themselves, and anything they tried that the rules do not offer.
const TURN_FIELDS = [
  ['speech', 'biography.turn.speech'],
  ['post', 'biography.turn.post'],
  ['shift', 'biography.turn.shift'],
  ['moves', 'biography.turn.moves'],
  ['bill', 'biography.turn.bill'],
  ['rationale', 'biography.turn.rationale'],
  ['note_to_self', 'biography.turn.note'],
  ['other_initiative', 'biography.turn.initiative'],
] as const;

const TurnDetails: React.FC<{ details: Entry['details'] }> = ({ details }) => {
  const { t } = useTranslation('polity');
  return (
    <dl className="grid w-full grid-cols-[max-content_1fr] gap-x-2 gap-y-0.5 pl-6">
      {TURN_FIELDS.map(([field, label]) => {
        const value = details[field];
        if (typeof value !== 'string' || !value) return null;
        const outside = field === 'other_initiative';
        return (
          <React.Fragment key={field}>
            <dt
              className={
                outside ? 'font-medium text-amber-700 dark:text-amber-400' : 'text-muted-foreground'
              }
            >
              {t(label)}
            </dt>
            <dd
              data-testid={`biography-turn-${field}`}
              className={outside ? 'font-medium' : undefined}
            >
              {field === 'speech' || field === 'post' ? <q>{value}</q> : value}
            </dd>
          </React.Fragment>
        );
      })}
    </dl>
  );
};

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
      const act = PRESSURE_KEYS[item.code];
      return act ? t(`map.legend.${act}`) : eventName(item.event_type);
    }
    return eventName(item.event_type);
  };
  const chip = (tick: number, key?: React.Key) => (
    <button
      key={key}
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
                {CENSUS_COLUMNS.map((column) => (
                  <th key={column} scope="col" className="px-2 py-0.5">
                    {t(`biography.${column}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {censusSpans(data.census).map((year) => (
                <tr key={year.year}>
                  <td className="px-2 py-0.5 tabular-nums">
                    {year.year === year.to ? year.year : `${year.year}–${year.to}`}
                  </td>
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
                    {groupEntries(entries).map(({ entry, ticks }, i) => (
                      <li
                        key={i}
                        data-testid="biography-entry"
                        className="flex flex-wrap items-baseline gap-1.5"
                      >
                        {ticks.map((tick, j) => chip(tick, j))}
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
                        {(entry.event_type === 'agent_turn' ||
                          entry.event_type === 'forum_post') && (
                          <TurnDetails details={entry.details} />
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
