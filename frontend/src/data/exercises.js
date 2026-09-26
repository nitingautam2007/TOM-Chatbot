/**
 * Phase 10 — guided stress-relief exercises (content only, no backend).
 *
 * Every exercise is a list of steps. A step with `seconds` is timed and
 * auto-advances while the exercise is running; a step without it waits for
 * the user's Next. Nothing here is clinical — these are plain relaxation
 * practices, not treatment, scoring, or diagnosis.
 */

const breathingCycle = [
  {
    label: "Inhale",
    seconds: 4,
    detail: "Breathe in slowly through your nose.",
  },
  {
    label: "Hold",
    seconds: 2,
    detail: "Keep the breath in, gently.",
  },
  {
    label: "Exhale",
    seconds: 6,
    detail: "Let the breath out slowly through your mouth.",
  },
];

export const EXERCISES = [
  {
    id: "breathing",
    title: "Breathing",
    duration: "About 1 minute",
    description:
      "A slow Inhale → Hold → Exhale cycle to help your body settle.",
    animation: "breath",
    steps: Array.from({ length: 5 }, () => breathingCycle).flat(),
  },
  {
    id: "grounding",
    title: "Grounding (5-4-3-2-1)",
    duration: "About 2 minutes",
    description:
      "Name five things you see, four you can touch, three you hear, two you smell, one you taste.",
    steps: [
      {
        label: "5 things you see",
        detail: "Look around and name five things you can see.",
      },
      {
        label: "4 things you can touch",
        detail: "Notice four things you can feel — clothes, floor, a table.",
      },
      {
        label: "3 things you can hear",
        detail: "Listen for three sounds, near or far away.",
      },
      {
        label: "2 things you can smell",
        detail: "Notice two smells around you, or one you remember.",
      },
      {
        label: "1 thing you can taste",
        detail: "Notice one taste in your mouth right now.",
      },
    ],
  },
  {
    id: "muscle",
    title: "Muscle relaxation",
    duration: "About 2 minutes",
    description:
      "Tense and release four muscle groups, one at a time, to let go of physical tension.",
    steps: [
      {
        label: "Hands",
        detail: "Make a soft fist, hold for a moment, then open and release.",
      },
      {
        label: "Shoulders",
        detail: "Lift your shoulders toward your ears, then let them drop.",
      },
      {
        label: "Face",
        detail: "Scrunch your face gently, then smooth it out.",
      },
      {
        label: "Legs",
        detail: "Press your feet down, then relax your legs completely.",
      },
    ],
  },
  {
    id: "calm",
    title: "Calm moment",
    duration: "About 1 minute",
    description:
      "A short quiet pause: slow breathing, stillness, and simple observation.",
    steps: [
      {
        label: "Slow breathing",
        seconds: 20,
        detail: "Breathe in for 4, out for 6. Nothing else to do.",
      },
      {
        label: "Quiet pause",
        seconds: 20,
        detail: "Sit still and let the moment pass without doing anything.",
      },
      {
        label: "Notice around you",
        seconds: 20,
        detail: "Look at one thing nearby and simply observe it.",
      },
    ],
  },
];
