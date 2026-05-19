import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { AuthStatus } from '@/types'

export function useAuthStatus() {
  return useQuery({
    queryKey: ['auth', 'status'],
    queryFn: () => api.get<AuthStatus>('/auth/status'),
    staleTime: 0,
  })
}
