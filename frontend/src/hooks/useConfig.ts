import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Config, ConfigWrite } from '@/types'

export function useConfig() {
  return useQuery({
    queryKey: ['config'],
    queryFn: () => api.get<Config>('/config'),
  })
}

export function useUpdateConfig() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: ConfigWrite) => api.put<Config>('/config', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config'] })
    },
  })
}
