import React, { useCallback } from 'react';
// react-joyride v3 types are not fully compatible with React 19 —
// suppress via 'any' casts until an updated version is released.
// eslint-disable-next-line @typescript-eslint/no-require-imports
const Joyride = require('react-joyride').default;
// eslint-disable-next-line @typescript-eslint/no-require-imports
const { STATUS } = require('react-joyride');

// ── Tour steps ─────────────────────────────────────────────────────────────

const STEPS = [
  {
    target: '[data-tour="navbar"]',
    title: '🗳️ Bienvenue sur Vote Lab',
    content:
      '3 outils sont disponibles dans ce menu : le Simulateur de scénario, la Comparaison des méthodes, et le Simulateur de crise constitutionnelle.',
    disableBeacon: true,
    placement: 'bottom',
  },
  {
    target: '[data-tour="hero"]',
    title: '▶ Simuler une élection',
    content:
      "Commencez par construire votre propre élection : définissez les candidats, l'électorat et la règle du vote blanc, puis comparez les résultats sous 5 méthodes de vote différentes.",
    placement: 'bottom',
  },
  {
    target: '[data-tour="blank-vote-card"]',
    title: '⬜ Vote Blanc',
    content:
      "Le vote blanc est modélisé comme un candidat à part entière. Chaque électeur possède un seuil d'insatisfaction qui détermine s'il le classe en tête. 4 règles constitutionnelles définissent les conséquences si le blanc gagne.",
    placement: 'top',
  },
  {
    target: '[data-tour="compare-card"]',
    title: '⚖️ Régret bayésien',
    content:
      "Le régret bayésien mesure l'insatisfaction collective générée par chaque méthode. Plus il est bas, plus la méthode élit un candidat proche des préférences réelles de la population.",
    placement: 'top',
  },
  {
    target: '[data-tour="elections-section"]',
    title: '🗺️ Élections historiques',
    content:
      "Testez sur des élections réelles : France 2002 (élimination de Jospin), France 2022 (fragmentation extrême), USA 1992 (effet Perot), et une « Élection de crise » pédagogique où le vote blanc gagne.",
    placement: 'top',
  },
];

// ── Vote Lab styles ────────────────────────────────────────────────────────

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
  buttonBack: {
    color: '#0d6efd',
    fontSize: '0.85rem',
  },
  buttonSkip: {
    color: '#6c757d',
    fontSize: '0.8rem',
  },
  buttonClose: {
    color: '#adb5bd',
  },
};

const LOCALE = {
  back:  'Précédent',
  close: 'Fermer',
  last:  'Terminer',
  next:  'Suivant',
  open:  'Ouvrir le tour',
  skip:  'Passer',
};

// ── Component ──────────────────────────────────────────────────────────────

interface Props {
  run: boolean;
  onFinish: () => void;
}

const OnboardingTour: React.FC<Props> = ({ run, onFinish }) => {
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

  const JoyrideAny = Joyride as any;

  return (
    <JoyrideAny
      run={run}
      steps={STEPS}
      callback={handleCallback}
      styles={JOYRIDE_STYLES}
      locale={LOCALE}
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
