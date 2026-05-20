import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { SyncLog } from '@/types'

export function useSyncLogs() {
  return useQuery({
    queryKey: ['sync', 'logs'],
    queryFn: () => api.get<SyncLog[]>('/sync/logs'),
  })
}
