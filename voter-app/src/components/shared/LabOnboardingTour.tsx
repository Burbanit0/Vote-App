/**
 * LabOnboardingTour — first-visit walkthrough of Election Lab.
 *
 * Reuses react-joyride (already a dep via the HomePage tour) but with a
 * separate localStorage key (`lab_tour_completed`) so finishing the Home
 * tour doesn't skip the Lab one and vice-versa.
 *
 * Targets data-tour="lab-*" attributes placed on the central view, the
 * pinned-perturbations panel, the focus toggle, the tab groups and the
 * animation tab.
 */
import React, { useCallback } from 'react';
import { Joyride as JoyrideBase, STATUS } from 'react-joyride';
import { useTranslation } from 'react-i18next';

const Joyride = JoyrideBase as React.ComponentType<any>;

const LS_KEY = 'lab_tour_completed';

const STYLES = {
  options: {
    primaryColor:    '#0d6efd',
    textColor:       '#333',
    backgroundColor: '#fff',
    arrowColor:      '#fff',
    zIndex:          10500,
  },
  tooltip: {
    borderRadius: 10,
    boxShadow:    '0 4px 24px rgba(0,0,0,0.15)',
    padding:      '1rem 1.25rem',
  },
  tooltipTitle: {
    fontSize:    '1rem',
    fontWeight:  700,
    marginBottom: '0.5rem',
    color:       '#0d6efd',
  },
  tooltipContent: { fontSize: '0.88rem', lineHeight: 1.55, color: '#444' },
  buttonNext: {
    backgroundColor: '#0d6efd', color: 'white',
    borderRadius: 6, padding: '6px 16px', fontSize: '0.85rem',
  },
  buttonBack:  { color: '#0d6efd', fontSize: '0.85rem' },
  buttonSkip:  { color: '#6c757d', fontSize: '0.8rem' },
  buttonClose: { color: '#adb5bd' },
};

interface Props {
  run:      boolean;
  onFinish: () => void;
}

const LabOnboardingTour: React.FC<Props> = ({ run, onFinish }) => {
  const { t } = useTranslation();

  const steps = [
    {
      target:         '[data-tour="lab-central"]',
      title:          t('labTour.step1Title'),
      content:        t('labTour.step1Content'),
      placement:      'bottom',
      disableBeacon:  true,
    },
    {
      target:    '[data-tour="lab-tabs"]',
      title:     t('labTour.step2Title'),
      content:   t('labTour.step2Content'),
      placement: 'top',
    },
    {
      target:    '[data-tour="lab-perturb-tab"]',
      title:     t('labTour.step3Title'),
      content:   t('labTour.step3Content'),
      placement: 'bottom',
    },
    {
      target:    '[data-tour="lab-animation-tab"]',
      title:     t('labTour.step4Title'),
      content:   t('labTour.step4Content'),
      placement: 'bottom',
    },
    {
      target:    '[data-tour="lab-focus"]',
      title:     t('labTour.step5Title'),
      content:   t('labTour.step5Content'),
      placement: 'left',
    },
  ];

  const locale = {
    back:  t('onboarding.back'),
    close: t('onboarding.close'),
    last:  t('onboarding.last'),
    next:  t('onboarding.next'),
    open:  t('onboarding.open'),
    skip:  t('onboarding.skip'),
  };

  const handleCallback = useCallback(
    (data: any) => {
      const { status } = data;
      if (status === STATUS.FINISHED || status === STATUS.SKIPPED) {
        try { localStorage.setItem(LS_KEY, 'true'); } catch { /* */ }
        onFinish();
      }
    },
    [onFinish]
  );

  return (
    <Joyride
      run={run}
      steps={steps}
      callback={handleCallback}
      styles={STYLES}
      locale={locale}
      continuous
      showProgress
      showSkipButton
      scrollToFirstStep
      disableOverlayClose
      spotlightClicks={false}
    />
  );
};

export default LabOnboardingTour;
export const LAB_TOUR_LS_KEY = LS_KEY;
