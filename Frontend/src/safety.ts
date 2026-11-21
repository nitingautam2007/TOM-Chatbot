export type Region = 'IN' | 'US_CA' | 'UK' | 'INTL'

export interface CrisisResource {
  label: string
  description: string
  tel?: string
  sms?: string
  url?: string
}

export const REGION_LABELS: Record<Region, string> = {
  IN: 'India',
  US_CA: 'US & Canada',
  UK: 'UK & Ireland',
  INTL: 'International',
}

export const DEFAULT_REGION: Region = 'IN'

export const CRISIS_RESPONSE =
  "I'm really glad you told me. I want to make sure you're safe right now. " +
  'If you are in immediate danger, please call your local emergency number. ' +
  'If you can, reach out to someone you trust and stay with them. ' +
  'You deserve support from a real person right now.'

// Keep these in sync with backend/safety.py. Every entry should have a real
// phone, SMS, or web destination. Verify numbers periodically.
export const CRISIS_RESOURCES: Record<Region, CrisisResource[]> = {
  IN: [
    {
      label: 'Tele-MANAS',
      description: 'Free, 24/7 national mental health helpline.',
      tel: '14416',
    },
    {
      label: 'iCall',
      description: 'Free counselling, Monday to Saturday, 10am–8pm.',
      tel: '+91-9152987821',
      url: 'https://icallhelpline.org',
    },
    {
      label: 'AASRA',
      description: '24/7 crisis support and suicide prevention.',
      tel: '+91-9820466726',
      url: 'http://www.aasra.info',
    },
    {
      label: 'Emergency services',
      description: 'If you are in immediate danger, call now.',
      tel: '112',
    },
  ],
  US_CA: [
    {
      label: '988 Suicide & Crisis Lifeline',
      description: 'Call or text 988, free and confidential, 24/7 (US & Canada).',
      tel: '988',
      sms: '988',
    },
    {
      label: 'Crisis Text Line',
      description: 'US: text HOME to 741741. Canada: text CONNECT to 686868.',
      url: 'https://www.crisistextline.org',
    },
    {
      label: 'Emergency services',
      description: 'If you are in immediate danger, call 911.',
      tel: '911',
    },
  ],
  UK: [
    {
      label: 'Samaritans',
      description: 'Free, 24/7 listening support.',
      tel: '116123',
      url: 'https://www.samaritans.org',
    },
    {
      label: 'Shout',
      description: 'Free, 24/7 text support. Text SHOUT to 85258.',
      sms: '85258',
      url: 'https://giveusashout.org',
    },
    {
      label: 'Emergency services',
      description: 'If you are in immediate danger, call 999.',
      tel: '999',
    },
  ],
  INTL: [
    {
      label: 'Find A Helpline',
      description: 'Find a verified crisis line in your country.',
      url: 'https://findahelpline.com',
    },
    {
      label: 'Befrienders Worldwide',
      description: 'Find emotional support centres around the world.',
      url: 'https://befrienders.org',
    },
  ],
}

// A narrow, phrase-based list. Do not add bare words such as "die": they match
// grief ("my mum died") and ordinary language ("I'm dieting").
const CRISIS_PATTERNS: RegExp[] = [
  /\b(?:kill|killing)\s+(?:myself|my\s*self)\b/,
  /\b(?:want|wanna|plan|planning|intend|intending|going|gonna|about)\s+to\s+(?:kill|hurt|harm)\s+(?:myself|my\s*self)\b/,
  /\b(?:commit|committing|attempt|attempted|attempting)\s+suicide\b/,
  /\bsuicid(?:e|al)\b/,
  /\b(?:end|ending)\s+my\s+life\b/,
  /\b(?:take|taking)\s+my\s+(?:own\s+)?life\b/,
  /\b(?:want|wish|wanting|wishing)\s+to\s+die\b/,
  /\b(?:don'?t|do\s+not)\s+want\s+to\s+(?:live|be\s+here|exist|go\s+on)\b/,
  /\b(?:better\s+off\s+dead|wish\s+i\s+(?:was|were)\s+dead|rather\s+be\s+dead)\b/,
  /\bno\s+reason\s+to\s+live\b/,
  /\blife\s+(?:is|isn'?t|is\s+not)\s+worth\s+living\b/,
  /\b(?:end\s+it\s+all|ending\s+it\s+all)\b/,
  /\b(?:tired\s+of\s+living|done\s+with\s+life)\b/,
  /\b(?:wish\s+i\s+wasn'?t\s+here|wish\s+i\s+wasn'?t\s+alive)\b/,
  /\b(?:self[-\s]?harm|self[-\s]?harming)\b/,
  /\b(?:cut|cutting)\s+(?:myself|my\s+wrists?)\b/,
  /\b(?:hurt|hurting|harm|harming|injure|injuring)\s+(?:myself|my\s*self)\b/,
  /\b(?:took|take|taking|had|have)\s+(?:an?\s+)?overdose\b/,
  /\boverdosed\b/,
  /\b(?:took|take|taking|swallowed)\s+(?:too\s+many|a\s+handful\s+of)\s+(?:pills|tablets|meds|medication)\b/,
  /\b(?:hang|hanging)\s+(?:myself|my\s*self)\b/,
  /\bkms\b/,
]

const NEGATED_PATTERNS: RegExp[] = [
  /\b(?:i\s+)?(?:do\s+not|don'?t)\s+want\s+to\s+die\b/g,
  /\b(?:i\s+)?(?:do\s+not|don'?t)\s+want\s+to\s+kill\s+(?:myself|my\s*self)\b/g,
  /\b(?:i\s+am|i'm|im)\s+not\s+suicidal\b/g,
]

export function detectCrisis(text: string): boolean {
  let normalized = text.toLowerCase().replace(/’/g, "'").trim()
  for (const pattern of NEGATED_PATTERNS) {
    normalized = normalized.replace(pattern, ' ')
  }
  return CRISIS_PATTERNS.some((pattern) => pattern.test(normalized))
}

export function getCrisisResources(region: Region): CrisisResource[] {
  return CRISIS_RESOURCES[region] ?? CRISIS_RESOURCES[DEFAULT_REGION]
}

export function isRegion(value: unknown): value is Region {
  return (
    typeof value === 'string' &&
    Object.prototype.hasOwnProperty.call(CRISIS_RESOURCES, value)
  )
}
