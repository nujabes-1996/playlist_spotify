import { cn } from '@/lib/utils'
import { useTogglePlaylist } from '@/hooks/usePlaylists'

interface Props {
  spotify_id: string
  name: string
  is_included: boolean
}

export default function PlaylistToggle({ spotify_id, name, is_included }: Props) {
  const toggle = useTogglePlaylist()
  const isPending = toggle.isPending && toggle.variables?.spotifyId === spotify_id

  return (
    <div
      className={cn(
        'flex flex-col justify-between gap-3 p-4 rounded-xl border transition-all cursor-pointer select-none',
        is_included
          ? 'border-[var(--spotify-green)] bg-[var(--card)] shadow-[0_0_12px_oklch(0.72_0.21_145/0.15)]'
          : 'border-[var(--border)] bg-[var(--card)] hover:border-[var(--muted-foreground)]',
        isPending && 'opacity-60 pointer-events-none'
      )}
      onClick={() => toggle.mutate({ spotifyId: spotify_id, is_included: !is_included })}
      role="button"
      aria-pressed={is_included}
      aria-label={`${is_included ? 'Exclude' : 'Include'} ${name}`}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-sm font-medium leading-snug line-clamp-2">{name}</span>
        {/* Inline switch pill */}
        <button
          type="button"
          disabled={isPending}
          onClick={(e) => {
            e.stopPropagation()
            toggle.mutate({ spotifyId: spotify_id, is_included: !is_included })
          }}
          className={cn(
            'relative shrink-0 w-10 h-6 rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]',
            is_included ? 'bg-[var(--spotify-green)]' : 'bg-red-600'
          )}
        >
          <span
            className={cn(
              'absolute top-1 left-1 w-4 h-4 rounded-full bg-white shadow transition-transform',
              is_included ? 'translate-x-4' : 'translate-x-0'
            )}
          />
        </button>
      </div>
      <span
        className={cn(
          'text-xs font-semibold uppercase tracking-wider',
          is_included ? 'text-[var(--spotify-green)]' : 'text-[var(--muted-foreground)]'
        )}
      >
        {is_included ? 'Included' : 'Excluded'}
      </span>
    </div>
  )
}
