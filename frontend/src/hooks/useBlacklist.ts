import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { RecentlyAddedTrack } from '@/types'

interface BlacklistResponse {
  spotify_id: string
  blacklisted_at: string
}

export function useBlacklistTrack() {
  const queryClient = useQueryClient()
  return useMutation<
    BlacklistResponse,
    Error,
    { spotify_id: string },
    { previous: RecentlyAddedTrack[] | undefined }
  >({
    mutationFn: ({ spotify_id }) =>
      api.post<BlacklistResponse>('/blacklist', { spotify_id }),
    onMutate: async ({ spotify_id }) => {
      await queryClient.cancelQueries({ queryKey: ['recently-added'] })
      const previous = queryClient.getQueryData<RecentlyAddedTrack[]>(['recently-added'])
      if (previous) {
        queryClient.setQueryData<RecentlyAddedTrack[]>(
          ['recently-added'],
          previous.filter((t) => t.spotify_id !== spotify_id),
        )
      }
      return { previous }
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(['recently-added'], context.previous)
      }
    },
  })
}
