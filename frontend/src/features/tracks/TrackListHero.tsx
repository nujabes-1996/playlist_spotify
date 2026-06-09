import type { ReactNode } from 'react'

export interface TrackListHeroProps {
  kicker: string
  title: string
  subLine: ReactNode
  coverUrl: string | null
  actions?: ReactNode
}

export default function TrackListHero({
  kicker,
  title,
  subLine,
  coverUrl,
  actions,
}: TrackListHeroProps) {
  return (
    <div className="-mx-4 md:-mx-8 -mt-2">
      <div
        className="flex flex-col items-start gap-6 px-8 pb-7 pt-6 md:flex-row md:items-end md:gap-[26px]"
        style={{
          background:
            'linear-gradient(180deg, color-mix(in oklab, var(--accent-color) 40%, #1a1a1a) 0%, var(--bg-elevated) 100%)',
          padding: '24px 32px 28px 32px',
        }}
      >
        {coverUrl ? (
          <img
            src={coverUrl}
            alt=""
            className="h-40 w-40 flex-shrink-0 object-cover md:h-[232px] md:w-[232px]"
            style={{
              borderRadius: '4px',
              boxShadow: '0 16px 40px rgba(0,0,0,0.6)',
            }}
          />
        ) : (
          <div
            className="h-40 w-40 flex-shrink-0 md:h-[232px] md:w-[232px]"
            style={{
              borderRadius: '4px',
              boxShadow: '0 16px 40px rgba(0,0,0,0.6)',
              background: 'linear-gradient(135deg, var(--accent-color), #22d3ee)',
            }}
          />
        )}

        <div className="min-w-0 flex-1">
          <div
            className="text-[12px] font-bold uppercase text-white"
            style={{ letterSpacing: '0.06em' }}
          >
            {kicker}
          </div>
          <h1
            className="text-white"
            style={{
              fontSize: 'clamp(40px, 5vw, 72px)',
              fontWeight: 900,
              letterSpacing: '-0.04em',
              lineHeight: 1,
              margin: '6px 0 14px',
            }}
          >
            {title}
          </h1>
          <div className="text-[13px] text-[var(--text-secondary)]">{subLine}</div>
        </div>
      </div>

      {actions ? (
        <div
          className="flex items-center gap-4"
          style={{ padding: '20px 32px 4px' }}
        >
          {actions}
        </div>
      ) : null}
    </div>
  )
}
