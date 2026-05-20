import { useSyncLogs } from '@/hooks/useSyncLogs'

export default function SyncLogPanel() {
  const { data: logs, isPending, isError } = useSyncLogs()

  if (isPending) return <p className="text-sm text-muted-foreground">Loading logs…</p>
  if (isError) return <p className="text-sm text-red-600">Failed to load sync logs.</p>

  if (!logs || logs.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No syncs yet — trigger your first sync from the dashboard.
      </p>
    )
  }

  return (
    <ul className="space-y-2">
      {logs.map((log) => (
        <li key={log.id} className="border rounded p-3 text-sm space-y-1">
          <div className="flex items-center gap-2">
            <span className={log.status === 'success' ? 'text-green-600 font-medium' : 'text-red-600 font-medium'}>
              {log.status === 'success' ? 'Success' : 'Failure'}
            </span>
            <span className="text-muted-foreground">{new Date(log.timestamp).toLocaleString()}</span>
          </div>
          <div>Tracks: {log.track_count ?? '—'}</div>
          {log.status === 'failure' && log.error_message && (
            <div className="text-red-600">{log.error_message}</div>
          )}
        </li>
      ))}
    </ul>
  )
}
