import { useState } from 'react'
import Modal from './Modal.tsx'

interface ConsentGateProps {
  onAccept: () => void
  onDecline: () => void
  onOpenResources: () => void
}

export default function ConsentGate({
  onAccept,
  onDecline,
  onOpenResources,
}: ConsentGateProps) {
  const [understood, setUnderstood] = useState(false)

  return (
    <Modal title="Before we talk" onClose={onDecline}>
      <div className="space-y-3 text-sm text-sage-600 leading-relaxed">
        <p>
          TOM is a supportive AI companion. It is not a therapist, doctor, or
          emergency service, and it can make mistakes.
        </p>

        <ul className="space-y-2 text-xs">
          <li
            className="rounded-2xl px-3 py-2.5"
            style={{
              background: 'rgba(90,127,90,0.06)',
              border: '1px solid rgba(90,127,90,0.12)',
            }}
          >
            <strong className="font-semibold text-sage-700">
              Your messages
            </strong>{' '}
            are sent to the TOM server to generate a reply. Server context is
            kept in memory only, expires after 30 minutes, and is not a chat
            archive.
          </li>
          <li
            className="rounded-2xl px-3 py-2.5"
            style={{
              background: 'rgba(90,127,90,0.06)',
              border: '1px solid rgba(90,127,90,0.12)',
            }}
          >
            <strong className="font-semibold text-sage-700">
              On this device
            </strong>{' '}
            your chat is kept in this tab's session storage. Your consent,
            region, and an anonymous session ID are kept in local storage.
          </li>
          <li
            className="rounded-2xl px-3 py-2.5"
            style={{
              background: 'rgba(90,127,90,0.06)',
              border: '1px solid rgba(90,127,90,0.12)',
            }}
          >
            <strong className="font-semibold text-sage-700">
              No account or ads.
            </strong>{' '}
            Your conversations are not used to train models. You can clear or
            delete everything from Privacy at any time.
          </li>
        </ul>

        <label className="flex items-start gap-2.5 rounded-2xl px-3 py-3 cursor-pointer text-xs text-sage-700">
          <input
            type="checkbox"
            checked={understood}
            onChange={(event) => setUnderstood(event.target.checked)}
            data-autofocus
            className="mt-0.5 h-4 w-4 flex-shrink-0 accent-sage-600"
          />
          <span>
            I understand and agree to this use of my data before I start
            chatting.
          </span>
        </label>
      </div>

      <div className="mt-4 space-y-2">
        <button
          type="button"
          onClick={onAccept}
          disabled={!understood}
          className="w-full py-2.5 rounded-2xl text-sm font-semibold text-white ios-press disabled:opacity-40 disabled:cursor-not-allowed"
          style={{
            background: understood
              ? 'linear-gradient(145deg, rgba(90,127,90,0.9) 0%, rgba(70,100,70,0.95) 100%)'
              : 'rgba(90,127,90,0.35)',
            border: '1px solid rgba(120,160,120,0.4)',
            boxShadow: understood
              ? '0 6px 20px rgba(70,100,70,0.24), 0 1px 0 rgba(160,200,160,0.4) inset'
              : 'none',
          }}
        >
          I understand — continue
        </button>
        <button
          type="button"
          onClick={onOpenResources}
          className="w-full py-2 rounded-2xl text-xs font-semibold text-[#7a2e2e] ios-press"
          style={{
            background: 'rgba(196,122,122,0.12)',
            border: '1px solid rgba(196,122,122,0.3)',
          }}
        >
          See crisis support instead
        </button>
        <button
          type="button"
          onClick={onDecline}
          className="w-full py-1.5 text-[11px] font-medium text-sage-400 hover:text-sage-600 transition-colors"
        >
          Not now
        </button>
      </div>
    </Modal>
  )
}
