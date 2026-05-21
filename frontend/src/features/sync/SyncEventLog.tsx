import { useSyncStream } from '@/hooks/useSyncStream'

export default function SyncEventLog() {
  const { isStreaming, events, error } = useSyncStream()

  if (events.length === 0 && !error) return null

  return (
    <div className="space-y-2">
      {events.length > 0 && (
        <ul className="text-sm text-[var(--text-secondary)] space-y-0.5">
          {events.map((ev, i) => (
            <li key={i}>{ev.message}</li>
          ))}
        </ul>
      )}
      {!isStreaming && events.length > 0 && !error && (
        <p className="text-sm text-[var(--accent-color)]">Sync complete.</p>
      )}
      {error && <p className="text-sm text-[var(--danger)]">{error}</p>}
    </div>
  )
}
