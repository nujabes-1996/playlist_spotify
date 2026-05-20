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
    return <div className="p-6 text-sm text-muted-foreground">Loading…</div>
  }

  if (config.isError || authStatus.isError) {
    return <div className="p-6 text-sm text-red-600">Failed to load configuration.</div>
  }

  if (config.data.setup_required) {
    return <SetupWizard />
  }

  if (!authStatus.data.authenticated) {
    return authStatus.data.has_previous_auth ? <ReauthBanner /> : <SpotifyConnect />
  }

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <SyncStatusBadge />
      <PlaylistList />
      <SyncButton />
    </div>
  )
}
