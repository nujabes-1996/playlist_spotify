import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { SyncLog } from '@/types'

export function useSyncStatus() {
  return useQuery({
    queryKey: ['sync', 'status'],
    queryFn: () => api.get<SyncLog | null>('/sync/status'),
  })
}
