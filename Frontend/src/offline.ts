import {
  CRISIS_RESPONSE,
  detectCrisis,
  getCrisisResources,
  type Region,
} from './safety.ts'
import type { BotReply } from './types.ts'

const CONNECTION_NOTE =
  "I can't reach TOM's server right now. Your message is still here in this tab, so you can try again when the connection is back."

const OFFLINE_SUPPORT: { pattern: RegExp; text: string }[] = [
  {
    pattern: /\b(?:anxi|panic|worry|nervous|overwhelm)/i,
    text: "While we wait, try one slow breath: in for 4, hold for 4, out for 6. You don't have to sort everything out at once.",
  },
  {
    pattern: /\b(?:sleep|insomnia|tired|awake)/i,
    text: 'While we wait, dim your screens and give yourself a few quiet minutes. Rest is allowed to take time.',
  },
  {
    pattern: /\b(?:breath|ground|calm|relax)/i,
    text: 'While we wait, name 5 things you can see, 4 you can feel, 3 you can hear, 2 you can smell, and 1 you can taste.',
  },
  {
    pattern: /\b(?:lonely|alone|nobody|no one)/i,
    text: "While we wait, remember that reaching out like this takes courage. I'm still here with you.",
  },
]

/**
 * Build a local reply when the server cannot be reached.
 *
 * Crisis language always gets the same deterministic crisis response and
 * regional resources as the backend. Other messages get an honest connection
 * note plus a small supportive step.
 */
export function buildOfflineReply(input: string, region: Region): BotReply {
  if (detectCrisis(input)) {
    return {
      text: CRISIS_RESPONSE,
      intent: 'crisis',
      riskLevel: 'high',
      source: 'offline_safety',
      resources: getCrisisResources(region),
      offline: true,
    }
  }

  const support = OFFLINE_SUPPORT.find((entry) => entry.pattern.test(input))
  return {
    text: support
      ? `${CONNECTION_NOTE}\n\n${support.text}`
      : `${CONNECTION_NOTE}\n\nI'm still here. You can try again, or open Crisis resources if you need support right now.`,
    intent: 'offline',
    riskLevel: 'low',
    source: 'offline',
    resources: [],
    offline: true,
  }
}
