import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { RecentlyAddedTrack } from '@/types'

export function useRecentlyAdded() {
  return useQuery({
    queryKey: ['recently-added'],
    queryFn: () => api.get<RecentlyAddedTrack[]>('/recently-added'),
    staleTime: 30_000,
  })
}
