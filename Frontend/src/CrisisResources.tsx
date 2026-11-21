import { useId } from 'react'
import {
  CRISIS_RESOURCES,
  REGION_LABELS,
  getCrisisResources,
  type CrisisResource,
  type Region,
} from './safety'

interface CrisisResourcesProps {
  region: Region
  onRegionChange?: (region: Region) => void
  resources?: CrisisResource[]
  compact?: boolean
  showRegionPicker?: boolean
}

const REGIONS = Object.keys(CRISIS_RESOURCES) as Region[]

function phoneHref(value: string) {
  return `tel:${value.replace(/[^\d+]/g, '')}`
}

function websiteHref(value?: string) {
  return value && /^https?:\/\//i.test(value) ? value : undefined
}

export default function CrisisResources({
  region,
  onRegionChange,
  resources,
  compact = false,
  showRegionPicker = true,
}: CrisisResourcesProps) {
  const headingId = useId()
  const list = resources && resources.length > 0 ? resources : getCrisisResources(region)

  return (
    <section
      aria-labelledby={headingId}
      className={`rounded-3xl ${compact ? 'p-3' : 'p-4'}`}
      style={{
        background: 'rgba(196,122,122,0.10)',
        border: '1px solid rgba(196,122,122,0.28)',
        boxShadow: '0 4px 18px rgba(122,46,46,0.06)',
      }}
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <div>
          <h2
            id={headingId}
            className={`font-semibold text-[#7a2e2e] ${compact ? 'text-sm' : 'text-base'}`}
            style={{ fontFamily: 'var(--font-display)' }}
          >
            Crisis support
          </h2>
          <p className={`text-[#7a2e2e]/80 ${compact ? 'text-[11px]' : 'text-xs'} leading-snug mt-0.5`}>
            If you are in immediate danger, call your local emergency number.
          </p>
        </div>
        <span className="text-xl flex-shrink-0" aria-hidden="true">
          🆘
        </span>
      </div>

      {showRegionPicker && onRegionChange && (
        <div
          className="flex flex-wrap gap-1.5 mb-3"
          role="group"
          aria-label="Choose your region"
        >
          {REGIONS.map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => onRegionChange(value)}
              aria-pressed={region === value}
              className={`rounded-full px-2.5 py-1 text-[11px] font-medium transition-colors ${
                region === value
                  ? 'bg-[#7a2e2e] text-white'
                  : 'bg-white/60 text-[#7a2e2e] hover:bg-white'
              }`}
              style={{ border: '1px solid rgba(122,46,46,0.18)' }}
            >
              {REGION_LABELS[value]}
            </button>
          ))}
        </div>
      )}

      <ul className="space-y-2">
        {list.map((resource) => {
          const callHref = resource.tel ? phoneHref(resource.tel) : undefined
          const textHref = resource.sms ? `sms:${resource.sms}` : undefined
          const webHref = websiteHref(resource.url)

          return (
            <li
              key={resource.label}
              className="rounded-2xl px-3 py-2.5"
              style={{
                background: 'rgba(255,255,255,0.55)',
                border: '1px solid rgba(122,46,46,0.12)',
              }}
            >
              <p className={`font-semibold text-[#4a2020] ${compact ? 'text-xs' : 'text-sm'}`}>
                {resource.label}
              </p>
              <p className={`text-[#5f3a3a]/85 ${compact ? 'text-[11px]' : 'text-xs'} leading-snug mt-0.5`}>
                {resource.description}
              </p>
              <div className="flex flex-wrap gap-2 mt-2">
                {callHref && (
                  <a
                    href={callHref}
                    className="rounded-full px-2.5 py-1 text-[11px] font-semibold text-white"
                    style={{ background: '#7a2e2e' }}
                    aria-label={`Call ${resource.label}${resource.tel ? ` at ${resource.tel}` : ''}`}
                  >
                    Call {resource.tel}
                  </a>
                )}
                {textHref && (
                  <a
                    href={textHref}
                    className="rounded-full px-2.5 py-1 text-[11px] font-semibold text-[#7a2e2e]"
                    style={{ background: 'rgba(122,46,46,0.10)', border: '1px solid rgba(122,46,46,0.18)' }}
                    aria-label={`Text ${resource.label}`}
                  >
                    Text
                  </a>
                )}
                {webHref && (
                  <a
                    href={webHref}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="rounded-full px-2.5 py-1 text-[11px] font-semibold text-[#466446]"
                    style={{ background: 'rgba(70,100,70,0.10)', border: '1px solid rgba(70,100,70,0.18)' }}
                    aria-label={`Open ${resource.label} website (opens in a new tab)`}
                  >
                    Website ↗
                  </a>
                )}
              </div>
            </li>
          )
        })}
      </ul>

      <p className={`text-[#5f3a3a]/70 ${compact ? 'text-[10px]' : 'text-[11px]'} leading-snug mt-2`}>
        These services are independent of TOM. Numbers can change, so verify locally if you can.
      </p>
    </section>
  )
}
