import { useSyncStatus } from '@/hooks/useSyncStatus'

export default function SyncStatusBadge() {
  const { data: status, isPending } = useSyncStatus()

  if (isPending) return null

  if (!status) {
    return (
      <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[var(--muted)] text-[var(--muted-foreground)] text-xs font-medium">
        <span className="w-2 h-2 rounded-full bg-[var(--muted-foreground)]" />
        Never synced
      </div>
    )
  }

  if (status.status === 'success') {
    return (
      <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[var(--spotify-green)]/10 text-[var(--spotify-green)] text-xs font-medium">
        <span className="w-2 h-2 rounded-full bg-[var(--spotify-green)]" />
        Last sync: {new Date(status.timestamp).toLocaleString()}
        {status.track_count != null && ` · ${status.track_count} tracks`}
      </div>
    )
  }

  return (
    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-red-600/10 text-red-500 text-xs font-medium">
      <span className="w-2 h-2 rounded-full bg-red-500" />
      Last sync failed — {status.error_message ?? 'Unknown error'}
    </div>
  )
}
