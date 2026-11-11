import { useEffect, useId, useRef, type ReactNode } from 'react'

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'textarea:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

interface ModalProps {
  title: string
  children: ReactNode
  onClose?: () => void
  dismissible?: boolean
}

/**
 * Small accessible dialog: focus moves inside, Tab stays inside, Escape
 * closes, and focus returns to the element that opened it.
 */
export default function Modal({
  title,
  children,
  onClose,
  dismissible = true,
}: ModalProps) {
  const titleId = useId()
  const dialogRef = useRef<HTMLDivElement>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)
  const closeRef = useRef(onClose)
  const dismissibleRef = useRef(dismissible)

  closeRef.current = onClose
  dismissibleRef.current = dismissible

  useEffect(() => {
    previousFocusRef.current =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null

    const dialog = dialogRef.current
    const initialFocus =
      dialog?.querySelector<HTMLElement>('[data-autofocus]') ??
      dialog?.querySelector<HTMLElement>(FOCUSABLE_SELECTOR) ??
      dialog
    initialFocus?.focus()

    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && dismissibleRef.current) {
        event.preventDefault()
        closeRef.current?.()
        return
      }

      if (event.key !== 'Tab' || !dialog) return

      const focusable = Array.from(
        dialog.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
      ).filter((element) => element.offsetParent !== null)

      if (focusable.length === 0) {
        event.preventDefault()
        dialog.focus()
        return
      }

      const first = focusable[0]
      const last = focusable[focusable.length - 1]

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = previousOverflow
      previousFocusRef.current?.focus()
    }
  }, [])

  return (
    <div
      className="tom-modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && dismissible) {
          onClose?.()
        }
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="tom-modal"
      >
        <div className="flex items-start justify-between gap-3 mb-3">
          <h2
            id={titleId}
            className="text-sage-800"
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: '21px',
              fontWeight: 400,
              letterSpacing: '-0.01em',
            }}
          >
            {title}
          </h2>
          {dismissible && onClose && (
            <button
              type="button"
              onClick={onClose}
              aria-label="Close dialog"
              className="w-7 h-7 rounded-full flex items-center justify-center text-sage-400 hover:text-sage-600 hover:bg-sage-600/10 transition-colors ios-press flex-shrink-0"
            >
              ×
            </button>
          )}
        </div>
        {children}
      </div>
    </div>
  )
}
