import PlaylistGrid from '@/features/playlists/PlaylistGrid'
import HiddenPlaylistsAccordion from '@/features/playlists/HiddenPlaylistsAccordion'
import SyncEventLog from '@/features/sync/SyncEventLog'

// Auth/setup gating moved to AppShell (Story 10.2): by the time this renders the
// visitor has a valid session, so the dashboard just shows playlist content.
export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--foreground)]">Your Playlists</h1>
        <p className="text-sm text-[var(--muted-foreground)] mt-1">
          Toggle which playlists to include in your next sync
        </p>
      </div>

      <SyncEventLog />
      <PlaylistGrid />
      <HiddenPlaylistsAccordion />
    </div>
  )
}
