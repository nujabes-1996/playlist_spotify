import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { ExternalLink, MoreHorizontal, Search, EyeOff } from 'lucide-react'
import { toast } from 'sonner'
import { usePlaylistTracks } from '@/hooks/usePlaylistTracks'
import { usePlaylists } from '@/hooks/usePlaylists'
import { useAuthStatus } from '@/hooks/useAuthStatus'
import { useBlacklistTrack, useUnblacklistTrack } from '@/hooks/useBlacklist'
import { cn } from '@/lib/utils'
import TrackListHero from '@/features/tracks/TrackListHero'
import TrackListTable from '@/features/tracks/TrackListTable'

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

function playlistSpotifyHref(id: string): string {
  return id === 'liked_songs'
    ? 'https://open.spotify.com/collection/tracks'
    : `https://open.spotify.com/playlist/${id}`
}

export default function PlaylistDetailPage() {
  const { spotifyId } = useParams<{ spotifyId: string }>()
  const tracks = usePlaylistTracks(spotifyId)
  const playlists = usePlaylists()
  const auth = useAuthStatus()
  const blacklist = useBlacklistTrack()
  const unblacklist = useUnblacklistTrack()

  const playlist = playlists.data?.find((p) => p.spotify_id === spotifyId)
  const list = useMemo(
    () => tracks.data?.pages.flatMap((p) => p.items) ?? [],
    [tracks.data],
  )
  const totalTracks = tracks.data?.pages[0]?.total ?? 0
  const owner = auth.data?.spotify_user_id ?? 'You'

  const [query, setQuery] = useState('')
  const [showHiddenOnly, setShowHiddenOnly] = useState(false)
  const q = query.trim().toLowerCase()

  // Auto-load more pages while a query is active so the filter has more
  // candidates to match against (filter still applies only to loaded pages).
  useEffect(() => {
    if (q && tracks.hasNextPage && !tracks.isFetchingNextPage) {
      tracks.fetchNextPage()
    }
  }, [q, tracks.hasNextPage, tracks.isFetchingNextPage, tracks.fetchNextPage])

  const filtered = useMemo(() => {
    let result = q
      ? list.filter((t) =>
          (t.title + ' ' + t.artists.join(' ')).toLowerCase().includes(q),
        )
      : list
    if (showHiddenOnly) result = result.filter((t) => t.is_blacklisted)
    return result
  }, [list, q, showHiddenOnly])
  const hasFilter = q.length > 0
  const emptyTitle = showHiddenOnly
    ? 'No hidden tracks'
    : hasFilter
      ? 'No matches'
      : 'This playlist has no tracks'
  const emptyMessage = showHiddenOnly
    ? "You haven't hidden any tracks in this playlist yet."
    : hasFilter
      ? `No tracks match "${query.trim()}".`
      : "There's nothing in this playlist yet."

  if (!playlists.isPending && !playlist) {
    return (
      <TrackListHero
        kicker="PLAYLIST"
        title="Playlist not found"
        subLine={<>This playlist is no longer in your library.</>}
        coverUrl={null}
      />
    )
  }

  const n = tracks.isPending && list.length === 0 ? '…' : totalTracks
  const duration =
    tracks.isPending && list.length === 0 ? '…' : formatTotalDuration(list)

  const subLine = (
    <>
      <strong className="text-white">{owner}</strong> • {n} tracks • {duration}
    </>
  )

  const coverUrl = playlist?.image_url ?? null
  const href = spotifyId ? playlistSpotifyHref(spotifyId) : '#'

  const actions = (
    <>
      <a
        href={href}
        target="_blank"
        rel="noreferrer"
        aria-label="Open in Spotify"
        className="inline-flex items-center gap-2 rounded-full bg-[var(--accent-color)] px-5 py-2 text-sm font-bold text-black transition hover:bg-[var(--accent-hover)] hover:scale-[1.03] active:scale-[0.98]"
      >
        <ExternalLink size={14} />
        Open in Spotify
      </a>
      <div
        className="hidden md:flex w-60 items-center gap-2 rounded-full border border-transparent bg-[var(--bg-elevated-2)] px-3.5 py-1.5 text-[13px] text-[var(--text-secondary)] focus-within:border-[var(--border-strong)]"
      >
        <Search size={15} />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Filter tracks…"
          aria-label="Filter tracks"
          className="w-full bg-transparent text-white outline-none placeholder:text-[var(--text-faint)]"
        />
      </div>
      <button
        type="button"
        onClick={() => setShowHiddenOnly((v) => !v)}
        aria-pressed={showHiddenOnly}
        aria-label="Show hidden tracks only"
        title={showHiddenOnly ? 'Show all tracks' : 'Show hidden tracks only'}
        className={cn(
          'grid h-9 w-9 place-items-center rounded-full transition',
          showHiddenOnly
            ? 'bg-[var(--accent-color)] text-black hover:bg-[var(--accent-hover)]'
            : 'text-[var(--text-secondary)] hover:bg-white/5 hover:text-white',
        )}
      >
        <EyeOff size={16} />
      </button>
      <button
        type="button"
        aria-label="More actions"
        className="grid h-9 w-9 place-items-center rounded-full text-[var(--text-secondary)] transition hover:bg-white/5 hover:text-white"
      >
        <MoreHorizontal size={18} />
      </button>
    </>
  )

  const handleBlacklist = (id: string) => {
    blacklist.mutate(
      { spotify_id: id },
      {
        onSuccess: () =>
          toast.success('Removed from Recent Adds', {
            description:
              'Will be removed from your Spotify Recent Adds playlist on the next sync.',
          }),
        onError: (err) =>
          toast.error("Couldn't hide track", {
            description: err.message.slice(0, 200),
          }),
      },
    )
  }

  const handleUnblacklist = (id: string) => {
    unblacklist.mutate(
      { spotify_id: id },
      {
        onSuccess: () =>
          toast.success('Track unhidden', {
            description:
              'Visible again in your list. Will return to the dynamic playlist on the next sync.',
          }),
        onError: (err) =>
          toast.error("Couldn't unhide track", {
            description: err.message.slice(0, 200),
          }),
      },
    )
  }

  return (
    <>
      <TrackListHero
        kicker="PLAYLIST"
        title={playlist?.name ?? '…'}
        subLine={subLine}
        coverUrl={coverUrl}
        actions={actions}
      />
      <div className="mt-3">
        <TrackListTable
          tracks={filtered}
          isPending={tracks.isPending}
          error={tracks.error}
          refetch={tracks.refetch}
          onBlacklist={handleBlacklist}
          onUnblacklist={handleUnblacklist}
          fetchNextPage={tracks.fetchNextPage}
          hasNextPage={tracks.hasNextPage}
          isFetchingNextPage={tracks.isFetchingNextPage}
          errorTitle="Couldn't load playlist"
          emptyTitle={emptyTitle}
          emptyMessage={emptyMessage}
        />
      </div>
    </>
  )
}
