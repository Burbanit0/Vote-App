// Playground i18n bundle (English). Mirrors playground.fr.ts exactly (typed).
import type { PlaygroundKeys } from './playground.fr';

const pgEn: PlaygroundKeys = {
  masthead: {
    kicker: 'Vote Lab — a laboratory of voting theory',
    title: 'Voting instrument',
    subtitle:
      'One instrument, from simple to complex: pick the question, then move moment by moment and read the effects live.',
  },
  mode: {
    leader: 'Leader',
    assembly: 'Assembly',
  },
  moments: {
    electorate: { label: 'Electorate', hint: 'Who votes, how they cluster and behave.' },
    method: { label: 'Method', hint: 'The counting rule and the shape of the ballot.' },
    strategy: { label: 'Strategy', hint: 'Tactical voting, blank votes, manipulation.' },
    campaign: { label: 'Campaign', hint: 'How the vote reacts over time.' },
    bilan: { label: 'Verdict', hint: 'The verdict — what it is worth, by your values.' },
  },
  guided: {
    start: 'Start',
    restart: '↻ Replay',
    moment: 'Moment {{n}} / {{total}}',
    next: '{{label}} →',
  },
  explore: {
    heading: 'Go further',
  },
  anchors: {
    mechanisms: {
      title: '⚙️ Other decision procedures',
      subtitle: '11 mechanisms (jury, sortition, delegation…)',
    },
    systems: {
      title: '🔬 Systems & districts',
      subtitle: '7 views (coalitions, districts, gerrymander…)',
    },
    results: {
      title: '📋 Full results (tally)',
      subtitle: 'every method · animation',
    },
    analysis: {
      title: '🔬 Deep analysis of the current result',
      subtitle: 'distributions · regret · manipulability',
    },
    theory: {
      title: '🔬 Social-choice theory & paradoxes',
      subtitle: 'Sen · judgment · McKelvey · power · democratic backsliding…',
    },
  },
  common: {
    loading: 'Loading…',
  },
};

export default pgEn;
