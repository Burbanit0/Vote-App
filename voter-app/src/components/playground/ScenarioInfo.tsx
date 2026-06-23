import React from 'react';
import { useTranslation } from 'react-i18next';
import InfoPopover, { InfoLine } from './InfoPopover';
import { getScenarioInfo, type ScenarioLang, type ScenarioKind } from '@/lib/scenarioInfo';

// ScenarioInfo — the ⓘ next to a synthetic preset: explains what the scenario is,
// the lesson it sets up, and what to watch. Renders nothing for an unknown id.
// `kind` selects the registry (field presets vs electorate-mixture presets).
// Test hooks: `info-<kind>-<id>` / `pop-<kind>-<id>`.

interface Props {
  scenario: string;
  kind?: ScenarioKind;
  placement?: 'top' | 'bottom' | 'left' | 'right';
}

const ScenarioInfo: React.FC<Props> = ({ scenario, kind = 'scenario', placement = 'right' }) => {
  const { i18n } = useTranslation();
  const lang: ScenarioLang = i18n.language?.startsWith('en') ? 'en' : 'fr';

  const entry = getScenarioInfo(scenario, kind);
  if (!entry) return null;

  const c = entry[lang];
  const labels =
    lang === 'en'
      ? { what: 'What:', demonstrates: 'Shows:', watch: 'Try:' }
      : { what: 'C’est quoi :', demonstrates: 'Ce que ça montre :', watch: 'À observer :' };

  return (
    <InfoPopover
      testid={`${kind}-${scenario}`}
      placement={placement}
      ariaLabel={`${lang === 'en' ? 'About' : 'À propos de'} ${c.name}`}
    >
      <p className="text-sm font-bold">{c.name}</p>
      <InfoLine label={labels.what}>{c.what}</InfoLine>
      <InfoLine label={labels.demonstrates}>{c.demonstrates}</InfoLine>
      <InfoLine label={labels.watch}>{c.watch}</InfoLine>
    </InfoPopover>
  );
};

export default ScenarioInfo;
