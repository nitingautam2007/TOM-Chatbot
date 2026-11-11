import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type KeyboardEvent as ReactKeyboardEvent,
} from 'react'
import tomLogo from '@/imports/TOM_Bot.png'
import LandingPage from './LandingPage'
import CrisisResources from './CrisisResources'
import ConsentGate from './ConsentGate'
import PrivacyPanel from './PrivacyPanel'
import {
  ChatApiError,
  checkBackendHealth,
  deleteServerData,
  isOfflineError,
  resetServerSession,
  sendChatMessage,
} from './api'
import { buildOfflineReply } from './offline'
import { DEFAULT_REGION, detectCrisis, type Region } from './safety'
import {
  clearAllStoredData,
  clearStoredChat,
  createId,
  getOrCreateSessionId,
  getStoredRegion,
  hasConsent,
  loadStoredMessages,
  resetSessionId,
  saveConsent,
  saveStoredMessages,
  setStoredRegion,
} from './storage'
import type { Message, Mood, SupportResource } from './types'

const MAX_MESSAGE_LENGTH = 2000
const NORMAL_TIMEOUT_MS = 9_000
const OFFLINE_TIMEOUT_MS = 5_000

const MOODS: { value: Mood; emoji: string; label: string; color: string }[] = [
  { value: 1, emoji: '😔', label: 'Struggling', color: '#c47a7a' },
  { value: 2, emoji: '😕', label: 'Low', color: '#c49b5a' },
  { value: 3, emoji: '😐', label: 'Okay', color: '#8ab5c2' },
  { value: 4, emoji: '🙂', label: 'Good', color: '#7d9e7d' },
  { value: 5, emoji: '😊', label: 'Great', color: '#5a7f5a' },
]

const SUGGESTIONS = [
  "I'm feeling anxious",
  'I need to talk',
  'Breathing exercise',
  'Trouble sleeping',
  'Grounding technique',
]

// Crisis lines live in safety.ts so they stay in sync with the backend. These
// are non-emergency support and self-care resources.
const SUPPORT_RESOURCES: SupportResource[] = [
  {
    title: '5-4-3-2-1 Grounding Technique',
    desc: 'Name 5 things you see, 4 you feel, 3 you hear, 2 you smell, 1 you taste.',
    icon: '🌿',
    tag: 'Self-care',
    tagColor: '#5a7f5a',
  },
  {
    title: 'Box Breathing',
    desc: 'Inhale 4 sec → Hold 4 sec → Exhale 4 sec → Hold 4 sec. Repeat for calm.',
    icon: '🌬️',
    tag: 'Self-care',
    tagColor: '#5a7f5a',
  },
  {
    title: 'Body Scan Meditation',
    desc: 'A 10-minute practice to release tension and calm your mind.',
    icon: '🧘',
    tag: 'Self-care',
    tagColor: '#5a7f5a',
  },
  {
    title: 'Progressive Muscle Relaxation',
    desc: 'Tense and release each muscle group from toes to head.',
    icon: '🦵',
    tag: 'Self-care',
    tagColor: '#5a7f5a',
  },
  {
    title: 'Journaling Prompts',
    desc: 'Guided prompts to help you process emotions and thoughts.',
    icon: '✍️',
    tag: 'Self-care',
    tagColor: '#5a7f5a',
  },
  {
    title: 'Find a Therapist',
    desc: 'Search licensed therapists by location, specialty, and insurance.',
    icon: '🗺️',
    tag: 'Professional',
    tagColor: '#3d7a8e',
    href: 'https://www.psychologytoday.com/us/therapists',
  },
  {
    title: 'BetterHelp',
    desc: 'Online therapy with licensed counselors. Paid service.',
    icon: '💻',
    tag: 'Professional',
    tagColor: '#3d7a8e',
    href: 'https://www.betterhelp.com',
  },
  {
    title: 'Talkspace',
    desc: 'Connect with licensed therapists via text, video, or voice messaging.',
    icon: '📱',
    tag: 'Professional',
    tagColor: '#3d7a8e',
    href: 'https://www.talkspace.com',
  },
  {
    title: 'Open Path Collective',
    desc: 'Directory of therapists offering sliding-scale fees.',
    icon: '💰',
    tag: 'Professional',
    tagColor: '#3d7a8e',
    href: 'https://openpathcollective.org',
  },
  {
    title: '7 Cups',
    desc: 'Free emotional support from trained listeners. Anytime, anywhere.',
    icon: '☕',
    tag: 'Community',
    tagColor: '#8ab5c2',
    href: 'https://www.7cups.com',
  },
  {
    title: 'Mental Health Subreddits',
    desc: 'Peer support communities such as r/Anxiety and r/Depression.',
    icon: '🔴',
    tag: 'Community',
    tagColor: '#8ab5c2',
    href: 'https://www.reddit.com/r/Anxiety/',
  },
  {
    title: 'The Mighty',
    desc: 'Online community sharing real stories about mental health challenges.',
    icon: '✊',
    tag: 'Community',
    tagColor: '#8ab5c2',
    href: 'https://themighty.com',
  },
  {
    title: 'The Trevor Project',
    desc: 'Crisis and suicide prevention support for LGBTQ+ young people.',
    icon: '🏳️‍🌈',
    tag: 'Specialized',
    tagColor: '#a371f7',
    href: 'https://www.thetrevorproject.org',
  },
  {
    title: 'SAMHSA National Helpline',
    desc: 'US treatment referral and information service for substance use.',
    icon: '💊',
    tag: 'Specialized',
    tagColor: '#a371f7',
    href: 'https://www.samhsa.gov/find-help/national-helpline',
  },
  {
    title: 'Veterans Crisis Line',
    desc: 'US support for veterans, service members, and their families.',
    icon: '🎖️',
    tag: 'Specialized',
    tagColor: '#a371f7',
    href: 'https://www.veteranscrisisline.net',
  },
  {
    title: 'Disaster Distress Helpline',
    desc: 'US crisis counseling after natural or human-caused disasters.',
    icon: '🌪️',
    tag: 'Specialized',
    tagColor: '#a371f7',
    href: 'https://www.samhsa.gov/find-help/disaster-distress-helpline',
  },
  {
    title: 'Mental Health America',
    desc: 'Screening tools, education, and resources.',
    icon: '📚',
    tag: 'Education',
    tagColor: '#f8a55f',
    href: 'https://mhanational.org',
  },
  {
    title: 'NAMI',
    desc: 'Mental health education, support groups, and advocacy.',
    icon: '🎓',
    tag: 'Education',
    tagColor: '#f8a55f',
    href: 'https://www.nami.org',
  },
  {
    title: 'Headspace',
    desc: 'Guided meditation and mindfulness exercises for stress and anxiety.',
    icon: '🧠',
    tag: 'Education',
    tagColor: '#f8a55f',
    href: 'https://www.headspace.com',
  },
]

function createGreeting(): Message {
  return {
    id: createId(),
    role: 'assistant',
    text: "Hi, I'm TOM — Talk to Me. 💬\n\nI'm an AI companion, not a therapist or emergency service. This is a judgment-free space, and I'm here to listen. How are you feeling today?",
    timestamp: new Date(),
    visible: true,
  }
}

function initialMessages(): Message[] {
  if (hasConsent()) {
    const stored = loadStoredMessages()
    if (stored && stored.length > 0) return stored
  }
  return [createGreeting()]
}

function describeChatError(error: ChatApiError): string {
  if (error.code === 'rate_limited') {
    const wait =
      error.retryAfter && error.retryAfter > 0
        ? ` Try again in about ${error.retryAfter} seconds.`
        : ' Please wait a moment and try again.'
    return `${error.message}${wait}`
  }
  if (error.code === 'message_too_long') {
    return `That message is too long. Please keep it under ${MAX_MESSAGE_LENGTH} characters.`
  }
  return error.message
}

// Glass style helpers
const glass = {
  base: {
    background:
      'linear-gradient(145deg, rgba(255,255,255,0.68) 0%, rgba(255,255,255,0.42) 100%)',
    backdropFilter: 'blur(24px) saturate(1.9)',
    WebkitBackdropFilter: 'blur(24px) saturate(1.9)',
    border: '1px solid rgba(255,255,255,0.8)',
    boxShadow:
      '0 8px 32px rgba(90,127,90,0.10), 0 1.5px 0 rgba(255,255,255,0.95) inset, 0 -1px 0 rgba(90,127,90,0.05) inset',
  } as CSSProperties,
  strong: {
    background:
      'linear-gradient(145deg, rgba(255,255,255,0.82) 0%, rgba(255,255,255,0.56) 100%)',
    backdropFilter: 'blur(32px) saturate(2)',
    WebkitBackdropFilter: 'blur(32px) saturate(2)',
    border: '1px solid rgba(255,255,255,0.9)',
    boxShadow:
      '0 16px 48px rgba(90,127,90,0.12), 0 2px 0 rgba(255,255,255,1) inset, 0 -1px 0 rgba(90,127,90,0.06) inset',
  } as CSSProperties,
  pill: {
    background:
      'linear-gradient(145deg, rgba(255,255,255,0.60) 0%, rgba(255,255,255,0.32) 100%)',
    backdropFilter: 'blur(16px) saturate(1.6)',
    WebkitBackdropFilter: 'blur(16px) saturate(1.6)',
    border: '1px solid rgba(255,255,255,0.72)',
    boxShadow:
      '0 2px 8px rgba(90,127,90,0.07), 0 1px 0 rgba(255,255,255,0.9) inset',
  } as CSSProperties,
}

function TypingIndicator() {
  return (
    <div
      className="flex items-end gap-2 mb-4"
      role="status"
      aria-label="TOM is typing"
      style={{ animation: 'slideUp 0.32s cubic-bezier(0.34,1.56,0.64,1) both' }}
    >
      <div
        className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 overflow-hidden"
        style={{ background: '#0d0d12', ...glass.pill }}
      >
        <img src={tomLogo} alt="TOM" className="w-full h-full object-contain" />
      </div>
      <div className="px-4 py-3 rounded-2xl rounded-bl-sm" style={glass.base}>
        <div className="flex gap-1.5 items-center h-4" aria-hidden="true">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="w-1.5 h-1.5 rounded-full bg-sage-400 inline-block"
              style={{
                animation: 'typingBounce 1.1s ease-in-out infinite',
                animationDelay: `${i * 0.18}s`,
              }}
            />
          ))}
        </div>
        <span className="sr-only">TOM is typing…</span>
      </div>
    </div>
  )
}

function ResourceCard({
  resource,
  index,
}: {
  resource: SupportResource
  index: number
}) {
  const body = (
    <>
      <div
        className="w-10 h-10 rounded-xl flex items-center justify-center text-lg flex-shrink-0"
        style={glass.pill}
      >
        {resource.icon}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-sm font-medium text-sage-800">
            {resource.title}
          </span>
          <span
            className="text-[9px] font-medium px-1.5 py-0.5 rounded-full flex-shrink-0"
            style={{ background: resource.tagColor + '18', color: resource.tagColor }}
          >
            {resource.tag}
          </span>
        </div>
        <p className="text-xs text-sage-400 leading-snug">{resource.desc}</p>
      </div>
      {resource.href && (
        <svg
          className="w-4 h-4 text-sage-300 flex-shrink-0 mt-0.5 group-hover:text-sage-400 transition-colors"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M9 18l6-6-6-6" />
        </svg>
      )}
    </>
  )

  const style = {
    ...glass.base,
    animation: `slideUp 0.35s cubic-bezier(0.34,1.56,0.64,1) ${0.05 * index}s both`,
  }

  if (!resource.href) {
    return (
      <div className="flex items-start gap-3 p-4 rounded-2xl" style={style}>
        {body}
      </div>
    )
  }

  return (
    <a
      href={resource.href}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-start gap-3 p-4 rounded-2xl resource-row group"
      style={style}
      aria-label={`${resource.title} (opens in a new tab)`}
    >
      {body}
    </a>
  )
}

function ChatMessage({
  message,
  region,
  onRetry,
}: {
  message: Message
  region: Region
  onRetry: (message: Message) => void
}) {
  const isUser = message.role === 'user'
  const isCrisis = message.riskLevel === 'high'
  const isError = message.error === true
  const isOfflineReply = message.offline === true && !isCrisis
  const canRetry =
    !isUser && Boolean(message.retryText) && typeof onRetry === 'function'

  const bubbleStyle: CSSProperties = isUser
    ? {
        background:
          'linear-gradient(145deg, rgba(90,127,90,0.88) 0%, rgba(70,100,70,0.92) 100%)',
        backdropFilter: 'blur(20px) saturate(1.6)',
        WebkitBackdropFilter: 'blur(20px) saturate(1.6)',
        border: '1px solid rgba(120,160,120,0.5)',
        boxShadow:
          '0 4px 16px rgba(70,100,70,0.22), 0 1px 0 rgba(160,200,160,0.4) inset',
        color: '#ffffff',
      }
    : isCrisis
      ? {
          ...glass.base,
          border: '1.5px solid rgba(220, 80, 80, 0.45)',
          boxShadow: '0 8px 32px rgba(220, 80, 80, 0.15)',
        }
      : isError
        ? {
            ...glass.base,
            border: '1.5px solid rgba(196,122,122,0.45)',
            boxShadow: '0 8px 32px rgba(196,122,122,0.10)',
          }
        : isOfflineReply
          ? {
              ...glass.base,
              border: '1.5px solid rgba(196,155,90,0.38)',
            }
          : glass.base

  const textClass = isUser
    ? 'text-white'
    : isCrisis
      ? 'text-red-950 font-medium'
      : isError
        ? 'text-[#7a2e2e]'
        : isOfflineReply
          ? 'text-[#6b4f24]'
          : 'text-sage-800'

  return (
    <div
      className={`flex items-end gap-2 mb-3 ${isUser ? 'flex-row-reverse' : ''}`}
      style={{
        animation: 'slideUp 0.38s cubic-bezier(0.34,1.56,0.64,1) both',
        opacity: message.visible ? 1 : 0,
      }}
    >
      {!isUser && (
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 overflow-hidden"
          style={{ background: '#0d0d12', ...glass.pill }}
        >
          <img src={tomLogo} alt="TOM" className="w-full h-full object-contain" />
        </div>
      )}
      <div
        className={`${isCrisis ? 'max-w-[88%]' : 'max-w-[76%]'} px-4 py-3 text-sm leading-relaxed whitespace-pre-line ${
          isUser ? 'rounded-3xl rounded-br-md' : 'rounded-3xl rounded-bl-md'
        }`}
        style={bubbleStyle}
        role={isCrisis || isError ? 'alert' : undefined}
      >
        {isCrisis && (
          <div className="flex items-center gap-1 mb-1.5 text-[11px] font-semibold text-red-600 tracking-wide">
            <span aria-hidden="true">🚨</span>
            <span>Immediate support &amp; resources</span>
          </div>
        )}
        {isError && (
          <div className="flex items-center gap-1 mb-1.5 text-[11px] font-semibold text-[#7a2e2e] tracking-wide">
            <span aria-hidden="true">⚠️</span>
            <span>Couldn't send</span>
          </div>
        )}
        {isOfflineReply && (
          <div className="flex items-center gap-1 mb-1.5 text-[11px] font-semibold text-[#7a5a2e] tracking-wide">
            <span aria-hidden="true">📶</span>
            <span>Offline reply</span>
          </div>
        )}
        <span className={textClass}>{message.text}</span>
        {canRetry && (
          <button
            type="button"
            onClick={() => onRetry(message)}
            className={`mt-2 block text-[11px] font-semibold underline underline-offset-2 ${
              isError ? 'text-[#7a2e2e]' : 'text-[#6b4f24]'
            }`}
          >
            Try again
          </button>
        )}
        {isCrisis && (
          <div className="mt-3 whitespace-normal">
            <CrisisResources
              region={region}
              resources={message.resources}
              compact
              showRegionPicker={false}
            />
          </div>
        )}
        <div
          className={`text-[10px] mt-1.5 ${
            isUser
              ? 'text-sage-200/80'
              : isError
                ? 'text-[#7a2e2e]/70'
                : isOfflineReply
                  ? 'text-[#7a5a2e]/70'
                  : 'text-sage-400'
          }`}
        >
          {message.timestamp.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </div>
      </div>
    </div>
  )
}

export default function App() {
  const [showLanding, setShowLanding] = useState(true)
  const [messages, setMessages] = useState<Message[]>(initialMessages)
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [selectedMood, setSelectedMood] = useState<Mood | null>(null)
  const [moodSubmitted, setMoodSubmitted] = useState(false)
  const [showMoodSelector, setShowMoodSelector] = useState(true)
  const [activeTab, setActiveTab] = useState<'chat' | 'resources'>('chat')
  const [region, setRegion] = useState<Region>(getStoredRegion)
  const [isOffline, setIsOffline] = useState(false)
  const [consentGranted, setConsentGranted] = useState<boolean>(hasConsent)
  const [showConsent, setShowConsent] = useState(false)
  const [showPrivacy, setShowPrivacy] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)

  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const sessionIdRef = useRef<string | null>(null)
  const pendingRef = useRef(false)
  const requestTokenRef = useRef(0)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    if (consentGranted && !sessionIdRef.current) {
      sessionIdRef.current = getOrCreateSessionId()
    }
  }, [consentGranted])

  useEffect(() => {
    return () => abortRef.current?.abort()
  }, [])

  useEffect(() => {
    const reduceMotion = window.matchMedia?.(
      '(prefers-reduced-motion: reduce)',
    ).matches
    bottomRef.current?.scrollIntoView({
      behavior: reduceMotion ? 'auto' : 'smooth',
    })
  }, [messages, isTyping])

  useEffect(() => {
    if (activeTab === 'chat') {
      bottomRef.current?.scrollIntoView({ block: 'end' })
    }
  }, [activeTab])

  useEffect(() => {
    if (!consentGranted) return
    saveStoredMessages(messages)
  }, [messages, consentGranted])

  useEffect(() => {
    if (!notice) return
    const timer = window.setTimeout(() => setNotice(null), 4000)
    return () => window.clearTimeout(timer)
  }, [notice])

  useEffect(() => {
    if (!consentGranted) return

    let cancelled = false
    const refreshHealth = async () => {
      const healthy = await checkBackendHealth()
      if (!cancelled) setIsOffline(!healthy)
    }

    void refreshHealth()

    const handleOnline = () => {
      void refreshHealth()
    }
    const handleOffline = () => {
      setIsOffline(true)
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    return () => {
      cancelled = true
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [consentGranted])

  const cancelPending = useCallback(() => {
    requestTokenRef.current += 1
    pendingRef.current = false
    abortRef.current?.abort()
    abortRef.current = null
    setIsSending(false)
    setIsTyping(false)
  }, [])

  const sendMessage = useCallback(
    async (rawText: string, options: { appendUser?: boolean } = {}) => {
      const trimmed = rawText.trim()
      if (!trimmed || pendingRef.current) return
      if (!consentGranted) {
        setShowConsent(true)
        return
      }
      if (trimmed.length > MAX_MESSAGE_LENGTH) {
        setNotice(`Please keep messages under ${MAX_MESSAGE_LENGTH} characters.`)
        return
      }

      if (!sessionIdRef.current) {
        sessionIdRef.current = getOrCreateSessionId()
      }
      const sessionId = sessionIdRef.current
      if (!sessionId) return

      const token = ++requestTokenRef.current
      const abortController = new AbortController()
      abortRef.current?.abort()
      abortRef.current = abortController
      pendingRef.current = true
      setIsSending(true)
      setIsTyping(true)

      if (options.appendUser !== false) {
        const userMessage: Message = {
          id: createId(),
          role: 'user',
          text: trimmed,
          timestamp: new Date(),
          visible: true,
        }
        setMessages((previous) => [...previous, userMessage])
      }

      if (options.appendUser !== false) {
        setInput('')
      }

      try {
        const crisisMessage = detectCrisis(trimmed)
        const reply = await sendChatMessage(trimmed, sessionId, region, {
          timeoutMs:
            crisisMessage || isOffline ? OFFLINE_TIMEOUT_MS : NORMAL_TIMEOUT_MS,
          retries: crisisMessage || isOffline ? 0 : 1,
          signal: abortController.signal,
        })
        if (token !== requestTokenRef.current) return

        setIsOffline(false)
        const botMessage: Message = {
          id: createId(),
          role: 'assistant',
          text: reply.text,
          timestamp: new Date(),
          visible: true,
          riskLevel: reply.riskLevel ?? 'low',
          intent: reply.intent,
          confidence: reply.confidence,
          source: reply.source,
          resources:
            reply.resources && reply.resources.length > 0
              ? reply.resources
              : undefined,
        }
        setMessages((previous) => [...previous, botMessage])
      } catch (error) {
        if (token !== requestTokenRef.current) return

        const chatError =
          error instanceof ChatApiError
            ? error
            : new ChatApiError(
                'network',
                "I couldn't reach the TOM server. Check your connection and try again.",
              )

        if (isOfflineError(chatError)) {
          setIsOffline(true)
          const fallback = buildOfflineReply(trimmed, region)
          const fallbackMessage: Message = {
            id: createId(),
            role: 'assistant',
            text: fallback.text,
            timestamp: new Date(),
            visible: true,
            riskLevel: fallback.riskLevel ?? 'low',
            intent: fallback.intent,
            source: fallback.source,
            resources: fallback.resources,
            offline: true,
            retryText:
              fallback.riskLevel === 'high' ? undefined : trimmed,
          }
          setMessages((previous) => [...previous, fallbackMessage])
        } else {
          setIsOffline(false)
          const retryable =
            chatError.code === 'rate_limited' ||
            chatError.code === 'request_failed'
          const errorMessage: Message = {
            id: createId(),
            role: 'assistant',
            text: describeChatError(chatError),
            timestamp: new Date(),
            visible: true,
            riskLevel: 'low',
            intent: 'error',
            source: chatError.code,
            error: true,
            retryText: retryable ? trimmed : undefined,
          }
          setMessages((previous) => [...previous, errorMessage])
        }
      } finally {
        if (token === requestTokenRef.current) {
          pendingRef.current = false
          if (abortRef.current === abortController) {
            abortRef.current = null
          }
          setIsSending(false)
          setIsTyping(false)
        }
      }
    },
    [consentGranted, isOffline, region],
  )

  const handleRetry = useCallback(
    (message: Message) => {
      if (!message.retryText || pendingRef.current) return
      setMessages((previous) =>
        previous.filter((entry) => entry.id !== message.id),
      )
      void sendMessage(message.retryText, { appendUser: false })
    },
    [sendMessage],
  )

  const handleMoodSubmit = () => {
    if (!selectedMood || isSending) return
    const mood = MOODS.find((item) => item.value === selectedMood)
    if (!mood) return
    setMoodSubmitted(true)
    setShowMoodSelector(false)
    void sendMessage(
      `I'm feeling ${mood.label.toLowerCase()} today (${mood.emoji})`,
    )
  }

  const handleKeyDown = (event: ReactKeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      if (!isSending) void sendMessage(input)
    }
  }

  const handleRegionChange = (nextRegion: Region) => {
    setRegion(nextRegion)
    setStoredRegion(nextRegion)
  }

  const handleStartChat = useCallback(() => {
    if (!consentGranted) {
      setShowConsent(true)
      return
    }
    if (!sessionIdRef.current) {
      sessionIdRef.current = getOrCreateSessionId()
    }
    setShowLanding(false)
    setActiveTab('chat')
  }, [consentGranted])

  const handleAcceptConsent = useCallback(() => {
    saveConsent()
    setConsentGranted(true)
    sessionIdRef.current = getOrCreateSessionId()
    setShowConsent(false)
    setShowLanding(false)
    setActiveTab('chat')
  }, [])

  const handleDeclineConsent = useCallback(() => {
    setShowConsent(false)
  }, [])

  const handleOpenResources = useCallback(() => {
    setShowConsent(false)
    setShowPrivacy(false)
    setShowLanding(false)
    setActiveTab('resources')
  }, [])

  const handleTabChange = useCallback(
    (tab: 'chat' | 'resources') => {
      if (tab === 'chat' && !consentGranted) {
        setShowConsent(true)
        return
      }
      setActiveTab(tab)
    },
    [consentGranted],
  )

  const handleTabKeyDown = (
    event: ReactKeyboardEvent<HTMLButtonElement>,
  ) => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) {
      return
    }
    event.preventDefault()
    const nextTab: 'chat' | 'resources' =
      event.key === 'Home'
        ? 'chat'
        : event.key === 'End'
          ? 'resources'
          : activeTab === 'chat'
            ? 'resources'
            : 'chat'

    if (nextTab === 'chat' && !consentGranted) {
      handleTabChange(nextTab)
      return
    }

    handleTabChange(nextTab)
    window.requestAnimationFrame(() => {
      document.getElementById(`tom-tab-${nextTab}`)?.focus()
    })
  }

  const handleNewChat = useCallback(() => {
    cancelPending()
    const previousSession = sessionIdRef.current
    if (previousSession) void resetServerSession(previousSession)
    clearStoredChat()
    sessionIdRef.current = resetSessionId()
    setMessages([createGreeting()])
    setMoodSubmitted(false)
    setSelectedMood(null)
    setShowMoodSelector(true)
    setShowPrivacy(false)
    setShowLanding(false)
    setActiveTab('chat')
    setNotice('New conversation started.')
  }, [cancelPending])

  const handleClearChat = useCallback(() => {
    cancelPending()
    if (sessionIdRef.current) void resetServerSession(sessionIdRef.current)
    clearStoredChat()
    setMessages([createGreeting()])
    setMoodSubmitted(false)
    setSelectedMood(null)
    setShowMoodSelector(true)
    setShowPrivacy(false)
    setActiveTab('chat')
    setNotice('Conversation cleared.')
  }, [cancelPending])

  const handleDeleteData = useCallback(() => {
    cancelPending()
    if (sessionIdRef.current) void deleteServerData(sessionIdRef.current)
    clearAllStoredData()
    sessionIdRef.current = null
    setConsentGranted(false)
    setMessages([createGreeting()])
    setRegion(DEFAULT_REGION)
    setMoodSubmitted(false)
    setSelectedMood(null)
    setShowMoodSelector(true)
    setShowPrivacy(false)
    setShowConsent(false)
    setShowLanding(true)
    setActiveTab('chat')
    setNotice('Stored data deleted. Consent withdrawn.')
  }, [cancelPending])

  const overlays = (
    <>
      {showConsent && (
        <ConsentGate
          onAccept={handleAcceptConsent}
          onDecline={handleDeclineConsent}
          onOpenResources={handleOpenResources}
        />
      )}
      {showPrivacy && consentGranted && (
        <PrivacyPanel
          onClose={() => setShowPrivacy(false)}
          onNewChat={handleNewChat}
          onClearChat={handleClearChat}
          onDeleteData={handleDeleteData}
          onOpenResources={handleOpenResources}
        />
      )}
      {notice && (
        <div className="tom-toast" role="status" aria-live="polite">
          {notice}
        </div>
      )}
    </>
  )

  if (showLanding) {
    return (
      <>
        <LandingPage
          onStartChat={handleStartChat}
          onGetHelp={handleOpenResources}
        />
        {overlays}
      </>
    )
  }

  return (
    <>
      <div
        className="tom-screen flex flex-col items-center justify-center"
        style={{
          backgroundColor: '#ffffff',
          backgroundImage:
            'linear-gradient(rgba(90,127,90,0.07) 1px, transparent 1px), linear-gradient(90deg, rgba(90,127,90,0.07) 1px, transparent 1px)',
          backgroundSize: '32px 32px',
        }}
      >
        <style>{`
          @keyframes typingBounce {
            0%, 60%, 100% { transform: translateY(0); opacity: 0.5; }
            30% { transform: translateY(-5px); opacity: 1; }
          }
          @keyframes slideUp {
            from { opacity: 0; transform: translateY(14px) scale(0.96); }
            to   { opacity: 1; transform: translateY(0)   scale(1); }
          }
          @keyframes fadeIn {
            from { opacity: 0; transform: scale(0.97); }
            to   { opacity: 1; transform: scale(1); }
          }
          @keyframes shimmer {
            0%   { background-position: -200% center; }
            100% { background-position:  200% center; }
          }
          .glass-tab-active {
            background: linear-gradient(145deg, rgba(255,255,255,0.92) 0%, rgba(255,255,255,0.70) 100%);
            box-shadow: 0 2px 10px rgba(90,127,90,0.10), 0 1px 0 rgba(255,255,255,1) inset;
            border: 1px solid rgba(255,255,255,0.95);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
          }
          .glass-tab-inactive {
            background: transparent;
          }
          .ios-press:active {
            transform: scale(0.92);
            transition: transform 0.12s cubic-bezier(0.34,1.56,0.64,1);
          }
          .ios-press {
            transition: transform 0.28s cubic-bezier(0.34,1.56,0.64,1);
          }
          .suggestion-chip:active {
            transform: scale(0.94);
          }
          .suggestion-chip {
            transition: transform 0.22s cubic-bezier(0.34,1.56,0.64,1), box-shadow 0.2s ease;
          }
          .suggestion-chip:hover {
            box-shadow: 0 4px 14px rgba(90,127,90,0.14);
          }
          .resource-row {
            transition: transform 0.24s cubic-bezier(0.34,1.56,0.64,1), box-shadow 0.2s ease;
          }
          .resource-row:active {
            transform: scale(0.975);
          }
        `}</style>

        {/* App shell — liquid glass card */}
        <div
          className="tom-app-shell w-full max-w-md rounded-[2.5rem] overflow-hidden flex flex-col"
          style={{
            background: 'rgba(255,255,255,0.12)',
            backdropFilter: 'blur(12px) saturate(1.4)',
            WebkitBackdropFilter: 'blur(12px) saturate(1.4)',
            border: '1px solid rgba(255,255,255,0.45)',
            boxShadow:
              '0 24px 60px rgba(60,90,60,0.08), 0 1.5px 0 rgba(255,255,255,0.7) inset',
            animation: 'fadeIn 0.5s cubic-bezier(0.34,1.56,0.64,1) both',
          }}
        >
          {/* Header */}
          <div
            className="px-5 pt-5 pb-4 flex-shrink-0"
            style={{
              borderBottom: '1px solid rgba(90,127,90,0.1)',
              background: 'rgba(255,255,255,0.08)',
            }}
          >
            <div className="flex items-center justify-between gap-2 mb-4">
              <div className="flex items-center gap-3 min-w-0">
                <div
                  className="w-11 h-11 rounded-2xl flex items-center justify-center overflow-hidden ios-press flex-shrink-0"
                  style={{ background: '#0d0d12', ...glass.base }}
                >
                  <img
                    src={tomLogo}
                    alt="TOM logo"
                    className="w-full h-full object-contain"
                  />
                </div>
                <div className="min-w-0">
                  <h1
                    className="text-sage-800 leading-tight"
                    style={{
                      fontFamily: 'var(--font-display)',
                      fontSize: '19px',
                      fontWeight: 400,
                      letterSpacing: '-0.01em',
                    }}
                  >
                    TOM
                  </h1>
                  <p className="text-[11px] text-sage-400 font-light tracking-wide">
                    Talk to Me · Wellbeing companion
                  </p>
                </div>
              </div>
              <div className="flex items-center justify-end gap-1.5 flex-wrap flex-shrink-0">
                <button
                  type="button"
                  onClick={() => handleTabChange('resources')}
                  className="px-2.5 py-1 rounded-full text-[10px] font-semibold text-[#7a2e2e] hover:text-[#5f2020] transition-colors ios-press"
                  style={{
                    background: 'rgba(196,122,122,0.14)',
                    border: '1px solid rgba(196,122,122,0.3)',
                  }}
                  aria-label="Open crisis and support resources"
                >
                  Help
                </button>
                {consentGranted && (
                  <button
                    type="button"
                    onClick={() => setShowPrivacy(true)}
                    className="w-7 h-7 rounded-full flex items-center justify-center text-sage-600 hover:text-sage-700 transition-colors ios-press"
                    style={glass.pill}
                    title="Privacy and conversation controls"
                    aria-label="Open privacy and conversation controls"
                  >
                    <svg
                      width="13"
                      height="13"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="M12 3l7 3v5c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z" />
                    </svg>
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setShowLanding(true)}
                  className="px-2.5 py-1 rounded-full text-[10px] font-medium text-sage-600 hover:text-sage-700 transition-colors ios-press"
                  style={glass.pill}
                  aria-label="Return to the home screen"
                >
                  Home
                </button>
                <button
                  type="button"
                  onClick={() => {
                    if (moodSubmitted) setMoodSubmitted(false)
                    setShowMoodSelector(!showMoodSelector)
                  }}
                  className="px-2.5 py-1 rounded-full text-[10px] font-medium text-sage-600 hover:text-sage-700 transition-colors ios-press"
                  style={glass.pill}
                  title="Share your mood"
                  aria-label="Open mood check-in"
                >
                  Mood
                </button>
              </div>
            </div>

            {/* Tabs */}
            <div
              role="tablist"
              aria-label="TOM sections"
              className="flex gap-1 p-1 rounded-2xl"
              style={{
                background: 'rgba(90,127,90,0.06)',
                border: '1px solid rgba(90,127,90,0.08)',
              }}
            >
              {(['chat', 'resources'] as const).map((tab) => (
                <button
                  key={tab}
                  type="button"
                  role="tab"
                  id={`tom-tab-${tab}`}
                  aria-selected={activeTab === tab}
                  aria-controls={`tom-panel-${tab}`}
                  tabIndex={activeTab === tab ? 0 : -1}
                  onClick={() => handleTabChange(tab)}
                  onKeyDown={handleTabKeyDown}
                  className={`flex-1 text-xs font-medium py-1.5 rounded-xl capitalize transition-all duration-250 ios-press ${
                    activeTab === tab
                      ? 'glass-tab-active text-sage-700'
                      : 'glass-tab-inactive text-sage-400 hover:text-sage-600'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>

          {/* Chat tab */}
          {activeTab === 'chat' && (
            <div
              role="tabpanel"
              id="tom-panel-chat"
              aria-labelledby="tom-tab-chat"
              tabIndex={0}
              className="flex-1 flex flex-col min-h-0"
            >
              {/* Mood check-in */}
              {!moodSubmitted && showMoodSelector && (
                <div
                  className="mx-4 mt-4 p-4 rounded-3xl flex-shrink-0 relative"
                  style={{
                    ...glass.base,
                    animation:
                      'slideUp 0.4s cubic-bezier(0.34,1.56,0.64,1) 0.1s both',
                  }}
                >
                  <button
                    type="button"
                    onClick={() => {
                      setShowMoodSelector(false)
                      setSelectedMood(null)
                    }}
                    className="absolute top-2 right-2 w-7 h-7 rounded-full flex items-center justify-center text-sage-400 hover:text-sage-600 hover:bg-sage-600/10 transition-colors ios-press"
                    title="Skip mood selection"
                    aria-label="Skip mood check-in"
                  >
                    ×
                  </button>
                  <p className="text-xs font-medium text-sage-600 mb-3 tracking-wide">
                    How are you feeling right now?
                  </p>
                  <div className="flex justify-between mb-3">
                    {MOODS.map((mood) => (
                      <button
                        key={mood.value}
                        type="button"
                        onClick={() => setSelectedMood(mood.value)}
                        aria-pressed={selectedMood === mood.value}
                        aria-label={mood.label}
                        className="flex flex-col items-center gap-1 p-2 rounded-2xl ios-press"
                        style={
                          selectedMood === mood.value
                            ? {
                                background: 'rgba(255,255,255,0.9)',
                                boxShadow: `0 4px 16px ${mood.color}30, 0 1px 0 rgba(255,255,255,1) inset`,
                                border: `1px solid ${mood.color}30`,
                                transform: 'scale(1.12)',
                              }
                            : {
                                background: 'transparent',
                                border: '1px solid transparent',
                              }
                        }
                      >
                        <span
                          className="text-xl"
                          style={{
                            filter:
                              selectedMood === mood.value
                                ? 'drop-shadow(0 2px 4px rgba(0,0,0,0.15))'
                                : 'none',
                          }}
                        >
                          {mood.emoji}
                        </span>
                        <span className="text-[9px] text-sage-500 font-medium">
                          {mood.label}
                        </span>
                      </button>
                    ))}
                  </div>
                  <button
                    type="button"
                    onClick={handleMoodSubmit}
                    disabled={!selectedMood || isSending}
                    className="w-full py-2 rounded-2xl text-xs font-medium ios-press disabled:opacity-40 disabled:cursor-not-allowed"
                    style={{
                      background: selectedMood
                        ? 'linear-gradient(145deg, rgba(90,127,90,0.88) 0%, rgba(70,100,70,0.92) 100%)'
                        : 'rgba(90,127,90,0.25)',
                      color: '#fff',
                      border: '1px solid rgba(120,160,120,0.4)',
                      boxShadow: selectedMood
                        ? '0 4px 14px rgba(70,100,70,0.22), 0 1px 0 rgba(160,200,160,0.4) inset'
                        : 'none',
                    }}
                  >
                    Share my mood
                  </button>
                </div>
              )}

              {isOffline && (
                <div
                  role="status"
                  aria-live="polite"
                  className="mx-4 mt-3 px-3 py-2 rounded-2xl text-[11px] leading-snug text-[#7a5a2e]"
                  style={{
                    background: 'rgba(196,155,90,0.12)',
                    border: '1px solid rgba(196,155,90,0.28)',
                  }}
                >
                  Offline mode — replies are limited. Crisis support is still
                  available in{' '}
                  <button
                    type="button"
                    onClick={() => handleTabChange('resources')}
                    className="underline font-semibold"
                  >
                    Resources
                  </button>
                  .
                </div>
              )}

              {/* Messages */}
              <div
                className="flex-1 overflow-y-auto px-4 py-4 min-h-0 mx-3 my-3 rounded-3xl"
                role="log"
                aria-live="polite"
                aria-relevant="additions"
                aria-label="Conversation with TOM"
                aria-busy={isSending}
                style={{
                  background: 'rgba(255,255,255,0.10)',
                  backdropFilter: 'blur(8px) saturate(1.3)',
                  WebkitBackdropFilter: 'blur(8px) saturate(1.3)',
                  border: '1px solid rgba(255,255,255,0.38)',
                  boxShadow:
                    '0 4px 16px rgba(90,127,90,0.04), 0 1px 0 rgba(255,255,255,0.6) inset',
                }}
              >
                {messages.map((message) => (
                  <ChatMessage
                    key={message.id}
                    message={message}
                    region={region}
                    onRetry={handleRetry}
                  />
                ))}
                {isTyping && <TypingIndicator />}
                <div ref={bottomRef} />
              </div>

              {/* Suggestions */}
              <div className="px-4 pb-1 flex-shrink-0">
                <div
                  className="overflow-x-auto pb-2"
                  style={{
                    scrollbarWidth: 'thin',
                    scrollbarColor: 'rgba(90,127,90,0.25) transparent',
                  }}
                >
                  <style>{`
                    .suggestions-scroll::-webkit-scrollbar { height: 3px; }
                    .suggestions-scroll::-webkit-scrollbar-track { background: rgba(90,127,90,0.06); border-radius: 2px; }
                    .suggestions-scroll::-webkit-scrollbar-thumb { background: rgba(90,127,90,0.28); border-radius: 2px; }
                  `}</style>
                  <div
                    className="suggestions-scroll flex gap-2 w-max overflow-x-auto pb-1"
                    style={{
                      scrollbarWidth: 'thin',
                      scrollbarColor:
                        'rgba(90,127,90,0.25) rgba(90,127,90,0.06)',
                    }}
                  >
                    {SUGGESTIONS.map((suggestion) => (
                      <button
                        key={suggestion}
                        type="button"
                        onClick={() => void sendMessage(suggestion)}
                        disabled={isSending}
                        className="text-[11px] text-sage-600 rounded-full px-3 py-2 whitespace-nowrap flex-shrink-0 suggestion-chip font-medium disabled:opacity-40 disabled:cursor-not-allowed"
                        style={glass.pill}
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Input */}
              <div
                className="tom-composer px-6 pt-2 flex-shrink-0"
                style={{ borderTop: '1px solid rgba(90,127,90,0.07)' }}
              >
                <div
                  className="flex items-center gap-2 rounded-3xl px-3 py-2.5"
                  style={{
                    background:
                      'linear-gradient(145deg, rgba(255,255,255,0.72) 0%, rgba(255,255,255,0.48) 100%)',
                    backdropFilter: 'blur(24px) saturate(1.9)',
                    WebkitBackdropFilter: 'blur(24px) saturate(1.9)',
                    border: '1px solid rgba(255,255,255,0.88)',
                    boxShadow:
                      '0 4px 20px rgba(90,127,90,0.09), 0 1.5px 0 rgba(255,255,255,0.95) inset, 0 -1px 0 rgba(90,127,90,0.05) inset',
                  }}
                >
                  <textarea
                    ref={inputRef}
                    value={input}
                    onChange={(event) => setInput(event.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Share what's on your mind…"
                    rows={1}
                    maxLength={MAX_MESSAGE_LENGTH}
                    enterKeyHint="send"
                    aria-label="Message TOM"
                    aria-describedby="tom-composer-note"
                    className="flex-1 bg-transparent text-sm text-sage-800 placeholder:text-sage-300 resize-none outline-none leading-relaxed max-h-24 overflow-y-auto"
                    style={{ minHeight: '24px', fontFamily: 'var(--font-body)' }}
                  />
                  <button
                    type="button"
                    onClick={() => void sendMessage(input)}
                    disabled={!input.trim() || isSending}
                    aria-label={isSending ? 'Sending message' : 'Send message'}
                    aria-busy={isSending}
                    className="w-9 h-9 rounded-2xl flex items-center justify-center flex-shrink-0 ios-press disabled:opacity-35 disabled:cursor-not-allowed"
                    style={{
                      background: input.trim()
                        ? 'linear-gradient(145deg, rgba(90,127,90,0.9) 0%, rgba(60,95,60,0.95) 100%)'
                        : 'rgba(90,127,90,0.2)',
                      border: '1px solid rgba(120,160,120,0.4)',
                      boxShadow: input.trim()
                        ? '0 3px 10px rgba(70,100,70,0.28), 0 1px 0 rgba(160,200,160,0.4) inset'
                        : 'none',
                      color: '#fff',
                    }}
                  >
                    <svg
                      width="13"
                      height="13"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="M22 2L11 13" />
                      <path d="M22 2L15 22 11 13 2 9l20-7z" />
                    </svg>
                  </button>
                </div>
                {input.length > MAX_MESSAGE_LENGTH - 200 && (
                  <p
                    className="text-[10px] text-sage-400 text-right mt-1"
                    aria-live="polite"
                  >
                    {input.length} / {MAX_MESSAGE_LENGTH}
                  </p>
                )}
                <p
                  id="tom-composer-note"
                  className="text-[10px] text-sage-300/80 text-center mt-2 tracking-wide"
                >
                  TOM is an AI companion, not a therapist or emergency service ·{' '}
                  <button
                    type="button"
                    onClick={() => handleTabChange('resources')}
                    className="underline hover:text-sage-400 transition-colors"
                    aria-label="Open crisis resources"
                  >
                    Crisis resources
                  </button>
                </p>
              </div>
            </div>
          )}

          {/* Resources tab */}
          {activeTab === 'resources' && (
            <div
              role="tabpanel"
              id="tom-panel-resources"
              aria-labelledby="tom-tab-resources"
              tabIndex={0}
              className="flex-1 overflow-y-auto px-4 py-5 space-y-2.5"
            >
              <CrisisResources
                region={region}
                onRegionChange={handleRegionChange}
              />

              <p
                className="text-sage-700 mb-2 mt-5"
                style={{
                  fontFamily: 'var(--font-display)',
                  fontSize: '20px',
                  fontWeight: 400,
                  letterSpacing: '-0.01em',
                  animation:
                    'slideUp 0.35s cubic-bezier(0.34,1.56,0.64,1) both',
                }}
              >
                Support resources
              </p>

              {SUPPORT_RESOURCES.map((resource, index) => (
                <ResourceCard
                  key={resource.title}
                  resource={resource}
                  index={index}
                />
              ))}

              <div
                className="mt-2 p-4 rounded-2xl text-xs text-mist-600 leading-relaxed"
                style={{
                  background: 'rgba(61,122,142,0.06)',
                  border: '1px solid rgba(61,122,142,0.12)',
                }}
              >
                <strong className="font-medium text-mist-700">
                  A note of care.
                </strong>{' '}
                TOM is an AI companion, not a therapist, doctor, or emergency
                service. It can make mistakes. If you are in crisis or danger,
                contact a crisis line or emergency services immediately.
              </div>
            </div>
          )}
        </div>
      </div>
      {overlays}
    </>
  )
}
