import { useState, type CSSProperties } from 'react'
import tomLogo from '@/imports/TOM_Bot.png'

const glass = {
  base: {
    background: 'linear-gradient(145deg, rgba(255,255,255,0.68) 0%, rgba(255,255,255,0.42) 100%)',
    backdropFilter: 'blur(24px) saturate(1.9)',
    WebkitBackdropFilter: 'blur(24px) saturate(1.9)',
    border: '1px solid rgba(255,255,255,0.8)',
    boxShadow: '0 8px 32px rgba(90,127,90,0.10), 0 1.5px 0 rgba(255,255,255,0.95) inset',
  } as CSSProperties,
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
    }, 400)
  }

  return (
    <div
      className="tom-screen flex flex-col items-center justify-center p-4 md:p-8"
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
          from { opacity: 0; transform: translateY(20px) scale(0.98); }
          to   { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-8px); }
        }
        .avatar-float { animation: float 4s ease-in-out infinite; }
        .fade-in { animation: fadeIn 0.5s cubic-bezier(0.34,1.56,0.64,1) both; }
        .fade-in-1 { animation: fadeIn 0.5s cubic-bezier(0.34,1.56,0.64,1) 0.1s both; }
        .fade-in-2 { animation: fadeIn 0.5s cubic-bezier(0.34,1.56,0.64,1) 0.2s both; }
        .fade-in-3 { animation: fadeIn 0.5s cubic-bezier(0.34,1.56,0.64,1) 0.3s both; }
        .btn-main:hover { transform: translateY(-2px); box-shadow: 0 12px 32px rgba(70,100,70,0.32), 0 1px 0 rgba(160,200,160,0.4) inset !important; }
        .btn-main:active { transform: translateY(0px); }
        .btn-main { transition: all 0.2s ease; }
      `}</style>

      {/* Responsive Desktop / PC Presentation Shell */}
      <div
        className="w-full max-w-sm md:max-w-4xl rounded-[2.5rem] overflow-hidden flex flex-col shadow-2xl transition-all duration-300"
        style={{
          background: 'rgba(255,255,255,0.85)',
          backdropFilter: 'blur(32px) saturate(2)',
          WebkitBackdropFilter: 'blur(32px) saturate(2)',
          border: '1px solid rgba(255,255,255,0.95)',
          boxShadow: '0 32px 80px rgba(60,90,60,0.12), 0 2px 0 rgba(255,255,255,1) inset',
        }}
      >
        {/* Top bar */}
        <div
          className="px-6 md:px-8 py-4 flex items-center justify-between flex-shrink-0"
          style={{ borderBottom: '1px solid rgba(90,127,90,0.08)' }}
        >
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-2xl flex items-center justify-center overflow-hidden"
              style={{ background: '#ffffff', border: '1px solid rgba(90,127,90,0.15)' }}
            >
              <img src={tomLogo} alt="TOM" className="w-full h-full object-contain" />
            </div>
            <div>
              <p className="text-sage-800 font-semibold text-sm leading-tight">TOM · Talk To Me</p>
              <p className="text-[11px] text-sage-400 tracking-wide">Offline AI Wellbeing Companion</p>
            </div>
          </div>

          <div
            className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold"
            style={{
              background: 'rgba(90,127,90,0.1)',
              border: '1px solid rgba(90,127,90,0.25)',
              color: '#384f38',
            }}
          >
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#5a7f5a', display: 'inline-block', boxShadow: '0 0 8px #5a7f5a' }} />
            100% Local & Private
          </div>
        </div>

        {/* Desktop Split Presentation Layout */}
        <div className="flex flex-col md:grid md:grid-cols-12 gap-6 md:gap-10 p-6 md:p-10 items-center">
          
          {/* Left Column (Hero & Identity) */}
          <div className="w-full md:col-span-5 flex flex-col items-center md:items-start text-center md:text-left fade-in">
            <div className="avatar-float mb-6">
              <div
                className="w-24 h-24 md:w-32 md:h-32 rounded-[2rem] flex items-center justify-center overflow-hidden"
                style={{
                  background: 'linear-gradient(135deg, #ffffff 0%, #f0f4f0 100%)',
                  border: '1px solid rgba(90,127,90,0.15)',
                  boxShadow: '0 20px 50px rgba(46,63,46,0.28), 0 2px 0 rgba(255,255,255,0.15) inset',
                }}
              >
                <img src={tomLogo} alt="TOM" className="w-full h-full object-contain p-2" />
              </div>
            </div>

            <h1
              className="text-sage-800 mb-3 leading-tight"
              style={{ fontFamily: 'var(--font-display)', fontSize: '32px', fontWeight: 400, letterSpacing: '-0.02em' }}
            >
              Meet TOM 👋
            </h1>
            <p className="text-sage-600 text-sm md:text-base leading-relaxed mb-6">
              A private, judgment-free space built right on your computer. Talk freely about your feelings, thoughts, and day-to-day life.
            </p>

            <div
              className="w-full p-3.5 rounded-2xl text-[11px] leading-relaxed text-sage-600 mb-4"
              style={{
                background: 'rgba(90,127,90,0.06)',
                border: '1px solid rgba(90,127,90,0.14)',
              }}
            >
              <strong className="text-sage-700">Safety First:</strong> TOM is an AI companion, not a doctor. In crisis, call <strong>112</strong> or <strong>Tele-MANAS: 14416</strong>.
            </div>
          </div>

          {/* Right Column (Capabilities & CTA) */}
          <div className="w-full md:col-span-7 flex flex-col fade-in-1">
            
            {/* Symmetrical Feature Grid */}
            <div className="grid grid-cols-2 gap-3 w-full mb-6">
              {[
                { emoji: '🤫', title: '100% On-Device', desc: 'No cloud, zero tracking' },
                { emoji: '🦙', title: 'Ollama Engine', desc: 'Runs locally on CPU/GPU' },
                { emoji: '💬', title: 'Empathetic Companion', desc: 'Attentive & caring' },
                { emoji: '🛡️', title: 'Theory of Mind', desc: 'Infers emotional context' },
              ].map(({ emoji, title, desc }) => (
                <div
                  key={title}
                  className="flex flex-col p-3.5 rounded-2xl text-left transition-all hover:translate-y-[-1px]"
                  style={glass.base}
                >
                  <span className="text-xl mb-1">{emoji}</span>
                  <span className="text-xs font-semibold text-sage-800">{title}</span>
                  <span className="text-[10px] text-sage-500">{desc}</span>
                </div>
              ))}
            </div>

            {/* I can help with */}
            <div
              className="w-full rounded-2xl p-4 mb-6"
              style={{
                background: 'rgba(90,127,90,0.05)',
                border: '1px solid rgba(90,127,90,0.12)',
              }}
            >
              <p className="text-xs font-semibold text-sage-700 mb-2 uppercase tracking-wider">Here for you with</p>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                {[
                  '😰 Exam stress',
                  '😔 Low mood',
                  '😟 Family pressure',
                  '😰 Anxiety & fear',
                  '😶 Loneliness',
                  '🧘 Grounding steps',
                ].map((item) => (
                  <p key={item} className="text-xs text-sage-600 flex items-center gap-1.5">{item}</p>
                ))}
              </div>
            </div>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={handleStart}
                disabled={isLoading}
                className="btn-main flex-1 py-3.5 px-6 rounded-2xl text-sm font-semibold text-white disabled:opacity-70 text-center"
                style={{
                  background: 'linear-gradient(145deg, rgba(90,127,90,0.95) 0%, rgba(60,90,60,1) 100%)',
                  border: '1px solid rgba(120,160,120,0.3)',
                  boxShadow: '0 8px 24px rgba(70,100,70,0.28), 0 1px 0 rgba(160,200,160,0.4) inset',
                }}
              >
                {isLoading ? '✨ Launching Workspace...' : '💬 Launch Chatbot'}
              </button>

              <button
                onClick={onGetHelp}
                className="py-3 px-5 rounded-2xl text-xs font-semibold transition-all duration-200 text-center"
                style={{
                  background: 'rgba(196,122,122,0.12)',
                  border: '1px solid rgba(196,122,122,0.28)',
                  color: '#7a2e2e',
                }}
              >
                🆘 Emergency Helplines
              </button>
            </div>

          </div>

        </div>

        {/* Footer */}
        <div
          className="px-6 md:px-8 py-3 text-center flex-shrink-0"
          style={{ borderTop: '1px solid rgba(90,127,90,0.08)' }}
        >
          <p className="text-[11px] text-sage-400">
            Available 24/7 · Runs entirely offline · Not a medical substitute
          </p>
        </div>
      </div>
    </div>
  )
}
