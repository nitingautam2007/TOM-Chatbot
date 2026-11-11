import { useState } from 'react'
import Modal from './Modal.tsx'

interface PrivacyPanelProps {
  onClose: () => void
  onNewChat: () => void
  onClearChat: () => void
  onDeleteData: () => void
  onOpenResources: () => void
}

const noteStyle = {
  background: 'rgba(90,127,90,0.06)',
  border: '1px solid rgba(90,127,90,0.12)',
} as const

const secondaryButtonStyle = {
  background:
    'linear-gradient(145deg, rgba(255,255,255,0.72) 0%, rgba(255,255,255,0.48) 100%)',
  border: '1px solid rgba(90,127,90,0.18)',
  color: 'var(--color-sage-700)',
} as const

export default function PrivacyPanel({
  onClose,
  onNewChat,
  onClearChat,
  onDeleteData,
  onOpenResources,
}: PrivacyPanelProps) {
  const [confirmDelete, setConfirmDelete] = useState(false)

  return (
    <Modal title="Privacy & your data" onClose={onClose}>
      <div className="space-y-4 text-sm text-sage-600 leading-relaxed">
        <p>
          TOM does not require an account. This panel shows what is stored and
          lets you remove it whenever you want.
        </p>

        <dl className="space-y-2 text-xs">
          <div className="rounded-2xl px-3 py-2.5" style={noteStyle}>
            <dt className="font-semibold text-sage-700">On this device</dt>
            <dd className="mt-0.5">
              Your conversation lives in this tab's session storage. Consent,
              region, and an anonymous session ID live in local storage.
            </dd>
          </div>
          <div className="rounded-2xl px-3 py-2.5" style={noteStyle}>
            <dt className="font-semibold text-sage-700">On the TOM server</dt>
            <dd className="mt-0.5">
              Recent context is held in memory only, expires after 30 minutes,
              and is never written to a chat database.
            </dd>
          </div>
        </dl>

        <section>
          <h3 className="text-sm font-semibold text-sage-700 mb-2">
            Conversation controls
          </h3>
          <div className="space-y-2">
            <button
              type="button"
              onClick={onNewChat}
              className="w-full py-2 rounded-2xl text-xs font-semibold ios-press"
              style={secondaryButtonStyle}
            >
              Start a new conversation
            </button>
            <button
              type="button"
              onClick={onClearChat}
              className="w-full py-2 rounded-2xl text-xs font-semibold ios-press"
              style={secondaryButtonStyle}
            >
              Clear this conversation
            </button>
          </div>
        </section>

        <section>
          <h3 className="text-sm font-semibold text-sage-700 mb-2">
            Delete stored data
          </h3>
          {!confirmDelete ? (
            <button
              type="button"
              onClick={() => setConfirmDelete(true)}
              className="w-full py-2 rounded-2xl text-xs font-semibold text-[#7a2e2e] ios-press"
              style={{
                background: 'rgba(196,122,122,0.12)',
                border: '1px solid rgba(196,122,122,0.3)',
              }}
            >
              Delete my data &amp; withdraw consent
            </button>
          ) : (
            <div
              role="group"
              aria-label="Confirm data deletion"
              className="rounded-2xl px-3 py-3"
              style={{
                background: 'rgba(196,122,122,0.10)',
                border: '1px solid rgba(196,122,122,0.28)',
              }}
            >
              <p className="text-xs text-[#6b3030]">
                This clears the conversation, saved region, and consent record
                on this device, and asks the server to forget this session. If
                the server can't be reached, its in-memory context expires
                automatically. You will need to consent again before chatting.
              </p>
              <div className="flex gap-2 mt-2.5">
                <button
                  type="button"
                  onClick={onDeleteData}
                  className="flex-1 py-2 rounded-xl text-[11px] font-semibold text-white"
                  style={{ background: '#7a2e2e' }}
                >
                  Yes, delete everything
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmDelete(false)}
                  className="flex-1 py-2 rounded-xl text-[11px] font-semibold text-sage-700"
                  style={secondaryButtonStyle}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </section>

        <button
          type="button"
          onClick={onOpenResources}
          className="w-full py-2 rounded-2xl text-xs font-semibold text-[#7a2e2e] ios-press"
          style={{
            background: 'rgba(196,122,122,0.10)',
            border: '1px solid rgba(196,122,122,0.24)',
          }}
        >
          Open crisis &amp; support resources
        </button>
      </div>
    </Modal>
  )
}
