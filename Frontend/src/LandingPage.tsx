import { useState } from 'react'
import tomLogo from '@/imports/TOM_Bot.png'

// Glass style helpers (reusing from App.tsx)
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

interface LandingPageProps {
  onStartChat: () => void
}

export default function LandingPage({ onStartChat }: LandingPageProps) {
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
      className="min-h-screen flex flex-col items-center justify-center p-4"
      style={{
        backgroundColor: '#ffffff',
        backgroundImage:
          'linear-gradient(rgba(90,127,90,0.07) 1px, transparent 1px), linear-gradient(90deg, rgba(90,127,90,0.07) 1px, transparent 1px)',
        backgroundSize: '32px 32px',
      }}
    >
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(20px) scale(0.98); }
          to   { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(30px); }
          to   { opacity: 1; transform: translateY(0); }
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
      `}</style>

      {/* App shell - liquid glass card */}
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
                className="w-11 h-11 rounded-2xl flex items-center justify-center overflow-hidden"
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
        </div>

        {/* Landing Content */}
        <div
          className="flex-1 flex flex-col items-center justify-center px-6 py-8"
          style={{
            animation: 'slideUp 0.5s cubic-bezier(0.34,1.56,0.64,1) 0.2s both',
          }}
        >
          <div className="text-center mb-8">
            <h2
              className="text-2xl font-bold text-sage-800 mb-4"
              style={{ fontFamily: 'var(--font-display)', letterSpacing: '-0.01em' }}
            >
              Welcome to TOM
            </h2>
            <p className="text-sage-600 text-lg leading-relaxed">
              Your mental health companion is here.
              <br />
              A safe, judgment-free space to express yourself.
            </p>
          </div>

          {/* Feature Highlights */}
          <div className="grid grid-cols-2 gap-4 w-full max-w-sm mb-8">
            <div
              className="p-4 rounded-2xl text-center"
              style={glass.base}
            >
              <div className="text-2xl mb-2">💬</div>
              <p className="text-sm font-medium text-sage-700">Natural Conversations</p>
              <p className="text-xs text-sage-500 mt-1">Talk freely about your feelings</p>
            </div>
            <div
              className="p-4 rounded-2xl text-center"
              style={glass.base}
            >
              <div className="text-2xl mb-2">🧠</div>
              <p className="text-sm font-medium text-sage-700">Context Memory</p>
              <p className="text-xs text-sage-500 mt-1">Remembers conversation history</p>
            </div>
            <div
              className="p-4 rounded-2xl text-center"
              style={glass.base}
            >
              <div className="text-2xl mb-2">😊</div>
              <p className="text-sm font-medium text-sage-700">Mood Tracking</p>
              <p className="text-xs text-sage-500 mt-1">Select your emotional state</p>
            </div>
            <div
              className="p-4 rounded-2xl text-center"
              style={glass.base}
            >
              <div className="text-2xl mb-2">🛡️</div>
              <p className="text-sm font-medium text-sage-700">Safe & Private</p>
              <p className="text-xs text-sage-500 mt-1">Your conversations stay private</p>
            </div>
          </div>

          {/* Start Button */}
          <button
            onClick={handleStart}
            disabled={isLoading}
            className="w-full max-w-sm py-3 rounded-3xl text-base font-semibold text-white transition-all duration-300 disabled:opacity-70"
            style={{
              background: 'linear-gradient(145deg, rgba(90,127,90,0.9) 0%, rgba(70,100,70,0.95) 100%)',
              border: '1px solid rgba(120,160,120,0.4)',
              boxShadow: '0 6px 20px rgba(70,100,70,0.28), 0 1px 0 rgba(160,200,160,0.4) inset',
            }}
          >
            {isLoading ? 'Starting...' : 'Start Chat'}
          </button>

          <p className="text-[10px] text-sage-400 mt-4 tracking-wide">
            Not a substitute for professional help
          </p>
        </div>

        {/* Footer in card */}
        <div className="px-6 pb-4 flex-shrink-0">
          <p className="text-[10px] text-sage-300/80 text-center">
            Built with care for mental wellbeing
          </p>
        </div>
      </div>
    </div>
  )
}
