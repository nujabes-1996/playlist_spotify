import { useCallback, useMemo } from 'react'
import { Sparkles } from 'lucide-react'
import { toast } from 'sonner'
import {
  TrackListHeader,
  TrackRow,
  trackCols,
  type Track,
} from '@/components/TrackRow'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { formatAbsoluteDate, formatRelative } from '@/lib/relativeTime'
import { useBlacklistTrack } from '@/hooks/useBlacklist'
import type { RecentlyAddedTrack } from '@/types'

interface RecentlyAddedTableProps {
  tracks: RecentlyAddedTrack[]
  isLoading: boolean
  error: Error | unknown | null
  refetch: () => void
}

const openInSpotify = (id: string) =>
  window.open(`https://open.spotify.com/track/${id}`, '_blank', 'noreferrer')

function adapt(t: RecentlyAddedTrack): Track {
  const totalSec = Math.round(t.duration_ms / 1000)
  const m = Math.floor(totalSec / 60)
  const s = String(totalSec % 60).padStart(2, '0')
  return {
    id: t.spotify_id,
    title: t.title,
    artist: t.artists.join(', '),
    album: t.album,
    artUrl: t.image_url ?? '',
    durationLabel: `${m}:${s}`,
    addedAgo: formatRelative(t.added_at),
    addedAbs: formatAbsoluteDate(t.added_at),
    explicit: t.explicit,
    hasVideo: t.has_video,
    isNew: false,
    isActive: false,
  }
}

function SkeletonRow() {
  return (
    <div className={cn(trackCols, 'rounded-sm px-4 py-2')}>
      <div className="h-3 w-4 justify-self-center rounded bg-white/5" />
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 flex-shrink-0 rounded-sm bg-white/5 animate-pulse" />
        <div className="min-w-0 flex-1 space-y-1.5">
          <div className="h-3 w-2/3 rounded bg-white/5 animate-pulse" />
          <div className="h-2.5 w-1/3 rounded bg-white/5 animate-pulse" />
        </div>
      </div>
      <div className="hidden h-3 w-3/4 rounded bg-white/5 animate-pulse sm:block" />
      <div className="hidden h-3 w-1/2 rounded bg-white/5 animate-pulse sm:block" />
      <div className="h-3 w-8 justify-self-end rounded bg-white/5 animate-pulse" />
      <div />
    </div>
  )
}

export default function RecentlyAddedTable({
  tracks,
  isLoading,
  error,
  refetch,
}: RecentlyAddedTableProps) {
  const blacklist = useBlacklistTrack()

  const adaptedTracks = useMemo(() => tracks.map(adapt), [tracks])

  const handleHide = useCallback(
    (id: string) => {
      blacklist.mutate(
        { spotify_id: id },
        {
          onSuccess: () =>
            toast.success('Removed from Recent Adds', {
              description:
                'Will be removed from your Spotify playlist on the next sync.',
            }),
          onError: (err) =>
            toast.error("Couldn't hide track", {
              description: err.message.slice(0, 200),
            }),
        },
      )
    },
    [blacklist],
  )

  const errMessage =
    error instanceof Error
      ? error.message
      : error
        ? String(error)
        : null

  return (
    <div>
      <TrackListHeader />

      {errMessage ? (
        <div className="flex flex-col items-center justify-center gap-3 px-4 py-16 text-center">
          <div className="flex items-center gap-2">
            <span className="inline-block h-2 w-2 rounded-full bg-[var(--danger)]" />
            <span className="text-[15px] font-semibold text-white">
              Couldn't load Recently Added
            </span>
          </div>
          <p className="max-w-[400px] truncate text-[12px] text-[var(--text-muted)]">
            {errMessage.slice(0, 400)}
          </p>
          <Button
            variant="outline"
            onClick={() => refetch()}
            className="mt-1 rounded-full border-[var(--border-soft)]"
          >
            Retry
          </Button>
        </div>
      ) : isLoading && tracks.length === 0 ? (
        <div>
          {Array.from({ length: 8 }).map((_, i) => (
            <SkeletonRow key={i} />
          ))}
        </div>
      ) : tracks.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-2 px-4 py-[60px] text-center">
          <Sparkles size={28} className="text-[var(--accent-color)]" />
          <h3 className="text-[18px] font-bold text-white">No tracks yet</h3>
          <p className="max-w-[420px] text-[13px] text-[var(--text-secondary)]">
            Run a sync to populate Recently Added from your source playlists.
          </p>
        </div>
      ) : (
        <div>
          {adaptedTracks.map((track, i) => (
            <TrackRow
              key={`${track.id}-${i}`}
              track={track}
              index={i}
              onHide={handleHide}
              onOpenInSpotify={openInSpotify}
            />
          ))}
        </div>
      )}
    </div>
  )
}
