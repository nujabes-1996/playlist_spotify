import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Playlist } from '@/types'

export function usePlaylists() {
  return useQuery({
    queryKey: ['playlists'],
    queryFn: () => api.get<Playlist[]>('/playlists'),
  })
}

export function useTogglePlaylist() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ spotifyId, is_included }: { spotifyId: string; is_included: boolean }) =>
      api.patch<Playlist>(`/playlists/${spotifyId}`, { is_included }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['playlists'] })
    },
  })
}
