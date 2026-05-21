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

export function useHidePlaylist() {
  const queryClient = useQueryClient()
  return useMutation<
    Playlist,
    Error,
    { spotifyId: string; is_hidden: boolean },
    { previous: Playlist[] | undefined }
  >({
    mutationFn: ({ spotifyId, is_hidden }) =>
      api.patch<Playlist>(`/playlists/${spotifyId}`, { is_hidden }),
    onMutate: async ({ spotifyId, is_hidden }) => {
      await queryClient.cancelQueries({ queryKey: ['playlists'] })
      const previous = queryClient.getQueryData<Playlist[]>(['playlists'])
      if (previous) {
        queryClient.setQueryData<Playlist[]>(
          ['playlists'],
          previous.map((p) =>
            p.spotify_id === spotifyId
              ? { ...p, is_hidden, is_included: is_hidden ? false : p.is_included }
              : p,
          ),
        )
      }
      return { previous }
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(['playlists'], context.previous)
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['playlists'] })
    },
  })
}
