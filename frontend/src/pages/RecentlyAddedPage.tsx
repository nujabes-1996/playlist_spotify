import { RotateCw, ExternalLink, MoreHorizontal } from 'lucide-react'
import { toast } from 'sonner'
import { useRecentlyAdded } from '@/hooks/useRecentlyAdded'
import { useAuthStatus } from '@/hooks/useAuthStatus'
import { useConfig } from '@/hooks/useConfig'
import { useSyncStatus } from '@/hooks/useSyncStatus'
import { usePlaylists } from '@/hooks/usePlaylists'
import { useSyncStream } from '@/hooks/useSyncStream'
import { useBlacklistTrack, useUnblacklistTrack } from '@/hooks/useBlacklist'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { formatRelative } from '@/lib/relativeTime'
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

export default function RecentlyAddedPage() {
  const tracks = useRecentlyAdded()
  const auth = useAuthStatus()
  const config = useConfig()
  const sync = useSyncStatus()
  const playlists = usePlaylists()
  const { startStream, isStreaming } = useSyncStream()
  const blacklist = useBlacklistTrack()
  const unblacklist = useUnblacklistTrack()

  const list = tracks.data ?? []
  const sourceCount = playlists.data?.filter((p) => p.is_included).length
  const lastSyncRelative = sync.data ? formatRelative(sync.data.timestamp) : null
  const coverUrl = list[0]?.image_url ?? null
  const dynamicPlaylistId = config.data?.dynamic_playlist_id ?? null
  const spotifyHref = dynamicPlaylistId
    ? `https://open.spotify.com/playlist/${dynamicPlaylistId}`
    : undefined

  const n = tracks.isPending && list.length === 0 ? '…' : list.length
  const N = config.data?.playlist_size ?? '…'
  const duration =
    tracks.isPending && list.length === 0 ? '…' : formatTotalDuration(list)
  const who = auth.data?.spotify_user_id ?? 'You'
  const k = sourceCount ?? '…'
  const updated = lastSyncRelative ?? '…'

  const subLine = (
    <>
      <strong className="text-white">{who}</strong> • {n} of {N} tracks •{' '}
      {duration} • updated {updated} from {k} source playlists
    </>
  )

  const actions = (
    <>
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
    </>
  )

  const handleBlacklist = (id: string) => {
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
        kicker="AUTO-SYNCED PLAYLIST"
        title="Recent Adds"
        subLine={subLine}
        coverUrl={coverUrl}
        actions={actions}
      />
      <div className="mt-3">
        <TrackListTable
          tracks={list}
          isPending={tracks.isPending}
          error={tracks.error}
          refetch={tracks.refetch}
          onBlacklist={handleBlacklist}
          onUnblacklist={handleUnblacklist}
          errorTitle="Couldn't load Recently Added"
        />
      </div>
    </>
  )
}
