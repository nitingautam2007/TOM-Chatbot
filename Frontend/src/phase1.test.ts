import assert from 'node:assert/strict'
import { beforeEach, describe, test } from 'node:test'
import { buildOfflineReply } from './offline.ts'
import { detectCrisis } from './safety.ts'
import {
  clearAllStoredData,
  clearStoredChat,
  getOrCreateSessionId,
  getStoredRegion,
  hasConsent,
  loadStoredMessages,
  resetSessionId,
  saveConsent,
  saveStoredMessages,
  setStoredRegion,
} from './storage.ts'
import type { Message } from './types.ts'

class MemoryStorage {
  private values = new Map<string, string>()

  getItem(key: string): string | null {
    return this.values.get(key) ?? null
  }

  setItem(key: string, value: string): void {
    this.values.set(key, String(value))
  }

  removeItem(key: string): void {
    this.values.delete(key)
  }

  clear(): void {
    this.values.clear()
  }
}

let localStorageFake: MemoryStorage
let sessionStorageFake: MemoryStorage

beforeEach(() => {
  localStorageFake = new MemoryStorage()
  sessionStorageFake = new MemoryStorage()
  Object.defineProperty(globalThis, 'window', {
    configurable: true,
    value: {
      localStorage: localStorageFake,
      sessionStorage: sessionStorageFake,
    },
  })
})

describe('deterministic safety', () => {
  test('direct crisis language is detected', () => {
    assert.equal(detectCrisis('I want to die'), true)
    assert.equal(detectCrisis("I'm going to kill myself"), true)
    assert.equal(detectCrisis('I have been self-harming'), true)
  })

  test('grief and ordinary language are not treated as crisis', () => {
    assert.equal(detectCrisis('my mum died last year'), false)
    assert.equal(detectCrisis('I am dieting'), false)
    assert.equal(detectCrisis("I'm not suicidal"), false)
  })

  test('offline crisis replies are safety-first and include resources', () => {
    const reply = buildOfflineReply('I want to kill myself', 'UK')

    assert.equal(reply.riskLevel, 'high')
    assert.equal(reply.source, 'offline_safety')
    assert.equal(reply.offline, true)
    assert.ok(reply.resources && reply.resources.length > 0)
    assert.ok(reply.text)
    assert.ok(reply.resources?.some((resource) => resource.label === 'Samaritans'))
  })

  test('offline non-crisis replies are honest and low risk', () => {
    const reply = buildOfflineReply('I feel anxious about tomorrow', 'IN')

    assert.equal(reply.riskLevel, 'low')
    assert.equal(reply.source, 'offline')
    assert.equal(reply.offline, true)
    assert.deepEqual(reply.resources, [])
    assert.match(reply.text, /can't reach TOM's server/i)
  })
})

describe('browser storage', () => {
  test('consent must be explicitly saved and can be cleared', () => {
    assert.equal(hasConsent(), false)
    saveConsent()
    assert.equal(hasConsent(), true)
    clearAllStoredData()
    assert.equal(hasConsent(), false)
  })

  test('region defaults to India and persists', () => {
    assert.equal(getStoredRegion(), 'IN')
    setStoredRegion('UK')
    assert.equal(getStoredRegion(), 'UK')
  })

  test('session ids are stable until reset', () => {
    const first = getOrCreateSessionId()
    assert.equal(getOrCreateSessionId(), first)
    assert.ok(first.length >= 16)

    const second = resetSessionId()
    assert.notEqual(second, first)
    assert.equal(getOrCreateSessionId(), second)
  })

  test('messages round-trip through session storage', () => {
    const messages: Message[] = [
      {
        id: 'user-1',
        role: 'user',
        text: 'I feel sad',
        timestamp: new Date('2026-11-05T10:00:00.000Z'),
        visible: true,
      },
      {
        id: 'bot-1',
        role: 'assistant',
        text: 'I am here with you.',
        timestamp: new Date('2026-11-05T10:00:01.000Z'),
        visible: true,
        riskLevel: 'low',
        intent: 'sadness',
        confidence: 0.8,
        source: 'classifier',
      },
    ]

    saveStoredMessages(messages)
    const loaded = loadStoredMessages()

    assert.ok(loaded)
    assert.equal(loaded?.length, 2)
    assert.equal(loaded?.[0].text, 'I feel sad')
    assert.equal(loaded?.[1].intent, 'sadness')
    assert.equal(loaded?.[1].timestamp.toISOString(), '2026-11-05T10:00:01.000Z')

    clearStoredChat()
    assert.equal(loadStoredMessages(), null)
  })

  test('deleting all data removes chat, consent, region, and session id', () => {
    saveConsent()
    setStoredRegion('UK')
    getOrCreateSessionId()
    saveStoredMessages([
      {
        id: 'user-1',
        role: 'user',
        text: 'hello',
        timestamp: new Date(),
        visible: true,
      },
    ])

    clearAllStoredData()

    assert.equal(hasConsent(), false)
    assert.equal(getStoredRegion(), 'IN')
    assert.equal(loadStoredMessages(), null)
    assert.equal(localStorageFake.getItem('tom_session_id'), null)
  })
})
