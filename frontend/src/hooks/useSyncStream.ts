import { useState, useRef, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import type { SyncStreamEvent } from '@/types'

export function useSyncStream() {
  const [isStreaming, setIsStreaming] = useState(false)
  const [events, setEvents] = useState<SyncStreamEvent[]>([])
  const [error, setError] = useState<string | null>(null)
  const esRef = useRef<EventSource | null>(null)
  const queryClient = useQueryClient()

  const startStream = useCallback(() => {
    if (esRef.current) {
      esRef.current.close()
    }

    setIsStreaming(true)
    setEvents([])
    setError(null)

    const es = new EventSource('/api/v1/sync/stream')
    esRef.current = es

    es.addEventListener('sync_log', (e: MessageEvent) => {
      const data: SyncStreamEvent = JSON.parse(e.data)
      setEvents((prev) => [...prev, data])
    })

    const onDone = () => {
      setIsStreaming(false)
      es.close()
      esRef.current = null
      queryClient.invalidateQueries({ queryKey: ['sync', 'logs'] })
      queryClient.invalidateQueries({ queryKey: ['sync', 'status'] })
    }

    es.addEventListener('sync_complete', onDone)

    es.addEventListener('sync_error', (e: MessageEvent) => {
      const data = JSON.parse(e.data)
      setError(data.message ?? 'Sync failed')
      onDone()
    })

    es.onerror = () => {
      setIsStreaming(false)
      esRef.current = null
    }
  }, [queryClient])

  return { startStream, isStreaming, events, error }
}
