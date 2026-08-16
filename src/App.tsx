import { useState, useRef, useEffect, useCallback } from 'react'
import tomLogo from '@/imports/TOM_Bot.png'

type Mood = 1 | 2 | 3 | 4 | 5

interface Message {
  id: string
  role: 'user' | 'assistant'
  text: string
  timestamp: Date
  visible: boolean
}

const MOODS: { value: Mood; emoji: string; label: string; color: string }[] = [
  { value: 1, emoji: '😔', label: 'Struggling', color: '#c47a7a' },
  { value: 2, emoji: '😕', label: 'Low', color: '#c49b5a' },
  { value: 3, emoji: '😐', label: 'Okay', color: '#8ab5c2' },
  { value: 4, emoji: '🙂', label: 'Good', color: '#7d9e7d' },
  { value: 5, emoji: '😊', label: 'Great', color: '#5a7f5a' },
]

const SUGGESTIONS = [
  "I'm feeling anxious",
  "I need to talk",
  "Breathing exercise",
  "Trouble sleeping",
  "Grounding technique",
]

const BOT_RESPONSES: Record<string, string[]> = {
  default: [
    "I hear you. Would you like to tell me more about what's on your mind?",
    "Thank you for sharing that with me. You're not alone in feeling this way.",
    "It takes courage to reach out. How long have you been feeling this way?",
    "I'm here with you. Let's take this one step at a time.",
  ],
  anxious: [
    "Anxiety can feel overwhelming, but you're doing the right thing by acknowledging it. Let's try a simple breathing exercise: breathe in for 4 counts, hold for 4, breathe out for 6. How does that feel?",
    "When anxiety comes, it helps to ground yourself. Can you name 5 things you can see around you right now?",
  ],
  breathing: [
    "Let's do a calming box breath together:\n\n• Breathe in slowly for 4 counts\n• Hold for 4 counts\n• Breathe out for 4 counts\n• Hold for 4 counts\n\nRepeat this 4 times. Take your time — I'm right here with you. 💬",
  ],
  sleep: [
    "Sleep difficulties are so common, and they can make everything feel harder. A few things that often help: keeping a consistent bedtime, avoiding screens 30 minutes before bed, and a short body-scan meditation. Would you like me to guide you through one?",
  ],
  grounding: [
    "A gentle grounding technique: the 5-4-3-2-1 method.\n\n• 5 things you can see\n• 4 things you can physically feel\n• 3 things you can hear\n• 2 things you can smell\n• 1 thing you can taste\n\nThis brings your attention back to the present moment. 🌱",
  ],
  talk: [
    "I'm here and I'm listening. This is a safe space — there's no right or wrong way to feel. What would you like to share?",
  ],
}

function getBotResponse(input: string): string {
  const lower = input.toLowerCase()
  if (lower.includes('anxi') || lower.includes('panic') || lower.includes('worry'))
    return BOT_RESPONSES.anxious[Math.floor(Math.random() * BOT_RESPONSES.anxious.length)]
  if (lower.includes('breath')) return BOT_RESPONSES.breathing[0]
  if (lower.includes('sleep') || lower.includes('insomnia')) return BOT_RESPONSES.sleep[0]
  if (lower.includes('ground')) return BOT_RESPONSES.grounding[0]
  if (lower.includes('talk') || lower.includes('listen') || lower.includes('someone'))
    return BOT_RESPONSES.talk[0]
  return BOT_RESPONSES.default[Math.floor(Math.random() * BOT_RESPONSES.default.length)]
}

// Glass style helpers
const glass = {
  base: {
    background: 'linear-gradient(145deg, rgba(255,255,255,0.68) 0%, rgba(255,255,255,0.42) 100%)',
    backdropFilter: 'blur(24px) saturate(1.9)',
    WebkitBackdropFilter: 'blur(24px) saturate(1.9)',
    border: '1px solid rgba(255,255,255,0.8)',
    boxShadow: '0 8px 32px rgba(90,127,90,0.10), 0 1.5px 0 rgba(255,255,255,0.95) inset, 0 -1px 0 rgba(90,127,90,0.05) inset',
  } as React.CSSProperties,
  strong: {
    background: 'linear-gradient(145deg, rgba(255,255,255,0.82) 0%, rgba(255,255,255,0.56) 100%)',
    backdropFilter: 'blur(32px) saturate(2)',
    WebkitBackdropFilter: 'blur(32px) saturate(2)',
    border: '1px solid rgba(255,255,255,0.9)',
    boxShadow: '0 16px 48px rgba(90,127,90,0.12), 0 2px 0 rgba(255,255,255,1) inset, 0 -1px 0 rgba(90,127,90,0.06) inset',
  } as React.CSSProperties,
  pill: {
    background: 'linear-gradient(145deg, rgba(255,255,255,0.60) 0%, rgba(255,255,255,0.32) 100%)',
    backdropFilter: 'blur(16px) saturate(1.6)',
    WebkitBackdropFilter: 'blur(16px) saturate(1.6)',
    border: '1px solid rgba(255,255,255,0.72)',
    boxShadow: '0 2px 8px rgba(90,127,90,0.07), 0 1px 0 rgba(255,255,255,0.9) inset',
  } as React.CSSProperties,
}

function TypingIndicator() {
  return (
    <div
      className="flex items-end gap-2 mb-4"
      style={{ animation: 'slideUp 0.32s cubic-bezier(0.34,1.56,0.64,1) both' }}
    >
      <div
        className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 overflow-hidden"
        style={{ background: '#0d0d12', ...glass.pill }}
      >
        <img src={tomLogo} alt="TOM" className="w-full h-full object-contain" />
      </div>
      <div className="px-4 py-3 rounded-2xl rounded-bl-sm" style={glass.base}>
        <div className="flex gap-1.5 items-center h-4">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="w-1.5 h-1.5 rounded-full bg-sage-400 inline-block"
              style={{ animation: `typingBounce 1.1s ease-in-out infinite`, animationDelay: `${i * 0.18}s` }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === 'user'
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
        className={`max-w-[76%] px-4 py-3 text-sm leading-relaxed whitespace-pre-line ${
          isUser ? 'rounded-3xl rounded-br-md' : 'rounded-3xl rounded-bl-md'
        }`}
        style={
          isUser
            ? {
                background: 'linear-gradient(145deg, rgba(90,127,90,0.88) 0%, rgba(70,100,70,0.92) 100%)',
                backdropFilter: 'blur(20px) saturate(1.6)',
                WebkitBackdropFilter: 'blur(20px) saturate(1.6)',
                border: '1px solid rgba(120,160,120,0.5)',
                boxShadow: '0 4px 16px rgba(70,100,70,0.22), 0 1px 0 rgba(160,200,160,0.4) inset',
                color: '#ffffff',
              }
            : glass.base
        }
      >
        <span className={isUser ? 'text-white' : 'text-sage-800'}>{message.text}</span>
        <div className={`text-[10px] mt-1.5 ${isUser ? 'text-sage-200/80' : 'text-sage-400'}`}>
          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </div>
  )
}

export default function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '0',
      role: 'assistant',
      text: "Hi, I'm TOM — Talk to Me. 💬\n\nThis is a safe, judgment-free space. I'm here to listen whenever you need it. How are you feeling today?",
      timestamp: new Date(),
      visible: true,
    },
  ])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [selectedMood, setSelectedMood] = useState<Mood | null>(null)
  const [moodSubmitted, setMoodSubmitted] = useState(false)
  const [activeTab, setActiveTab] = useState<'chat' | 'resources'>('chat')
  const [pressedBtn, setPressedBtn] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  useEffect(() => {
    if (activeTab === 'chat') {
      bottomRef.current?.scrollIntoView({ behavior: 'instant' })
    }
  }, [activeTab])

  const sendMessage = useCallback((text: string) => {
    if (!text.trim()) return
    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      text: text.trim(),
      timestamp: new Date(),
      visible: true,
    }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setIsTyping(true)
    setTimeout(() => {
      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        text: getBotResponse(text),
        timestamp: new Date(),
        visible: true,
      }
      setMessages((prev) => [...prev, botMsg])
      setIsTyping(false)
    }, 900 + Math.random() * 600)
  }, [])

  const handleMoodSubmit = () => {
    if (!selectedMood) return
    const mood = MOODS.find((m) => m.value === selectedMood)!
    setMoodSubmitted(true)
    sendMessage(`I'm feeling ${mood.label.toLowerCase()} today (${mood.emoji})`)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center p-4"
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
        className="w-full max-w-md rounded-[2.5rem] overflow-hidden flex flex-col"
        style={{
          height: '90vh',
          maxHeight: '780px',
          background: 'rgba(255,255,255,0.12)',
          backdropFilter: 'blur(12px) saturate(1.4)',
          WebkitBackdropFilter: 'blur(12px) saturate(1.4)',
          border: '1px solid rgba(255,255,255,0.45)',
          boxShadow: '0 24px 60px rgba(60,90,60,0.08), 0 1.5px 0 rgba(255,255,255,0.7) inset',
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
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div
                className="w-11 h-11 rounded-2xl flex items-center justify-center overflow-hidden ios-press"
                style={{ background: '#0d0d12', ...glass.base }}
              >
                <img src={tomLogo} alt="TOM logo" className="w-full h-full object-contain" />
              </div>
              <div>
                <h1
                  className="text-sage-800 leading-tight"
                  style={{ fontFamily: 'var(--font-display)', fontSize: '19px', fontWeight: 400, letterSpacing: '-0.01em' }}
                >
                  TOM
                </h1>
                <p className="text-[11px] text-sage-400 font-light tracking-wide">Talk to Me · Wellbeing companion</p>
              </div>
            </div>
            <div
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-full"
              style={glass.pill}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-sage-400 inline-block" style={{ boxShadow: '0 0 4px rgba(90,127,90,0.6)' }} />
              <span className="text-[10px] text-sage-500 font-medium">Online</span>
            </div>
          </div>

          {/* Tabs */}
          <div
            className="flex gap-1 p-1 rounded-2xl"
            style={{
              background: 'rgba(90,127,90,0.06)',
              border: '1px solid rgba(90,127,90,0.08)',
            }}
          >
            {(['chat', 'resources'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex-1 text-xs font-medium py-1.5 rounded-xl capitalize transition-all duration-250 ios-press ${
                  activeTab === tab ? 'glass-tab-active text-sage-700' : 'glass-tab-inactive text-sage-400 hover:text-sage-600'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        {/* Chat tab */}
        {activeTab === 'chat' && (
          <>
            {/* Mood check-in */}
            {!moodSubmitted && (
              <div
                className="mx-4 mt-4 p-4 rounded-3xl flex-shrink-0"
                style={{
                  ...glass.base,
                  animation: 'slideUp 0.4s cubic-bezier(0.34,1.56,0.64,1) 0.1s both',
                }}
              >
                <p className="text-xs font-medium text-sage-600 mb-3 tracking-wide">How are you feeling right now?</p>
                <div className="flex justify-between mb-3">
                  {MOODS.map((m) => (
                    <button
                      key={m.value}
                      onClick={() => setSelectedMood(m.value)}
                      className="flex flex-col items-center gap-1 p-2 rounded-2xl ios-press"
                      style={
                        selectedMood === m.value
                          ? {
                              background: 'rgba(255,255,255,0.9)',
                              boxShadow: `0 4px 16px ${m.color}30, 0 1px 0 rgba(255,255,255,1) inset`,
                              border: `1px solid ${m.color}30`,
                              transform: 'scale(1.12)',
                            }
                          : { background: 'transparent', border: '1px solid transparent' }
                      }
                    >
                      <span className="text-xl" style={{ filter: selectedMood === m.value ? 'drop-shadow(0 2px 4px rgba(0,0,0,0.15))' : 'none' }}>{m.emoji}</span>
                      <span className="text-[9px] text-sage-500 font-medium">{m.label}</span>
                    </button>
                  ))}
                </div>
                <button
                  onClick={handleMoodSubmit}
                  disabled={!selectedMood}
                  className="w-full py-2 rounded-2xl text-xs font-medium ios-press disabled:opacity-40 disabled:cursor-not-allowed"
                  style={{
                    background: selectedMood
                      ? 'linear-gradient(145deg, rgba(90,127,90,0.88) 0%, rgba(70,100,70,0.92) 100%)'
                      : 'rgba(90,127,90,0.25)',
                    color: '#fff',
                    border: '1px solid rgba(120,160,120,0.4)',
                    boxShadow: selectedMood ? '0 4px 14px rgba(70,100,70,0.22), 0 1px 0 rgba(160,200,160,0.4) inset' : 'none',
                  }}
                >
                  Share my mood
                </button>
              </div>
            )}

            {/* Messages */}
            <div
              className="flex-1 overflow-y-auto px-4 py-4 min-h-0 mx-3 my-3 rounded-3xl"
              style={{
                background: 'rgba(255,255,255,0.10)',
                backdropFilter: 'blur(8px) saturate(1.3)',
                WebkitBackdropFilter: 'blur(8px) saturate(1.3)',
                border: '1px solid rgba(255,255,255,0.38)',
                boxShadow: '0 4px 16px rgba(90,127,90,0.04), 0 1px 0 rgba(255,255,255,0.6) inset',
              }}
            >
              {messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} />
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
                <div className="suggestions-scroll flex gap-2 w-max overflow-x-auto pb-1"
                  style={{ scrollbarWidth: 'thin', scrollbarColor: 'rgba(90,127,90,0.25) rgba(90,127,90,0.06)' }}
                >
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => sendMessage(s)}
                      className="text-[11px] text-sage-600 rounded-full px-3 py-1.5 whitespace-nowrap flex-shrink-0 suggestion-chip font-medium"
                      style={glass.pill}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Input */}
            <div
              className="px-6 pb-5 pt-2 flex-shrink-0"
              style={{ borderTop: '1px solid rgba(90,127,90,0.07)' }}
            >
              <div
                className="flex items-center gap-2 rounded-3xl px-3 py-2.5"
                style={{
                  background: 'linear-gradient(145deg, rgba(255,255,255,0.72) 0%, rgba(255,255,255,0.48) 100%)',
                  backdropFilter: 'blur(24px) saturate(1.9)',
                  WebkitBackdropFilter: 'blur(24px) saturate(1.9)',
                  border: '1px solid rgba(255,255,255,0.88)',
                  boxShadow: '0 4px 20px rgba(90,127,90,0.09), 0 1.5px 0 rgba(255,255,255,0.95) inset, 0 -1px 0 rgba(90,127,90,0.05) inset',
                }}
              >
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Share what's on your mind…"
                  rows={1}
                  className="flex-1 bg-transparent text-sm text-sage-800 placeholder:text-sage-300 resize-none outline-none leading-relaxed max-h-24 overflow-y-auto"
                  style={{ minHeight: '24px', fontFamily: 'var(--font-body)' }}
                />
                <button
                  onClick={() => sendMessage(input)}
                  disabled={!input.trim()}
                  className="w-8 h-8 rounded-2xl flex items-center justify-center flex-shrink-0 ios-press disabled:opacity-35 disabled:cursor-not-allowed"
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
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M22 2L11 13" /><path d="M22 2L15 22 11 13 2 9l20-7z" />
                  </svg>
                </button>
              </div>
              <p className="text-[10px] text-sage-300/80 text-center mt-2 tracking-wide">
                Not a substitute for professional help ·{' '}
                <span className="underline cursor-pointer hover:text-sage-400 transition-colors">Crisis resources</span>
              </p>
            </div>
          </>
        )}

        {/* Resources tab */}
        {activeTab === 'resources' && (
          <div className="flex-1 overflow-y-auto px-4 py-5 space-y-2.5">
            <p
              className="text-sage-700 mb-5"
              style={{ fontFamily: 'var(--font-display)', fontSize: '20px', fontWeight: 400, letterSpacing: '-0.01em', animation: 'slideUp 0.35s cubic-bezier(0.34,1.56,0.64,1) both' }}
            >
              Support resources
            </p>

            {[
              { title: 'Crisis Text Line', desc: 'Text HOME to 741741 — free, 24/7 support.', icon: '💬', tag: 'Crisis', tagColor: '#c47a7a' },
              { title: 'Suicide & Crisis Lifeline', desc: 'Call or text 988 — available 24 hours a day.', icon: '📞', tag: 'Crisis', tagColor: '#c47a7a' },
              { title: 'Calm breathing exercise', desc: '4-7-8 breathing to ease anxiety in minutes.', icon: '🌬️', tag: 'Self-care', tagColor: '#5a7f5a' },
              { title: 'Body scan meditation', desc: 'A 10-minute practice to release tension.', icon: '🧘', tag: 'Self-care', tagColor: '#5a7f5a' },
              { title: 'Therapist finder', desc: 'Find licensed therapists in your area by specialty.', icon: '🗺️', tag: 'Professional', tagColor: '#3d7a8e' },
              { title: 'BetterHelp', desc: 'Online therapy with licensed counselors, anytime.', icon: '💻', tag: 'Professional', tagColor: '#3d7a8e' },
            ].map((r, i) => (
              <div
                key={r.title}
                className="flex items-start gap-3 p-4 rounded-2xl cursor-pointer group resource-row"
                style={{
                  ...glass.base,
                  animation: `slideUp 0.35s cubic-bezier(0.34,1.56,0.64,1) ${0.05 * i}s both`,
                }}
              >
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center text-lg flex-shrink-0"
                  style={glass.pill}
                >
                  {r.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-sm font-medium text-sage-800">{r.title}</span>
                    <span
                      className="text-[9px] font-medium px-1.5 py-0.5 rounded-full flex-shrink-0"
                      style={{ background: r.tagColor + '18', color: r.tagColor }}
                    >
                      {r.tag}
                    </span>
                  </div>
                  <p className="text-xs text-sage-400 leading-snug">{r.desc}</p>
                </div>
                <svg className="w-4 h-4 text-sage-300 flex-shrink-0 mt-0.5 group-hover:text-sage-400 transition-colors" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 18l6-6-6-6" />
                </svg>
              </div>
            ))}

            <div
              className="mt-2 p-4 rounded-2xl text-xs text-mist-600 leading-relaxed"
              style={{ background: 'rgba(61,122,142,0.06)', border: '1px solid rgba(61,122,142,0.12)' }}
            >
              <strong className="font-medium text-mist-700">A note of care.</strong> TOM is a supportive companion, not a mental health professional. If you are in crisis or danger, please reach out to a crisis line or emergency services immediately.
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
