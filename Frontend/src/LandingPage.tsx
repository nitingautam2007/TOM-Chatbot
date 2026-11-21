import { useState } from 'react'
import tomLogo from '@/imports/TOM_Bot.png'

const glass = {
  base: {
    background: 'linear-gradient(145deg, rgba(255,255,255,0.68) 0%, rgba(255,255,255,0.42) 100%)',
    backdropFilter: 'blur(24px) saturate(1.9)',
    WebkitBackdropFilter: 'blur(24px) saturate(1.9)',
    border: '1px solid rgba(255,255,255,0.8)',
    boxShadow: '0 8px 32px rgba(90,127,90,0.10), 0 1.5px 0 rgba(255,255,255,0.95) inset',
  } as React.CSSProperties,
}

interface LandingPageProps {
  onStartChat: () => void
  onGetHelp: () => void
}

export default function LandingPage({ onStartChat, onGetHelp }: LandingPageProps) {
  const [isLoading, setIsLoading] = useState(false)

  const handleStart = () => {
    setIsLoading(true)
    setTimeout(() => {
      onStartChat()
      setIsLoading(false)
    }, 500)
  }

  return (
    <div
      className="tom-screen flex flex-col items-center justify-center"
      style={{
        backgroundColor: '#ffffff',
        backgroundImage:
          'linear-gradient(rgba(90,127,90,0.07) 1px, transparent 1px), linear-gradient(90deg, rgba(90,127,90,0.07) 1px, transparent 1px)',
        backgroundSize: '32px 32px',
        minHeight: '100vh',
      }}
    >
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(24px) scale(0.98); }
          to   { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-6px); }
        }
        .avatar-float { animation: float 4s ease-in-out infinite; }
        .fade-in { animation: fadeIn 0.6s cubic-bezier(0.34,1.56,0.64,1) both; }
        .fade-in-1 { animation: fadeIn 0.6s cubic-bezier(0.34,1.56,0.64,1) 0.1s both; }
        .fade-in-2 { animation: fadeIn 0.6s cubic-bezier(0.34,1.56,0.64,1) 0.2s both; }
        .fade-in-3 { animation: fadeIn 0.6s cubic-bezier(0.34,1.56,0.64,1) 0.3s both; }
        .fade-in-4 { animation: fadeIn 0.6s cubic-bezier(0.34,1.56,0.64,1) 0.4s both; }
        .btn-main:hover { transform: translateY(-2px); box-shadow: 0 12px 32px rgba(70,100,70,0.35), 0 1px 0 rgba(160,200,160,0.4) inset !important; }
        .btn-main:active { transform: translateY(0px); }
        .btn-main { transition: all 0.2s ease; }
      `}</style>

      <div
        className="w-full max-w-sm mx-4 rounded-[2.5rem] overflow-hidden flex flex-col"
        style={{
          background: 'rgba(255,255,255,0.75)',
          backdropFilter: 'blur(32px) saturate(2)',
          WebkitBackdropFilter: 'blur(32px) saturate(2)',
          border: '1px solid rgba(255,255,255,0.9)',
          boxShadow: '0 32px 80px rgba(60,90,60,0.12), 0 2px 0 rgba(255,255,255,1) inset',
        }}
      >
        {/* Top bar */}
        <div
          className="px-5 pt-5 pb-3 flex items-center justify-between flex-shrink-0"
          style={{ borderBottom: '1px solid rgba(90,127,90,0.08)' }}
        >
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-2xl flex items-center justify-center overflow-hidden"
              style={{ background: '#0d0d12' }}
            >
              <img src={tomLogo} alt="TOM" className="w-full h-full object-contain" />
            </div>
            <div>
              <p className="text-sage-800 font-semibold text-sm leading-tight">TOM</p>
              <p className="text-[10px] text-sage-400 tracking-wide">Talk to Me</p>
            </div>
          </div>
          {/* Local badge */}
          <div
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-semibold"
            style={{
              background: 'rgba(90,127,90,0.1)',
              border: '1px solid rgba(90,127,90,0.2)',
              color: '#466446',
            }}
          >
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#5a7f5a', display: 'inline-block', boxShadow: '0 0 6px #5a7f5a' }} />
            100% Local
          </div>
        </div>

        {/* Hero Section */}
        <div className="flex flex-col items-center px-6 pt-8 pb-6">

          {/* Avatar */}
          <div className="avatar-float mb-6 fade-in">
            <div
              className="w-24 h-24 rounded-[2rem] flex items-center justify-center overflow-hidden"
              style={{
                background: 'linear-gradient(135deg, #2e3f2e 0%, #0d0d12 100%)',
                boxShadow: '0 16px 48px rgba(46,63,46,0.25), 0 2px 0 rgba(255,255,255,0.1) inset',
              }}
            >
              <img src={tomLogo} alt="TOM" className="w-full h-full object-contain p-2" />
            </div>
          </div>

          {/* Headline */}
          <div className="text-center mb-6 fade-in-1">
            <h1
              className="text-sage-800 mb-2 leading-tight"
              style={{ fontFamily: 'var(--font-display)', fontSize: '28px', fontWeight: 400, letterSpacing: '-0.02em' }}
            >
              Hey, I'm TOM 👋
            </h1>
            <p className="text-sage-600 text-sm leading-relaxed">
              Your private, offline-first companion.<br />
              Talk about anything — in <span style={{ fontWeight: 600 }}>English or Hinglish</span>.
            </p>
          </div>

          {/* Feature pills - Symmetric 2x2 Grid */}
          <div className="grid grid-cols-2 gap-2.5 w-full mb-6 fade-in-2">
            {[
              { emoji: '🤫', label: '100% On-Device' },
              { emoji: '🦙', label: 'Ollama Engine' },
              { emoji: '💬', label: 'English & Hinglish' },
              { emoji: '🛡️', label: 'Zero Data Shared' },
            ].map(({ emoji, label }) => (
              <div
                key={label}
                className="flex items-center justify-center gap-2 py-2 px-3 rounded-full text-xs font-medium text-sage-700 text-center"
                style={glass.base}
              >
                <span className="text-sm">{emoji}</span>
                <span className="whitespace-nowrap">{label}</span>
              </div>
            ))}
          </div>

          {/* What can I help with */}
          <div
            className="w-full rounded-2xl p-4 mb-6 fade-in-3"
            style={{
              background: 'rgba(90,127,90,0.06)',
              border: '1px solid rgba(90,127,90,0.14)',
            }}
          >
            <p className="text-xs font-semibold text-sage-700 mb-2.5 uppercase tracking-wider">I can help with</p>
            <div className="grid grid-cols-2 gap-1.5">
              {[
                '😰 Exam stress',
                '😔 Sadness & low mood',
                '😟 Family pressure',
                '😰 Anxiety & worry',
                '😶 Loneliness',
                '🧘 Coping strategies',
              ].map((item) => (
                <p key={item} className="text-xs text-sage-600 flex items-center gap-1.5">{item}</p>
              ))}
            </div>
          </div>

          {/* Disclaimer */}
          <p
            className="text-center text-[10px] leading-relaxed text-sage-500 mb-5 px-2 fade-in-3"
          >
            <strong className="text-sage-600">TOM is an AI companion</strong>, not a therapist or doctor.
            If you're in danger, call <strong>112</strong> or <strong>Tele-MANAS: 14416</strong>.
          </p>

          {/* CTA Buttons */}
          <div className="w-full flex flex-col gap-2 fade-in-4">
            <button
              onClick={handleStart}
              disabled={isLoading}
              className="btn-main w-full py-3 rounded-2xl text-sm font-semibold text-white disabled:opacity-70"
              style={{
                background: 'linear-gradient(145deg, rgba(90,127,90,0.95) 0%, rgba(60,90,60,1) 100%)',
                border: '1px solid rgba(120,160,120,0.3)',
                boxShadow: '0 8px 24px rgba(70,100,70,0.3), 0 1px 0 rgba(160,200,160,0.4) inset',
              }}
            >
              {isLoading ? '✨ Starting...' : '💬 Start Chatting'}
            </button>

            <button
              onClick={onGetHelp}
              className="w-full py-2.5 rounded-2xl text-xs font-semibold transition-all duration-200"
              style={{
                background: 'rgba(196,122,122,0.10)',
                border: '1px solid rgba(196,122,122,0.25)',
                color: '#7a2e2e',
              }}
            >
              🆘 Get crisis support & helplines
            </button>
          </div>
        </div>

        {/* Footer */}
        <div
          className="px-6 py-3 text-center flex-shrink-0"
          style={{ borderTop: '1px solid rgba(90,127,90,0.08)' }}
        >
          <p className="text-[10px] text-sage-300">
            Available 24/7 · Runs locally · Not an emergency service
          </p>
        </div>
      </div>
    </div>
  )
}
