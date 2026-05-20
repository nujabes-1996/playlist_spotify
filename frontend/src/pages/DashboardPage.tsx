import { useConfig } from '@/hooks/useConfig'
import { useAuthStatus } from '@/hooks/useAuthStatus'
import SetupWizard from '@/features/config/SetupWizard'
import SpotifyConnect from '@/features/auth/SpotifyConnect'
import ReauthBanner from '@/features/auth/ReauthBanner'
import PlaylistList from '@/features/playlists/PlaylistList'
import SyncButton from '@/features/sync/SyncButton'
import SyncStatusBadge from '@/features/sync/SyncStatusBadge'

export default function DashboardPage() {
  const config = useConfig()
  const authStatus = useAuthStatus()

  if (config.isPending || authStatus.isPending) {
    return <div className="text-sm text-[var(--muted-foreground)]">Loading…</div>
  }

  if (config.isError || authStatus.isError) {
    return <div className="text-sm text-red-500">Failed to load configuration.</div>
  }

  if (config.data.setup_required) {
    return <SetupWizard />
  }

  if (!authStatus.data.authenticated) {
    return authStatus.data.has_previous_auth ? <ReauthBanner /> : <SpotifyConnect />
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--foreground)]">Your Playlists</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            Toggle which playlists to include in your next sync
          </p>
        </div>
        <SyncButton />
      </div>

      <SyncStatusBadge />
      <PlaylistList />
    </div>
  )
}
