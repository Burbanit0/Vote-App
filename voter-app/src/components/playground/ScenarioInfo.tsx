import React from 'react';
import { useTranslation } from 'react-i18next';
import InfoPopover, { InfoLine } from './InfoPopover';
import { getScenarioInfo, type ScenarioLang } from '@/lib/scenarioInfo';

// ScenarioInfo — the ⓘ next to a synthetic preset: explains what the scenario is,
// the lesson it sets up, and what to watch. Renders nothing for an unknown id.
// Test hooks: `info-scenario-<id>` / `pop-scenario-<id>`.

interface Props {
  scenario: string;
  placement?: 'top' | 'bottom' | 'left' | 'right';
}

const ScenarioInfo: React.FC<Props> = ({ scenario, placement = 'right' }) => {
  const { i18n } = useTranslation();
  const lang: ScenarioLang = i18n.language?.startsWith('en') ? 'en' : 'fr';

  const entry = getScenarioInfo(scenario);
  if (!entry) return null;

  const c = entry[lang];
  const labels =
    lang === 'en'
      ? { what: 'What:', demonstrates: 'Shows:', watch: 'Try:' }
      : { what: 'C’est quoi :', demonstrates: 'Ce que ça montre :', watch: 'À observer :' };

  return (
    <InfoPopover
      testid={`scenario-${scenario}`}
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
