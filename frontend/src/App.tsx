import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type KeyboardEvent as ReactKeyboardEvent,
  type MouseEvent as ReactMouseEvent,
} from 'react'
import tomLogo from '@/imports/TOM_Bot.png'
import LandingPage from './LandingPage'
import CrisisResources from './CrisisResources'
import ConsentGate from './ConsentGate'
import PrivacyPanel from './PrivacyPanel'
import MoodDashboard from './MoodDashboard'
import {
  ChatApiError,
  checkBackendHealth,
  deleteServerData,
  isOfflineError,
  resetMoodStats,
  resetServerSession,
  sendChatMessage,
} from './api'
import { buildOfflineReply } from './offline'
import { DEFAULT_REGION, detectCrisis, type Region } from './safety'
import {
  clearAllStoredData,
  clearStoredChat,
  createId,
  deleteConversationFromHistory,
  getOrCreateSessionId,
  getStoredRegion,
  hasConsent,
  loadAllConversations,
  loadStoredMessages,
  resetSessionId,
  saveConsent,
  saveConversationToHistory,
  saveStoredMessages,
  setStoredRegion,
  type SavedConversation,
} from './storage'
import type { Message, Mood, SupportResource } from './types'

const MAX_MESSAGE_LENGTH = 2000
const NORMAL_TIMEOUT_MS = 60_000
const OFFLINE_TIMEOUT_MS = 60_000

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
        style={{ background: '#ffffff', border: '1px solid rgba(90,127,90,0.15)', ...glass.pill }}
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
          background: '#ffffff',
          border: '1.5px solid rgba(220, 80, 80, 0.45)',
          boxShadow: '0 8px 32px rgba(220, 80, 80, 0.15)',
        }
      : isError
        ? {
            background: '#ffffff',
            border: '1.5px solid rgba(196,122,122,0.45)',
            boxShadow: '0 8px 32px rgba(196,122,122,0.10)',
          }
        : isOfflineReply
          ? {
              background: '#ffffff',
              border: '1.5px solid rgba(196,155,90,0.38)',
              boxShadow: '0 4px 16px rgba(196,155,90,0.08)',
            }
          : {
              background: '#ffffff',
              border: '1px solid rgba(90,127,90,0.18)',
              boxShadow: '0 4px 20px rgba(90,127,90,0.08)',
            }

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
          style={{ background: '#ffffff', border: '1px solid rgba(90,127,90,0.15)', ...glass.pill }}
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
          {(message.timestamp instanceof Date
            ? message.timestamp
            : new Date(message.timestamp)
          ).toLocaleTimeString([], {
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
  const [activeTab, setActiveTab] = useState<'chat' | 'dashboard' | 'resources'>('chat')
  const [region, setRegion] = useState<Region>(getStoredRegion)
  const [isOffline, setIsOffline] = useState(false)
  const [consentGranted, setConsentGranted] = useState<boolean>(hasConsent)
  const [showConsent, setShowConsent] = useState(false)
  const [showPrivacy, setShowPrivacy] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)
  const [conversations, setConversations] = useState<SavedConversation[]>(loadAllConversations)

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

  // Auto-resize composer textarea as text wraps or Shift+Enter is pressed
  useEffect(() => {
    const el = inputRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(Math.max(el.scrollHeight, 36), 220)}px`
  }, [input])

  useEffect(() => {
    if (!consentGranted) return
    saveStoredMessages(messages)

    // Persist into multi-conversation history when user interacts
    const firstUserMsg = messages.find((m) => m.role === 'user')
    if (firstUserMsg && sessionIdRef.current) {
      const title =
        firstUserMsg.text.length > 26
          ? `${firstUserMsg.text.slice(0, 26)}…`
          : firstUserMsg.text
      const convo: SavedConversation = {
        id: sessionIdRef.current,
        title,
        updatedAt: new Date().toISOString(),
        messages,
      }
      saveConversationToHistory(convo)
      setConversations(loadAllConversations())
    }
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
    async (
      rawText: string,
      options: { appendUser?: boolean; moodLabel?: string } = {},
    ) => {
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
          moodLabel: options.moodLabel,
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

  const handleMoodSubmit = (moodValue?: Mood) => {
    const val = moodValue ?? selectedMood
    if (!val || isSending) return
    const mood = MOODS.find((item) => item.value === val)
    if (!mood) return
    setSelectedMood(mood.value)
    setMoodSubmitted(true)
    setShowMoodSelector(false)
    const moodKey = mood.label.toLowerCase()
    void sendMessage(
      `I'm feeling ${moodKey} today (${mood.emoji})`,
      { moodLabel: moodKey },
    )
  }

  const handleKeyDown = (event: ReactKeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      if (!isSending && input.trim()) {
        void sendMessage(input)
        if (inputRef.current) {
          inputRef.current.style.height = 'auto'
        }
      }
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
    // Always start a brand-new session on fresh consent — never reuse old data
    sessionIdRef.current = resetSessionId()
    clearStoredChat()
    setMessages([createGreeting()])
    setConversations(loadAllConversations())
    setMoodSubmitted(false)
    setSelectedMood(null)
    setShowMoodSelector(true)
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
    (tab: 'chat' | 'dashboard' | 'resources') => {
      if (tab === 'chat' && !consentGranted) {
        setShowConsent(true)
        return
      }
      setActiveTab(tab)
    },
    [consentGranted],
  )

  const handleSelectConversation = useCallback(
    (conv: SavedConversation) => {
      cancelPending()
      sessionIdRef.current = conv.id
      setMessages(conv.messages)
      setActiveTab('chat')
      setMobileSidebarOpen(false)
    },
    [cancelPending],
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

  const handleDeleteConversation = useCallback(
    (id: string, e: ReactMouseEvent) => {
      e.stopPropagation()
      deleteConversationFromHistory(id)
      setConversations(loadAllConversations())
      if (sessionIdRef.current === id) {
        handleNewChat()
      }
    },
    [handleNewChat],
  )

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
    void deleteServerData(sessionIdRef.current || '')
    void resetMoodStats()
    clearAllStoredData()
    sessionIdRef.current = null
    setConsentGranted(false)
    setMessages([createGreeting()])
    setConversations([])
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
        className="w-full h-screen h-[100dvh] flex overflow-hidden relative"
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
            from { opacity: 0; transform: scale(0.98); }
            to   { opacity: 1; transform: scale(1); }
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
            transform: scale(0.95);
            transition: transform 0.12s cubic-bezier(0.34,1.56,0.64,1);
          }
          .ios-press {
            transition: transform 0.2s cubic-bezier(0.34,1.56,0.64,1);
          }
          .suggestion-chip:hover {
            box-shadow: 0 4px 14px rgba(90,127,90,0.18);
            transform: translateY(-1px);
            border-color: rgba(90,127,90,0.42) !important;
            background-color: #f8fbf8 !important;
          }
          .suggestion-chip {
            transition: all 0.2s ease;
            background-color: #ffffff !important;
            background: #ffffff !important;
            opacity: 1 !important;
          }
          .starter-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(90,127,90,0.12);
            border-color: rgba(90,127,90,0.35);
          }
          .starter-card {
            transition: all 0.2s ease;
            background-color: #ffffff !important;
            background: #ffffff !important;
            opacity: 1 !important;
          }
          textarea:focus,
          textarea:focus-visible,
          textarea:active {
            outline: none !important;
            box-shadow: none !important;
            border: none !important;
            -webkit-tap-highlight-color: transparent !important;
          }
        `}</style>

        {/* Mobile Sidebar Backdrop Overlay */}
        {mobileSidebarOpen && (
          <div
            onClick={() => setMobileSidebarOpen(false)}
            className="fixed inset-0 bg-sage-900/20 backdrop-blur-sm z-40 md:hidden"
            aria-hidden="true"
          />
        )}

        {/* ── LEFT DESKTOP SIDEBAR ── */}
        <aside
          className={`fixed md:static inset-y-0 left-0 w-72 lg:w-80 h-full flex flex-col z-50 md:z-20 transition-transform duration-300 ease-in-out ${
            mobileSidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
          }`}
          style={{
            background: 'rgba(255,255,255,0.85)',
            backdropFilter: 'blur(32px) saturate(2)',
            WebkitBackdropFilter: 'blur(32px) saturate(2)',
            borderRight: '1px solid rgba(90,127,90,0.12)',
            boxShadow: '4px 0 24px rgba(90,127,90,0.04)',
          }}
        >
          {/* Sidebar Header */}
          <div className="p-5 flex items-center justify-between border-b border-sage-900/10">
            <div className="flex items-center gap-3">
              <div
                className="w-10 h-10 rounded-2xl flex items-center justify-center overflow-hidden flex-shrink-0"
                style={{ background: '#ffffff', border: '1px solid rgba(90,127,90,0.15)' }}
              >
                <img src={tomLogo} alt="TOM logo" className="w-full h-full object-contain" />
              </div>
              <div>
                <h1
                  className="text-sage-800 leading-tight"
                  style={{
                    fontFamily: 'var(--font-display)',
                    fontSize: '18px',
                    fontWeight: 400,
                    letterSpacing: '-0.01em',
                  }}
                >
                  TOM
                </h1>
                <p className="text-[11px] text-sage-400 font-light">Talk To Me · Wellbeing</p>
              </div>
            </div>

            <div
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-semibold"
              style={{
                background: 'rgba(90,127,90,0.1)',
                border: '1px solid rgba(90,127,90,0.25)',
                color: '#384f38',
              }}
            >
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#5a7f5a', display: 'inline-block', boxShadow: '0 0 6px #5a7f5a' }} />
              Local
            </div>
          </div>

          {/* New Conversation Button */}
          <div className="p-4 pb-1">
            <button
              type="button"
              onClick={() => {
                handleNewChat()
                setMobileSidebarOpen(false)
              }}
              className="w-full py-2.5 px-4 rounded-2xl text-xs font-semibold text-white flex items-center justify-center gap-2 shadow-sm ios-press"
              style={{
                background: 'linear-gradient(145deg, rgba(90,127,90,0.92) 0%, rgba(65,95,65,0.95) 100%)',
                border: '1px solid rgba(120,160,120,0.3)',
                boxShadow: '0 4px 14px rgba(70,100,70,0.22)',
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="12" y1="5" x2="12" y2="19"></line>
                <line x1="5" y1="12" x2="19" y2="12"></line>
              </svg>
              New Conversation
            </button>
          </div>

          {/* Chat History List */}
          <div className="px-4 py-2 flex flex-col min-h-0 border-b border-sage-900/10">
            <div className="flex items-center justify-between mb-1.5 px-1">
              <span className="text-[10px] font-semibold text-sage-600 uppercase tracking-wider">
                Chat History
              </span>
              {conversations.length > 0 && (
                <span className="text-[10px] text-sage-400 font-medium">
                  {conversations.length}
                </span>
              )}
            </div>

            <div className="space-y-1 max-h-36 overflow-y-auto scrollbar-none pr-0.5">
              {conversations.length === 0 ? (
                <p className="text-[11px] text-sage-400 px-2 py-1 italic">
                  Past conversations will appear here
                </p>
              ) : (
                conversations.map((conv) => {
                  const isActive = conv.id === sessionIdRef.current
                  return (
                    <div
                      key={conv.id}
                      onClick={() => handleSelectConversation(conv)}
                      className={`group flex items-center justify-between px-2.5 py-1.5 rounded-xl text-xs cursor-pointer transition-all ${
                        isActive
                          ? 'bg-sage-600/15 text-sage-900 font-semibold border border-sage-600/25 shadow-2xs'
                          : 'text-sage-600 hover:bg-white/80 hover:text-sage-800'
                      }`}
                    >
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        <span className="text-xs flex-shrink-0">💬</span>
                        <span className="truncate text-[11px]">{conv.title}</span>
                      </div>
                      <button
                        type="button"
                        onClick={(e) => handleDeleteConversation(conv.id, e)}
                        className="opacity-0 group-hover:opacity-100 hover:text-red-600 p-1 rounded-md text-[10px] transition-all ml-1"
                        title="Delete chat"
                        aria-label="Delete chat"
                      >
                        ✕
                      </button>
                    </div>
                  )
                })
              )}
            </div>
          </div>

          {/* 3-Tab Switcher */}
          <div className="px-4 py-2">
            <div
              role="tablist"
              className="flex gap-1 p-1 rounded-2xl"
              style={{
                background: 'rgba(90,127,90,0.06)',
                border: '1px solid rgba(90,127,90,0.1)',
              }}
            >
              <button
                type="button"
                onClick={() => {
                  handleTabChange('chat')
                  setMobileSidebarOpen(false)
                }}
                className={`flex-1 text-[11px] font-medium py-1.5 rounded-xl transition-all ${
                  activeTab === 'chat'
                    ? 'glass-tab-active text-sage-800'
                    : 'text-sage-400 hover:text-sage-700'
                }`}
              >
                💬 Chat
              </button>
              <button
                type="button"
                onClick={() => {
                  handleTabChange('dashboard')
                  setMobileSidebarOpen(false)
                }}
                className={`flex-1 text-[11px] font-medium py-1.5 rounded-xl transition-all ${
                  activeTab === 'dashboard'
                    ? 'glass-tab-active text-sage-800'
                    : 'text-sage-400 hover:text-sage-700'
                }`}
              >
                📊 Mood
              </button>
              <button
                type="button"
                onClick={() => {
                  handleTabChange('resources')
                  setMobileSidebarOpen(false)
                }}
                className={`flex-1 text-[11px] font-medium py-1.5 rounded-xl transition-all ${
                  activeTab === 'resources'
                    ? 'glass-tab-active text-sage-800'
                    : 'text-sage-400 hover:text-sage-700'
                }`}
              >
                🌿 Relief
              </button>
            </div>
          </div>

          {/* Scrollable Sidebar Content */}
          <div className="flex-1 overflow-y-auto px-4 py-2 space-y-4">
            
            {/* Mood Check-In Widget */}
            <div
              className="p-3.5 rounded-2xl"
              style={{
                background: 'rgba(255,255,255,0.7)',
                border: '1px solid rgba(90,127,90,0.12)',
                boxShadow: '0 2px 10px rgba(90,127,90,0.04)',
              }}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-sage-700">How do you feel?</span>
                {selectedMood && (
                  <span className="text-[10px] text-sage-500 font-medium">Logged</span>
                )}
              </div>
              <div className="grid grid-cols-5 gap-1">
                {MOODS.map((mood) => (
                  <button
                    key={mood.value}
                    type="button"
                    onClick={() => {
                      void handleMoodSubmit(mood.value)
                    }}
                    className={`flex flex-col items-center justify-center p-1.5 rounded-xl transition-all ${
                      selectedMood === mood.value
                        ? 'bg-white shadow-sm ring-1 ring-sage-500/30 scale-105'
                        : 'hover:bg-white/50'
                    }`}
                    title={mood.label}
                  >
                    <span className="text-base">{mood.emoji}</span>
                    <span className="text-[9px] text-sage-600 truncate mt-0.5">{mood.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Quick Grounding Tools */}
            <div
              className="p-3.5 rounded-2xl"
              style={{
                background: 'rgba(255,255,255,0.7)',
                border: '1px solid rgba(90,127,90,0.12)',
              }}
            >
              <p className="text-xs font-semibold text-sage-700 mb-2">Quick Grounding Tools</p>
              <div className="space-y-1.5">
                {[
                  { name: '🌬️ Box Breathing (4-4-4-4)', query: 'Breathing exercise' },
                  { name: '✋ 5-4-3-2-1 Sensory Grounding', query: 'Grounding technique' },
                  { name: '🧘 Mindful Minute', query: 'Meditation' },
                  { name: '💡 Practical Coping Strategies', query: 'Coping strategies' },
                ].map((tool) => (
                  <button
                    key={tool.name}
                    type="button"
                    onClick={() => {
                      if (activeTab !== 'chat') handleTabChange('chat')
                      void sendMessage(tool.query)
                      setMobileSidebarOpen(false)
                    }}
                    className="w-full text-left text-[11px] font-medium text-sage-700 hover:text-sage-900 py-1.5 px-2.5 rounded-xl hover:bg-white/80 transition-all flex items-center justify-between group"
                  >
                    <span>{tool.name}</span>
                    <span className="text-sage-400 group-hover:translate-x-0.5 transition-transform">→</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Emergency Contacts Card */}
            <div
              className="p-3 rounded-2xl"
              style={{
                background: 'rgba(196,122,122,0.08)',
                border: '1px solid rgba(196,122,122,0.22)',
              }}
            >
              <p className="text-[11px] font-semibold text-[#7a2e2e] mb-1">Emergency Support 24/7</p>
              <p className="text-[10px] text-[#5f2020] leading-snug">
                Tele-MANAS (India): <strong className="font-semibold">14416</strong><br />
                National Emergency: <strong className="font-semibold">112</strong>
              </p>
            </div>

          </div>

          {/* Sidebar Footer */}
          <div className="p-4 border-t border-sage-900/10 flex items-center justify-between text-[11px] text-sage-500">
            <button
              type="button"
              onClick={() => setShowPrivacy(true)}
              className="flex items-center gap-1.5 hover:text-sage-800 transition-colors"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 3l7 3v5c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z" />
              </svg>
              Privacy & Data
            </button>
            <span className="text-[10px] text-sage-400">llama3.2:3b</span>
          </div>
        </aside>

        {/* ── RIGHT MAIN WORKSPACE CANVAS ── */}
        <main className="flex-1 flex flex-col h-full min-w-0 overflow-hidden relative">
          
          {/* Desktop Top Navbar */}
          <header
            className="h-14 px-4 md:px-8 flex items-center justify-between flex-shrink-0 z-10"
            style={{
              background: 'rgba(255,255,255,0.7)',
              backdropFilter: 'blur(20px)',
              borderBottom: '1px solid rgba(90,127,90,0.1)',
            }}
          >
            {/* Left: Mobile hamburger & title */}
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setMobileSidebarOpen(!mobileSidebarOpen)}
                className="md:hidden w-8 h-8 rounded-xl flex items-center justify-center text-sage-700 hover:bg-sage-100 transition-colors"
                aria-label="Toggle navigation menu"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="3" y1="12" x2="21" y2="12"></line>
                  <line x1="3" y1="6" x2="21" y2="6"></line>
                  <line x1="3" y1="18" x2="21" y2="18"></line>
                </svg>
              </button>
              
              <div>
                <h2
                  className="text-sage-800 text-sm font-semibold tracking-tight"
                  style={{ fontFamily: 'var(--font-display)' }}
                >
                  {activeTab === 'chat'
                    ? 'Conversation Workspace'
                    : activeTab === 'dashboard'
                      ? 'Mood & Wellbeing Analytics'
                      : 'Self-Care & Resources'}
                </h2>
              </div>
            </div>

            {/* Right: Actions */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => handleTabChange('resources')}
                className="px-3 py-1 rounded-full text-xs font-semibold text-[#7a2e2e] hover:bg-[#c47a7a15] transition-colors"
                style={{ border: '1px solid rgba(196,122,122,0.3)' }}
              >
                Helplines
              </button>

              <button
                type="button"
                onClick={() => setShowLanding(true)}
                className="px-3 py-1 rounded-full text-xs font-medium text-sage-700 hover:bg-white/80 transition-colors"
                style={glass.pill}
              >
                Home
              </button>

              {consentGranted && (
                <button
                  type="button"
                  onClick={() => setShowPrivacy(true)}
                  className="w-8 h-8 rounded-full flex items-center justify-center text-sage-600 hover:text-sage-800 hover:bg-white/80 transition-colors"
                  style={glass.pill}
                  title="Privacy controls"
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 3l7 3v5c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z" />
                  </svg>
                </button>
              )}
            </div>
          </header>

          {/* Offline Warning Banner */}
          {isOffline && (
            <div
              role="status"
              className="px-6 py-2 bg-amber-500/10 border-b border-amber-500/20 text-xs text-amber-800 flex items-center justify-between"
            >
              <span>⚠️ Offline mode active. Replies are limited. Crisis support is still accessible.</span>
              <button
                type="button"
                onClick={() => handleTabChange('resources')}
                className="font-semibold underline ml-2"
              >
                View Helplines
              </button>
            </div>
          )}

          {/* ── TAB CONTENT: CHAT ── */}
          {activeTab === 'chat' && (
            <div className="flex-1 flex flex-col min-h-0 relative">
              
              {/* Messages Viewport */}
              <div
                className="flex-1 overflow-y-auto px-4 md:px-8 py-6"
                role="log"
                aria-label="Conversation"
              >
                <div className="max-w-3xl xl:max-w-4xl mx-auto w-full space-y-4">
                  
                  {/* Empty state / Welcome Hero Banner if conversation is fresh */}
                  {messages.length <= 1 && (
                    <div
                      className="p-6 md:p-8 rounded-3xl text-center mb-6"
                      style={{
                        background: '#ffffff',
                        border: '1px solid rgba(90,127,90,0.18)',
                        boxShadow: '0 8px 30px rgba(90,127,90,0.06)',
                      }}
                    >
                      <h3
                        className="text-sage-800 text-xl font-normal mb-2"
                        style={{ fontFamily: 'var(--font-display)' }}
                      >
                        Welcome to your quiet space 🌿
                      </h3>
                      <p className="text-sage-600 text-xs md:text-sm max-w-lg mx-auto mb-6 leading-relaxed">
                        I'm TOM, your local companion. Everything you say stays completely on this machine. Pick a starter or type freely below:
                      </p>

                      {/* 4 Interactive Starter Prompt Cards */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-left max-w-xl mx-auto">
                        {[
                          { title: '😰 Exam & College Stress', prompt: "I am feeling really stressed about my upcoming semester exams." },
                          { title: '🌬️ Guided Breathing', prompt: "Can you guide me through a calming breathing exercise?" },
                          { title: '😟 Family Expectations', prompt: "I feel overwhelmed by family pressure and career expectations." },
                          { title: '💬 Just Need to Talk', prompt: "I've been feeling low and alone lately, just need someone to talk to." },
                        ].map((card) => (
                          <button
                            key={card.title}
                            type="button"
                            onClick={() => void sendMessage(card.prompt)}
                            disabled={isSending}
                            className="starter-card p-3.5 rounded-2xl text-left shadow-xs"
                            style={{
                              background: '#ffffff',
                              border: '1.5px solid rgba(90,127,90,0.22)',
                              boxShadow: '0 2px 8px rgba(90,127,90,0.06)',
                            }}
                          >
                            <p className="text-xs font-semibold text-sage-800 mb-1">{card.title}</p>
                            <p className="text-[11px] text-sage-500 line-clamp-2 leading-snug">{card.prompt}</p>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Message Stream */}
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
              </div>

              {/* Floating Bottom Composer Bar */}
              <div
                className="px-4 md:px-8 pb-4 pt-2 flex-shrink-0"
                style={{
                  background: 'linear-gradient(to top, #ffffff 80%, rgba(255,255,255,0) 100%)',
                }}
              >
                <div className="max-w-3xl xl:max-w-4xl mx-auto w-full">
                  
                  {/* Suggestion Chips - Solid White */}
                  <div className="flex gap-2 overflow-x-auto pb-2 mb-1 scrollbar-none">
                    {SUGGESTIONS.map((suggestion) => (
                      <button
                        key={suggestion}
                        type="button"
                        onClick={() => void sendMessage(suggestion)}
                        disabled={isSending}
                        className="text-[11px] text-sage-800 rounded-full px-3.5 py-1.5 whitespace-nowrap flex-shrink-0 suggestion-chip font-medium disabled:opacity-40"
                        style={{
                          backgroundColor: '#ffffff',
                          background: '#ffffff',
                          border: '1.5px solid rgba(90,127,90,0.28)',
                          boxShadow: '0 2px 10px rgba(90,127,90,0.12), 0 1px 0 rgba(255,255,255,1) inset',
                          color: '#384f38',
                          opacity: 1,
                        }}
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>

                  {/* Input Box */}
                  <div
                    className="flex items-end gap-3 rounded-2xl md:rounded-3xl px-4 py-2"
                    style={{
                      background: 'rgba(255,255,255,0.95)',
                      backdropFilter: 'blur(24px) saturate(2)',
                      border: '1px solid rgba(90,127,90,0.22)',
                      boxShadow: '0 8px 30px rgba(90,127,90,0.08), 0 1px 0 rgba(255,255,255,1) inset',
                    }}
                  >
                    <textarea
                      ref={inputRef}
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="Share what's on your mind…"
                      rows={1}
                      maxLength={MAX_MESSAGE_LENGTH}
                      enterKeyHint="send"
                      aria-label="Message TOM"
                      className="flex-1 bg-transparent text-sm text-sage-800 placeholder:text-sage-400 resize-none outline-none focus:outline-none focus:ring-0 leading-normal max-h-48 overflow-y-auto py-2 m-0"
                      style={{
                        minHeight: '36px',
                        outline: 'none',
                        boxShadow: 'none',
                        border: 'none',
                      }}
                    />

                    <button
                      type="button"
                      onClick={() => void sendMessage(input)}
                      disabled={!input.trim() || isSending}
                      aria-label="Send message"
                      className="w-9 h-9 rounded-xl md:rounded-2xl flex items-center justify-center flex-shrink-0 ios-press disabled:opacity-30 disabled:cursor-not-allowed transition-all self-end"
                      style={{
                        background: input.trim()
                          ? 'linear-gradient(145deg, rgba(90,127,90,0.95) 0%, rgba(60,95,60,1) 100%)'
                          : 'rgba(90,127,90,0.2)',
                        color: '#fff',
                        boxShadow: input.trim() ? '0 3px 12px rgba(70,100,70,0.3)' : 'none',
                      }}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M22 2L11 13" />
                        <path d="M22 2L15 22 11 13 2 9l20-7z" />
                      </svg>
                    </button>
                  </div>

                  {/* Bottom Note */}
                  <p className="text-[10px] text-sage-400 text-center mt-2">
                    TOM is an offline AI companion · Data stays strictly on your computer · Tele-MANAS: 14416
                  </p>
                </div>
              </div>

            </div>
          )}

          {/* ── TAB CONTENT: MOOD DASHBOARD ── */}
          {activeTab === 'dashboard' && (
            <MoodDashboard
              onNavigateChat={(prompt) => {
                setActiveTab('chat')
                if (prompt) void sendMessage(prompt)
              }}
            />
          )}

          {/* ── TAB CONTENT: RESOURCES ── */}
          {activeTab === 'resources' && (
            <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6">
              <div className="max-w-3xl xl:max-w-4xl mx-auto w-full space-y-6">
                
                <CrisisResources
                  region={region}
                  onRegionChange={handleRegionChange}
                />

                <div>
                  <h3
                    className="text-sage-800 text-xl font-normal mb-3"
                    style={{ fontFamily: 'var(--font-display)' }}
                  >
                    Self-Care & Grounding Resources
                  </h3>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {SUPPORT_RESOURCES.map((resource, index) => (
                      <ResourceCard
                        key={resource.title}
                        resource={resource}
                        index={index}
                      />
                    ))}
                  </div>
                </div>

                <div
                  className="p-4 rounded-2xl text-xs text-mist-700 leading-relaxed"
                  style={{
                    background: 'rgba(61,122,142,0.06)',
                    border: '1px solid rgba(61,122,142,0.15)',
                  }}
                >
                  <strong>A note of care:</strong> TOM is an AI companion for emotional support and reflection, not a licensed medical professional or crisis intervention service. If you are experiencing an emergency, please reach out to emergency helplines immediately.
                </div>

              </div>
            </div>
          )}

        </main>
      </div>

      {overlays}
    </>
  )
}
