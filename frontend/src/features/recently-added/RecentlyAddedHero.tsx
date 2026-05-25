import { RotateCw, ExternalLink, MoreHorizontal } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useSyncStream } from '@/hooks/useSyncStream'
import { cn } from '@/lib/utils'
import type { RecentlyAddedTrack } from '@/types'

interface RecentlyAddedHeroProps {
  tracks: RecentlyAddedTrack[]
  isLoading: boolean
  email: string | null | undefined
  playlistSize: number | undefined
  sourceCount: number | undefined
  lastSyncRelative: string | null
  dynamicPlaylistId: string | null
}

function formatTotalDuration(tracks: { duration_ms: number }[]): string {
  if (tracks.length === 0) return '…'
  const totalMin = Math.round(
    tracks.reduce((s, t) => s + t.duration_ms, 0) / 60000,
  )
  if (totalMin < 60) return `about ${totalMin}m`
  const h = Math.floor(totalMin / 60)
  const m = totalMin % 60
  return m === 0 ? `about ${h}h` : `about ${h}h ${m}m`
}

export default function RecentlyAddedHero({
  tracks,
  isLoading,
  email,
  playlistSize,
  sourceCount,
  lastSyncRelative,
  dynamicPlaylistId,
}: RecentlyAddedHeroProps) {
  const { startStream, isStreaming } = useSyncStream()
  const coverUrl = tracks[0]?.image_url ?? null
  const n = isLoading && tracks.length === 0 ? '…' : tracks.length
  const N = playlistSize ?? '…'
  const duration = isLoading && tracks.length === 0 ? '…' : formatTotalDuration(tracks)
  const updated = lastSyncRelative ?? '…'
  const k = sourceCount ?? '…'
  const who = email ?? 'You'

  const spotifyHref = dynamicPlaylistId
    ? `https://open.spotify.com/playlist/${dynamicPlaylistId}`
    : undefined

  return (
    <div className="-mx-4 md:-mx-8 -mt-2">
      {/* hero gradient block */}
      <div
        className="flex flex-col items-start gap-6 px-8 pb-7 pt-6 md:flex-row md:items-end md:gap-[26px]"
        style={{
          background:
            'linear-gradient(180deg, color-mix(in oklab, var(--accent-color) 40%, #1a1a1a) 0%, var(--bg-elevated) 100%)',
          padding: '24px 32px 28px 32px',
        }}
      >
        {/* cover */}
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

        {/* meta column */}
        <div className="min-w-0 flex-1">
          <div
            className="text-[12px] font-bold uppercase text-white"
            style={{ letterSpacing: '0.06em' }}
          >
            AUTO-SYNCED PLAYLIST
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
            Recent Adds
          </h1>
          <div className="text-[13px] text-[var(--text-secondary)]">
            <strong className="text-white">{who}</strong> • {n} of {N} tracks •{' '}
            {duration} • updated {updated} from {k} source playlists
          </div>
        </div>
      </div>

      {/* actions row */}
      <div
        className="flex items-center gap-4"
        style={{ padding: '20px 32px 4px' }}
      >
        <Button
          onClick={() => startStream()}
          disabled={isStreaming}
          aria-label={isStreaming ? 'Syncing' : 'Sync now'}
          className="rounded-full bg-[var(--accent-color)] px-5 font-bold text-black
                     hover:bg-[var(--accent-hover)] hover:scale-[1.03] active:scale-[0.98] transition"
        >
          <RotateCw size={14} className={cn('mr-2', isStreaming && 'animate-spin')} />
          {isStreaming ? 'Syncing…' : 'Sync now'}
        </Button>

        {spotifyHref ? (
          <a
            href={spotifyHref}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 rounded-full border border-[var(--border-soft)] bg-transparent px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/5"
          >
            <ExternalLink size={14} />
            Open in Spotify
          </a>
        ) : (
          <span
            title="Playlist not created yet"
            className="inline-flex cursor-not-allowed items-center gap-2 rounded-full border border-[var(--border-soft)] bg-transparent px-4 py-2 text-sm font-semibold text-white opacity-50"
          >
            <ExternalLink size={14} />
            Open in Spotify
          </span>
        )}

        <button
          type="button"
          aria-label="More actions"
          className="grid h-9 w-9 place-items-center rounded-full text-[var(--text-secondary)] transition hover:bg-white/5 hover:text-white"
        >
          <MoreHorizontal size={18} />
        </button>
      </div>
    </div>
  )
}
