import { useSyncStream } from '@/hooks/useSyncStream'
import { Button } from '@/components/ui/button'

export default function SyncButton() {
  const { startStream, isStreaming, events, error } = useSyncStream()

  return (
    <div className="space-y-2">
      <Button onClick={startStream} disabled={isStreaming}>
        {isStreaming ? 'Syncing…' : 'Sync Now'}
      </Button>

      {events.length > 0 && (
        <ul className="text-sm text-muted-foreground space-y-0.5">
          {events.map((ev, i) => (
            <li key={i}>{ev.message}</li>
          ))}
        </ul>
      )}

      {!isStreaming && events.length > 0 && !error && (
        <p className="text-sm text-green-600">Sync complete.</p>
      )}

      {error && (
        <p className="text-sm text-red-600">{error}</p>
      )}
    </div>
  )
}
