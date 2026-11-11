import assert from 'node:assert/strict'
import { afterEach, describe, test } from 'node:test'
import {
  ChatApiError,
  deleteServerData,
  resetServerSession,
  sendChatMessage,
} from './api.ts'

type FetchCall = {
  url: string
  init?: RequestInit
}

const originalFetch = globalThis.fetch
let calls: FetchCall[] = []

function mockFetch(
  handler: (call: FetchCall) => Promise<Response> | Response,
): void {
  calls = []
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    const call = { url: String(input), init }
    calls.push(call)
    return handler(call)
  }) as typeof fetch
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

afterEach(() => {
  globalThis.fetch = originalFetch
})

describe('chat API client', () => {
  test('parses reply metadata and crisis resources', async () => {
    mockFetch(() =>
      jsonResponse({
        response: 'I am here with you.',
        intent: 'crisis',
        risk_level: 'high',
        confidence: 1,
        source: 'safety',
        resources: [
          {
            label: 'Tele-MANAS',
            description: 'Free, 24/7 support.',
            tel: '14416',
          },
        ],
      }),
    )

    const reply = await sendChatMessage('I want to die', 'session-a', 'IN', {
      retries: 0,
    })

    assert.equal(reply.text, 'I am here with you.')
    assert.equal(reply.riskLevel, 'high')
    assert.equal(reply.source, 'safety')
    assert.equal(reply.resources?.[0].label, 'Tele-MANAS')
    assert.equal(calls.length, 1)
    assert.equal(calls[0].url.endsWith('/api/chat'), true)
    assert.deepEqual(JSON.parse(String(calls[0].init?.body)), {
      message: 'I want to die',
      session_id: 'session-a',
      region: 'IN',
    })
  })

  test('reports a timeout and does not retry when retries are zero', async () => {
    mockFetch(
      ({ init }) =>
        new Promise<Response>((_, reject) => {
          init?.signal?.addEventListener('abort', () => {
            reject(new DOMException('Aborted', 'AbortError'))
          })
        }),
    )

    await assert.rejects(
      sendChatMessage('hello', 'session-b', 'IN', {
        timeoutMs: 20,
        retries: 0,
      }),
      (error: unknown) =>
        error instanceof ChatApiError && error.code === 'timeout',
    )
    assert.equal(calls.length, 1)
  })

  test('does not retry non-retryable validation errors', async () => {
    mockFetch(() =>
      jsonResponse(
        {
          error: 'message_too_long',
          response: 'Please keep your message under 2000 characters.',
        },
        413,
      ),
    )

    await assert.rejects(
      sendChatMessage('x', 'session-c', 'IN', { retries: 2 }),
      (error: unknown) =>
        error instanceof ChatApiError &&
        error.code === 'message_too_long' &&
        error.status === 413,
    )
    assert.equal(calls.length, 1)
  })

  test('retries one transient server failure', async () => {
    mockFetch(({ url }) => {
      if (!url.endsWith('/api/chat')) {
        return jsonResponse({ status: 'ok' })
      }
      return calls.length === 1
        ? jsonResponse({ error: 'server_error' }, 500)
        : jsonResponse({ response: 'Welcome back.', intent: 'greeting' })
    })

    const reply = await sendChatMessage('hello', 'session-d', 'IN', {
      retries: 1,
    })

    assert.equal(reply.text, 'Welcome back.')
    assert.equal(calls.length, 2)
  })

  test('stops retrying when the caller aborts', async () => {
    mockFetch(
      ({ init }) =>
        new Promise<Response>((_, reject) => {
          init?.signal?.addEventListener('abort', () => {
            reject(new DOMException('Aborted', 'AbortError'))
          })
        }),
    )

    const controller = new AbortController()
    const pending = sendChatMessage('hello', 'session-f', 'IN', {
      retries: 3,
      signal: controller.signal,
    })
    controller.abort()

    await assert.rejects(
      pending,
      (error: unknown) =>
        error instanceof ChatApiError && error.code === 'request_failed',
    )
    assert.equal(calls.length, 1)
  })

  test('reset and delete control calls use the right verbs', async () => {
    mockFetch(() => jsonResponse({ status: 'ok' }))

    assert.equal(await resetServerSession('session-e'), true)
    assert.equal(await deleteServerData('session-e'), true)
    assert.equal(calls[0].init?.method, 'POST')
    assert.equal(calls[1].init?.method, 'DELETE')
    assert.deepEqual(JSON.parse(String(calls[1].init?.body)), {
      session_id: 'session-e',
    })
  })
})
