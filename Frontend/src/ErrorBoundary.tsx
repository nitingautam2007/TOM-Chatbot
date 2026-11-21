import { Component, type ErrorInfo, type ReactNode } from 'react'
import tomLogo from '@/imports/TOM_Bot.png'

interface ErrorBoundaryProps {
  children: ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
}

/**
 * Last-resort recovery screen. TOM has no server-side account state, so a
 * reload does not lose consent or the saved conversation in this tab.
 */
export default class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { hasError: false }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('TOM UI error:', error, info.componentStack)
  }

  render() {
    if (!this.state.hasError) return this.props.children

    return (
      <div
        className="tom-screen flex flex-col items-center justify-center"
        style={{
          backgroundColor: '#ffffff',
          backgroundImage:
            'linear-gradient(rgba(90,127,90,0.07) 1px, transparent 1px), linear-gradient(90deg, rgba(90,127,90,0.07) 1px, transparent 1px)',
          backgroundSize: '32px 32px',
        }}
      >
        <div
          role="alert"
          className="w-full max-w-md rounded-[2.5rem] p-6 text-center"
          style={{
            background:
              'linear-gradient(145deg, rgba(255,255,255,0.82) 0%, rgba(255,255,255,0.56) 100%)',
            backdropFilter: 'blur(32px) saturate(2)',
            WebkitBackdropFilter: 'blur(32px) saturate(2)',
            border: '1px solid rgba(255,255,255,0.9)',
            boxShadow:
              '0 16px 48px rgba(90,127,90,0.12), 0 2px 0 rgba(255,255,255,1) inset',
          }}
        >
          <div
            className="w-14 h-14 rounded-2xl flex items-center justify-center overflow-hidden mx-auto mb-4"
            style={{ background: '#0d0d12' }}
          >
            <img
              src={tomLogo}
              alt="TOM"
              className="w-full h-full object-contain"
            />
          </div>
          <h1
            className="text-sage-800 mb-2"
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: '24px',
              fontWeight: 400,
              letterSpacing: '-0.01em',
            }}
          >
            Something went wrong
          </h1>
          <p className="text-sm text-sage-600 leading-relaxed mb-5">
            TOM hit an unexpected problem. If you had a saved conversation, it
            should still be on this device after a reload.
          </p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="w-full py-2.5 rounded-2xl text-sm font-semibold text-white ios-press"
            style={{
              background:
                'linear-gradient(145deg, rgba(90,127,90,0.9) 0%, rgba(70,100,70,0.95) 100%)',
              border: '1px solid rgba(120,160,120,0.4)',
              boxShadow:
                '0 6px 20px rgba(70,100,70,0.28), 0 1px 0 rgba(160,200,160,0.4) inset',
            }}
          >
            Reload TOM
          </button>
          <p className="text-[11px] text-[#7a2e2e] leading-relaxed mt-5">
            If you need support right now, please contact your local emergency
            number or a crisis line. You matter, and you deserve to speak with
            a real person.
          </p>
        </div>
      </div>
    )
  }
}
