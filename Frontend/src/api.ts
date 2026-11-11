import type { CrisisResource, Region } from './safety.ts'
import type { BotReply } from './types.ts'

const env = (
  import.meta as ImportMeta & {
    env?: Record<string, string | undefined>
  }
).env ?? {}

export const API_BASE_URL = (
  env.VITE_TOM_API_URL ??
  env.VITE_API_BASE_URL ??
  'http://127.0.0.1:8000'
).replace(/\/$/, '')

const DEFAULT_TIMEOUT_MS = 12_000
const DEFAULT_RETRIES = 2
const RETRY_DELAYS_MS = [350, 900]
const CONTROL_TIMEOUT_MS = 4_000

export type ChatErrorCode =
  | 'timeout'
  | 'network'
  | 'server'
  | 'malformed'
  | 'rate_limited'
  | 'message_too_long'
  | 'invalid_request'
  | 'request_failed'

export class ChatApiError extends Error {
  code: ChatErrorCode
  status?: number
  retryAfter?: number

  constructor(
    code: ChatErrorCode,
    message: string,
    status?: number,
    retryAfter?: number,
  ) {
    super(message)
    this.name = 'ChatApiError'
    this.code = code
    this.status = status
    this.retryAfter = retryAfter
  }
}

export function isOfflineError(error: unknown): boolean {
  return (
    error instanceof ChatApiError &&
    ['timeout', 'network', 'server', 'malformed'].includes(error.code)
  )
}

export function isRetryableError(error: ChatApiError): boolean {
  return ['timeout', 'network', 'server'].includes(error.code)
}

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, milliseconds)
  })
}

function toChatApiError(error: unknown): ChatApiError {
  if (error instanceof ChatApiError) return error
  return new ChatApiError(
    'network',
    "I couldn't reach the TOM server. Check your connection and try again.",
  )
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

function parseResources(value: unknown): CrisisResource[] {
  if (!Array.isArray(value)) return []
  return value.filter(isCrisisResource)
}

function errorCodeForStatus(status: number): ChatErrorCode {
  if (status === 413) return 'message_too_long'
  if (status === 429) return 'rate_limited'
  if (status >= 500) return 'server'
  if (status >= 400) return 'invalid_request'
  return 'request_failed'
}

async function requestChatOnce(
  message: string,
  sessionId: string,
  region: Region,
  timeoutMs: number,
  callerSignal?: AbortSignal,
): Promise<BotReply> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  const abortFromCaller = () => controller.abort()

  if (callerSignal?.aborted) {
    controller.abort()
  } else {
    callerSignal?.addEventListener('abort', abortFromCaller)
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        session_id: sessionId,
        region,
      }),
      signal: controller.signal,
    })

    let payload: unknown = null
    try {
      payload = await response.json()
    } catch {
      payload = null
    }

    const body =
      typeof payload === 'object' && payload !== null
        ? (payload as Record<string, unknown>)
        : null

    if (!response.ok) {
      const retryAfterValue =
        typeof body?.retry_after === 'number' ? body.retry_after : undefined
      const messageText =
        typeof body?.response === 'string'
          ? body.response
          : `TOM returned ${response.status}.`
      throw new ChatApiError(
        errorCodeForStatus(response.status),
        messageText,
        response.status,
        retryAfterValue,
      )
    }

    if (typeof body?.response !== 'string' || !body.response.trim()) {
      throw new ChatApiError(
        'malformed',
        'TOM sent an empty response. Please try again.',
      )
    }

    return {
      text: body.response,
      intent: typeof body.intent === 'string' ? body.intent : undefined,
      confidence:
        typeof body.confidence === 'number' ? body.confidence : undefined,
      source: typeof body.source === 'string' ? body.source : undefined,
      riskLevel: body.risk_level === 'high' ? 'high' : 'low',
      resources: parseResources(body.resources),
    }
  } catch (error) {
    if (error instanceof ChatApiError) throw error
    if (controller.signal.aborted) {
      if (callerSignal?.aborted) {
        throw new ChatApiError('request_failed', 'Request cancelled.')
      }
      throw new ChatApiError(
        'timeout',
        'TOM took too long to respond. Please try again.',
      )
    }
    throw new ChatApiError(
      'network',
      "I couldn't reach the TOM server. Check your connection and try again.",
    )
  } finally {
    clearTimeout(timer)
    callerSignal?.removeEventListener('abort', abortFromCaller)
  }
}

export async function sendChatMessage(
  message: string,
  sessionId: string,
  region: Region,
  options: {
    timeoutMs?: number
    retries?: number
    signal?: AbortSignal
  } = {},
): Promise<BotReply> {
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS
  const retries = options.retries ?? DEFAULT_RETRIES
  let lastError: ChatApiError | null = null

  for (let attempt = 0; attempt <= retries; attempt += 1) {
    if (options.signal?.aborted) {
      throw new ChatApiError('request_failed', 'Request cancelled.')
    }

    try {
      return await requestChatOnce(
        message,
        sessionId,
        region,
        timeoutMs,
        options.signal,
      )
    } catch (error) {
      lastError = toChatApiError(error)
      if (options.signal?.aborted) throw lastError
      if (attempt >= retries || !isRetryableError(lastError)) {
        throw lastError
      }
      await delay(RETRY_DELAYS_MS[Math.min(attempt, RETRY_DELAYS_MS.length - 1)])
    }
  }

  throw (
    lastError ??
    new ChatApiError(
      'network',
      "I couldn't reach the TOM server. Check your connection and try again.",
    )
  )
}

export async function checkBackendHealth(): Promise<boolean> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), CONTROL_TIMEOUT_MS)
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`, {
      headers: { Accept: 'application/json' },
      signal: controller.signal,
    })
    return response.ok
  } catch {
    return false
  } finally {
    clearTimeout(timer)
  }
}

async function sendControlRequest(
  path: string,
  method: 'POST' | 'DELETE',
  sessionId: string,
): Promise<boolean> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), CONTROL_TIMEOUT_MS)
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId }),
      signal: controller.signal,
    })
    return response.ok
  } catch {
    return false
  } finally {
    clearTimeout(timer)
  }
}

export function resetServerSession(sessionId: string): Promise<boolean> {
  return sendControlRequest('/api/session/reset', 'POST', sessionId)
}

export function deleteServerData(sessionId: string): Promise<boolean> {
  return sendControlRequest('/api/data', 'DELETE', sessionId)
}
