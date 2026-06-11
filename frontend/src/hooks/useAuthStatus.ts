import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { AuthStatus } from '@/types'

export function useAuthStatus() {
  return useQuery({
    queryKey: ['auth', 'status'],
    queryFn: () => api.get<AuthStatus>('/auth/status'),
    staleTime: 0,
  })
}

export function useLogout() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api.post<{ ok: boolean }>('/auth/logout'),
    onSuccess: () => {
      // Drop all cached data and re-evaluate auth → the gate shows the login screen
      queryClient.clear()
      queryClient.invalidateQueries({ queryKey: ['auth', 'status'] })
    },
  })
}
