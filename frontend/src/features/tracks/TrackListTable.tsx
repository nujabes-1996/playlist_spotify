import { useCallback, useEffect, useMemo, useRef } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { Sparkles } from 'lucide-react'
import {
  TrackListHeader,
  TrackRow,
  trackCols,
  type Track,
} from '@/components/TrackRow'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { formatAbsoluteDate, formatRelative } from '@/lib/relativeTime'
import type { RecentlyAddedTrack } from '@/types'

const VIRTUALIZE_THRESHOLD = 200

export interface TrackListTableProps {
  tracks: RecentlyAddedTrack[]
  isPending: boolean
  error: Error | unknown | null
  refetch: () => void
  emptyTitle?: string
  emptyMessage?: string
  errorTitle?: string
  onBlacklist?: (spotifyId: string) => void
  onUnblacklist?: (spotifyId: string) => void
  onOpenInSpotify?: (spotifyId: string) => void
  fetchNextPage?: () => void
  hasNextPage?: boolean
  isFetchingNextPage?: boolean
}

const defaultOpenInSpotify = (id: string) =>
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
    isBlacklisted: t.is_blacklisted,
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

export default function TrackListTable({
  tracks,
  isPending,
  error,
  refetch,
  emptyTitle = 'No tracks yet',
  emptyMessage = 'Run a sync to populate Recently Added from your source playlists.',
  errorTitle = "Couldn't load tracks",
  onBlacklist,
  onUnblacklist,
  onOpenInSpotify,
  fetchNextPage,
  hasNextPage,
  isFetchingNextPage,
}: TrackListTableProps) {
  const adaptedTracks = useMemo(() => tracks.map(adapt), [tracks])
  const openInSpotify = onOpenInSpotify ?? defaultOpenInSpotify
  const handleHide = useCallback(
    (id: string) => onBlacklist?.(id),
    [onBlacklist],
  )
  const handleUnhide = useCallback(
    (id: string) => onUnblacklist?.(id),
    [onUnblacklist],
  )

  const sentinelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = sentinelRef.current
    if (!el || !fetchNextPage || !hasNextPage) return
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting && !isFetchingNextPage) {
          fetchNextPage()
        }
      },
      { rootMargin: '300px' },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [fetchNextPage, hasNextPage, isFetchingNextPage])

  const shouldVirtualize = tracks.length > VIRTUALIZE_THRESHOLD
  const virtualizer = useVirtualizer({
    count: adaptedTracks.length,
    getScrollElement: () =>
      typeof document !== 'undefined'
        ? document.getElementById('main-scroll')
        : null,
    estimateSize: () => 56,
    overscan: 8,
  })

  const errMessage =
    error instanceof Error
      ? error.message
      : error
        ? String(error)
        : null

  const showVirtualized =
    !errMessage &&
    !(isPending && tracks.length === 0) &&
    tracks.length > 0 &&
    shouldVirtualize

  return (
    <div>
      {!showVirtualized && <TrackListHeader />}

      {errMessage ? (
        <div className="flex flex-col items-center justify-center gap-3 px-4 py-16 text-center">
          <div className="flex items-center gap-2">
            <span className="inline-block h-2 w-2 rounded-full bg-[var(--danger)]" />
            <span className="text-[15px] font-semibold text-white">
              {errorTitle}
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
      ) : isPending && tracks.length === 0 ? (
        <div>
          {Array.from({ length: 8 }).map((_, i) => (
            <SkeletonRow key={i} />
          ))}
        </div>
      ) : tracks.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-2 px-4 py-[60px] text-center">
          <Sparkles size={28} className="text-[var(--accent-color)]" />
          <h3 className="text-[18px] font-bold text-white">{emptyTitle}</h3>
          <p className="max-w-[420px] text-[13px] text-[var(--text-secondary)]">
            {emptyMessage}
          </p>
        </div>
      ) : shouldVirtualize ? (
        <div>
          <TrackListHeader />
          <div
            style={{
              height: virtualizer.getTotalSize(),
              width: '100%',
              position: 'relative',
            }}
          >
            {virtualizer.getVirtualItems().map((vRow) => {
              const track = adaptedTracks[vRow.index]
              return (
                <div
                  key={`${track.id}-${vRow.index}`}
                  data-index={vRow.index}
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    transform: `translateY(${vRow.start}px)`,
                  }}
                >
                  <TrackRow
                    track={track}
                    index={vRow.index}
                    onHide={handleHide}
                    onUnhide={handleUnhide}
                    onOpenInSpotify={openInSpotify}
                  />
                </div>
              )
            })}
          </div>
          <div ref={sentinelRef} style={{ height: 1 }} />
          {isFetchingNextPage && (
            <>
              <SkeletonRow />
              <SkeletonRow />
              <SkeletonRow />
            </>
          )}
        </div>
      ) : (
        <div>
          {adaptedTracks.map((track, i) => (
            <TrackRow
              key={`${track.id}-${i}`}
              track={track}
              index={i}
              onHide={handleHide}
              onUnhide={handleUnhide}
              onOpenInSpotify={openInSpotify}
            />
          ))}
          <div ref={sentinelRef} style={{ height: 1 }} />
          {isFetchingNextPage && (
            <>
              <SkeletonRow />
              <SkeletonRow />
              <SkeletonRow />
            </>
          )}
        </div>
      )}
    </div>
  )
}
