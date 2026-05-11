import React, { useCallback } from 'react';
import { Joyride as JoyrideBase, STATUS } from 'react-joyride';
import { useTranslation } from 'react-i18next';

const Joyride = JoyrideBase as React.ComponentType<any>;

const JOYRIDE_STYLES = {
  options: {
    primaryColor: '#0d6efd',
    textColor: '#333',
    backgroundColor: '#fff',
    arrowColor: '#fff',
    zIndex: 10500,
  },
  tooltip: {
    borderRadius: 10,
    boxShadow: '0 4px 24px rgba(0,0,0,0.15)',
    padding: '1rem 1.25rem',
  },
  tooltipTitle: {
    fontSize: '1rem',
    fontWeight: 700,
    marginBottom: '0.5rem',
    color: '#0d6efd',
  },
  tooltipContent: {
    fontSize: '0.88rem',
    lineHeight: 1.55,
    color: '#444',
  },
  buttonNext: {
    backgroundColor: '#0d6efd',
    color: 'white',
    borderRadius: 6,
    padding: '6px 16px',
    fontSize: '0.85rem',
  },
  buttonBack: { color: '#0d6efd', fontSize: '0.85rem' },
  buttonSkip: { color: '#6c757d', fontSize: '0.8rem' },
  buttonClose: { color: '#adb5bd' },
};

interface Props {
  run: boolean;
  onFinish: () => void;
}

const OnboardingTour: React.FC<Props> = ({ run, onFinish }) => {
  const { t } = useTranslation();

  const steps = [
    {
      target: '[data-tour="navbar"]',
      title: t('onboarding.step1Title'),
      content: t('onboarding.step1Content'),
      disableBeacon: true,
      placement: 'bottom',
    },
    {
      target: '[data-tour="hero"]',
      title: t('onboarding.step2Title'),
      content: t('onboarding.step2Content'),
      placement: 'bottom',
    },
    {
      target: '[data-tour="blank-vote-card"]',
      title: t('onboarding.step3Title'),
      content: t('onboarding.step3Content'),
      placement: 'top',
    },
    {
      target: '[data-tour="compare-card"]',
      title: t('onboarding.step4Title'),
      content: t('onboarding.step4Content'),
      placement: 'top',
    },
    {
      target: '[data-tour="elections-section"]',
      title: t('onboarding.step5Title'),
      content: t('onboarding.step5Content'),
      placement: 'top',
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
        localStorage.setItem('tour_completed', 'true');
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
      styles={JOYRIDE_STYLES}
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

export default OnboardingTour;
