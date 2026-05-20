import { useSyncStatus } from '@/hooks/useSyncStatus'

export default function SyncStatusBadge() {
  const { data: status, isPending } = useSyncStatus()

  if (isPending) return null

  if (!status) {
    return (
      <p className="text-sm text-muted-foreground">Last sync: Never synced</p>
    )
  }

  if (status.status === 'success') {
    return (
      <p className="text-sm text-green-600">
        Last sync: Success — {new Date(status.timestamp).toLocaleString()}
        {status.track_count != null && ` (${status.track_count} tracks)`}
      </p>
    )
  }

  return (
    <p className="text-sm text-red-600">
      Last sync: Failed — {status.error_message ?? 'Unknown error'}
    </p>
  )
}
