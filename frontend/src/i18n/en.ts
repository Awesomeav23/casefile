/**
 * All user-facing UI strings live here (docs/ROADMAP M2: strings externalised from the
 * start, so localisation later (M29) is a data change). In-world case text comes from the
 * API, not from this file.
 */
export const en = {
  app: {
    name: 'Casefile',
    tagline: 'Every case has an answer. Prove it.',
    skipToContent: 'Skip to main content',
  },
  nav: {
    main: 'Main',
    cases: 'Cases',
    progress: 'Progress',
    settings: 'Settings',
    logIn: 'Log in',
    workspace: 'Investigation',
    overview: 'Overview',
    locations: 'Locations',
    evidence: 'Evidence',
    people: 'People',
    timeline: 'Timeline',
    board: 'Board',
    theories: 'Theories',
    accuse: 'Accuse',
  },
  common: {
    close: 'Close',
    dismiss: 'Dismiss',
    loading: 'Loading…',
    tryAgain: 'Try again',
    backToLibrary: 'Back to the case library',
    plannedIn: (milestone: string) => `This screen is planned for ${milestone}.`,
  },
  notifications: 'Notifications',
  screens: {
    landing: { title: 'Casefile', milestone: 'M8' },
    login: { title: 'Log in', milestone: 'M5' },
    register: { title: 'Create an account', milestone: 'M5' },
    resetPassword: { title: 'Reset your password', milestone: 'M5' },
    library: { title: 'Case library', milestone: 'M8' },
    briefing: { title: 'Case briefing', milestone: 'M8' },
    overview: { title: 'Overview', milestone: 'M9' },
    locations: { title: 'Locations', milestone: 'M9' },
    evidence: { title: 'Evidence', milestone: 'M9' },
    people: { title: 'People', milestone: 'M10' },
    timeline: { title: 'Timeline', milestone: 'M11' },
    board: { title: 'Evidence board', milestone: 'M12' },
    theories: { title: 'Theories', milestone: 'M13' },
    accuse: { title: 'Final accusation', milestone: 'M14' },
    results: { title: 'Case results', milestone: 'M14' },
    progress: { title: 'Your progress', milestone: 'M16' },
    settings: { title: 'Settings', milestone: 'M16' },
    notFound: {
      title: 'File not found',
      body: "This file doesn't exist, or it isn't yours.",
    },
  },
  errors: {
    network: "We couldn't reach the server. Check your connection and try again.",
    unexpected: 'Something went wrong on our side.',
  },
} as const

export type Messages = typeof en
