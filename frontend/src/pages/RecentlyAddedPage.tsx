import { useRecentlyAdded } from '@/hooks/useRecentlyAdded'
import { useAuthStatus } from '@/hooks/useAuthStatus'
import { useConfig } from '@/hooks/useConfig'
import { useSyncStatus } from '@/hooks/useSyncStatus'
import { usePlaylists } from '@/hooks/usePlaylists'
import { formatRelative } from '@/lib/relativeTime'
import RecentlyAddedHero from '@/features/recently-added/RecentlyAddedHero'
import RecentlyAddedTable from '@/features/recently-added/RecentlyAddedTable'

export default function RecentlyAddedPage() {
  const tracks = useRecentlyAdded()
  const auth = useAuthStatus()
  const config = useConfig()
  const sync = useSyncStatus()
  const playlists = usePlaylists()

  const sourceCount = playlists.data?.filter((p) => p.is_included).length
  const lastSyncRelative = sync.data ? formatRelative(sync.data.timestamp) : null

  return (
    <>
      <RecentlyAddedHero
        tracks={tracks.data ?? []}
        isLoading={tracks.isPending}
        email={auth.data?.spotify_user_id}
        playlistSize={config.data?.playlist_size}
        sourceCount={sourceCount}
        lastSyncRelative={lastSyncRelative}
        dynamicPlaylistId={config.data?.dynamic_playlist_id ?? null}
      />
      <div className="mt-3">
        <RecentlyAddedTable
          tracks={tracks.data ?? []}
          isLoading={tracks.isPending}
          error={tracks.error}
          refetch={tracks.refetch}
        />
      </div>
    </>
  )
}
