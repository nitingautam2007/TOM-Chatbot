import {
  DEFAULT_REGION,
  isRegion,
  type CrisisResource,
  type Region,
} from './safety.ts'
import type { Message } from './types.ts'

const SESSION_ID_KEY = 'tom_session_id'
const REGION_KEY = 'tom_region'
const MESSAGES_KEY = 'tom_messages_v1'
const CONSENT_KEY = 'tom_consent_v1'
const CONSENT_VERSION = 1
const MAX_STORED_MESSAGES = 60
const MAX_SESSION_ID_LENGTH = 128

type StorageKind = 'local' | 'session'

function getStorage(kind: StorageKind): Storage | null {
  if (typeof window === 'undefined') return null
  try {
    return kind === 'local' ? window.localStorage : window.sessionStorage
  } catch {
    // Storage can be unavailable (private mode or blocked cookies).
    return null
  }
}

function readValue(kind: StorageKind, key: string): string | null {
  try {
    return getStorage(kind)?.getItem(key) ?? null
  } catch {
    return null
  }
}

function writeValue(kind: StorageKind, key: string, value: string): void {
  try {
    getStorage(kind)?.setItem(key, value)
  } catch {
    // Ignore quota and permission errors.
  }
}

function removeValue(kind: StorageKind, key: string): void {
  try {
    getStorage(kind)?.removeItem(key)
  } catch {
    // Ignore permission errors.
  }
}

export function createId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    try {
      return crypto.randomUUID()
    } catch {
      // Fall through to the non-crypto fallback.
    }
  }
  return `tom-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export function getOrCreateSessionId(): string {
  const stored = readValue('local', SESSION_ID_KEY)
  if (stored && stored.length <= MAX_SESSION_ID_LENGTH) return stored
  const created = createId()
  writeValue('local', SESSION_ID_KEY, created)
  return created
}

export function resetSessionId(): string {
  removeValue('local', SESSION_ID_KEY)
  return getOrCreateSessionId()
}

export function getStoredRegion(): Region {
  const stored = readValue('local', REGION_KEY)
  return isRegion(stored) ? stored : DEFAULT_REGION
}

export function setStoredRegion(region: Region): void {
  writeValue('local', REGION_KEY, region)
}

export function hasConsent(): boolean {
  const raw = readValue('local', CONSENT_KEY)
  if (!raw) return false
  try {
    const parsed = JSON.parse(raw) as {
      version?: unknown
      accepted?: unknown
    }
    return parsed.version === CONSENT_VERSION && parsed.accepted === true
  } catch {
    return raw === 'true' || raw === 'accepted'
  }
}

export function saveConsent(): void {
  writeValue(
    'local',
    CONSENT_KEY,
    JSON.stringify({
      version: CONSENT_VERSION,
      accepted: true,
      at: new Date().toISOString(),
    }),
  )
}

export function clearConsent(): void {
  removeValue('local', CONSENT_KEY)
}

function isCrisisResource(value: unknown): value is CrisisResource {
  if (typeof value !== 'object' || value === null) return false
  const resource = value as Record<string, unknown>
  if (
    typeof resource.label !== 'string' ||
    typeof resource.description !== 'string'
  ) {
    return false
  }
  return ['tel', 'sms', 'url'].every(
    (key) =>
      resource[key] === undefined || typeof resource[key] === 'string',
  )
}

function parseStoredMessage(value: unknown): Message | null {
  if (typeof value !== 'object' || value === null) return null
  const stored = value as Record<string, unknown>
  if (stored.role !== 'user' && stored.role !== 'assistant') return null
  if (typeof stored.text !== 'string' || !stored.text.trim()) return null
  if (typeof stored.id !== 'string' || !stored.id) return null

  const timestampValue =
    typeof stored.timestamp === 'string' ? Date.parse(stored.timestamp) : NaN
  const timestamp = Number.isFinite(timestampValue)
    ? new Date(timestampValue)
    : new Date()

  const resources = Array.isArray(stored.resources)
    ? stored.resources.filter(isCrisisResource)
    : undefined

  return {
    id: stored.id,
    role: stored.role,
    text: stored.text,
    timestamp,
    visible: true,
    riskLevel: stored.riskLevel === 'high' ? 'high' : 'low',
    intent: typeof stored.intent === 'string' ? stored.intent : undefined,
    confidence:
      typeof stored.confidence === 'number' ? stored.confidence : undefined,
    source: typeof stored.source === 'string' ? stored.source : undefined,
    resources: resources && resources.length > 0 ? resources : undefined,
    error: stored.error === true,
    retryText: typeof stored.retryText === 'string' ? stored.retryText : undefined,
    offline: stored.offline === true,
  }
}

export function loadStoredMessages(): Message[] | null {
  const raw = readValue('session', MESSAGES_KEY)
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) return null
    const messages = parsed
      .map(parseStoredMessage)
      .filter((message): message is Message => message !== null)
      .slice(-MAX_STORED_MESSAGES)
    return messages.length > 0 ? messages : null
  } catch {
    return null
  }
}

export function saveStoredMessages(messages: Message[]): void {
  const stored = messages.slice(-MAX_STORED_MESSAGES).map((message) => ({
    id: message.id,
    role: message.role,
    text: message.text,
    timestamp: message.timestamp.toISOString(),
    riskLevel: message.riskLevel,
    intent: message.intent,
    confidence: message.confidence,
    source: message.source,
    resources: message.resources,
    error: message.error,
    retryText: message.retryText,
    offline: message.offline,
  }))
  writeValue('session', MESSAGES_KEY, JSON.stringify(stored))
}

export function clearStoredChat(): void {
  removeValue('session', MESSAGES_KEY)
}

export function clearAllStoredData(): void {
  clearStoredChat()
  clearConsent()
  removeValue('local', SESSION_ID_KEY)
  removeValue('local', REGION_KEY)
}
