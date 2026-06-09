import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { InfiniteData, QueryKey } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { PlaylistTracksPage, RecentlyAddedTrack } from '@/types'

interface BlacklistResponse {
  spotify_id: string
  blacklisted_at: string
}

type PlaylistTracksCacheValue =
  | InfiniteData<PlaylistTracksPage>
  | RecentlyAddedTrack[]
  | undefined

type Ctx = {
  previous: RecentlyAddedTrack[] | undefined
  previousPlaylistTracks: Array<[QueryKey, PlaylistTracksCacheValue]>
}

function flagTrack(
  id: string,
  flag: boolean,
): (data: RecentlyAddedTrack[]) => RecentlyAddedTrack[] {
  return (data) =>
    data.map((t) => (t.spotify_id === id ? { ...t, is_blacklisted: flag } : t))
}

function flagInPlaylistCache(
  data: PlaylistTracksCacheValue,
  id: string,
  flag: boolean,
): PlaylistTracksCacheValue {
  if (!data) return data
  if ('pages' in data) {
    return {
      ...data,
      pages: data.pages.map((p) => ({
        ...p,
        items: p.items.map((t) =>
          t.spotify_id === id ? { ...t, is_blacklisted: flag } : t,
        ),
      })),
    }
  }
  if (Array.isArray(data)) {
    return flagTrack(id, flag)(data)
  }
  return data
}

export function useBlacklistTrack() {
  const queryClient = useQueryClient()
  return useMutation<BlacklistResponse, Error, { spotify_id: string }, Ctx>({
    mutationFn: ({ spotify_id }) =>
      api.post<BlacklistResponse>('/blacklist', { spotify_id }),
    onMutate: async ({ spotify_id }) => {
      await queryClient.cancelQueries({ queryKey: ['recently-added'] })
      const previous = queryClient.getQueryData<RecentlyAddedTrack[]>(['recently-added'])
      if (previous) {
        queryClient.setQueryData<RecentlyAddedTrack[]>(
          ['recently-added'],
          flagTrack(spotify_id, true)(previous),
        )
      }

      await queryClient.cancelQueries({ queryKey: ['playlist-tracks'] })
      const previousPlaylistTracks = queryClient.getQueriesData<PlaylistTracksCacheValue>({
        queryKey: ['playlist-tracks'],
      })
      previousPlaylistTracks.forEach(([key, data]) => {
        queryClient.setQueryData(key, flagInPlaylistCache(data, spotify_id, true))
      })

      return { previous, previousPlaylistTracks }
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(['recently-added'], context.previous)
      }
      if (context?.previousPlaylistTracks) {
        context.previousPlaylistTracks.forEach(([key, data]) => {
          queryClient.setQueryData(key, data)
        })
      }
    },
  })
}

export function useUnblacklistTrack() {
  const queryClient = useQueryClient()
  return useMutation<void, Error, { spotify_id: string }, Ctx>({
    mutationFn: ({ spotify_id }) =>
      api.delete(`/blacklist/${encodeURIComponent(spotify_id)}`),
    onMutate: async ({ spotify_id }) => {
      await queryClient.cancelQueries({ queryKey: ['recently-added'] })
      const previous = queryClient.getQueryData<RecentlyAddedTrack[]>(['recently-added'])
      if (previous) {
        queryClient.setQueryData<RecentlyAddedTrack[]>(
          ['recently-added'],
          flagTrack(spotify_id, false)(previous),
        )
      }

      await queryClient.cancelQueries({ queryKey: ['playlist-tracks'] })
      const previousPlaylistTracks = queryClient.getQueriesData<PlaylistTracksCacheValue>({
        queryKey: ['playlist-tracks'],
      })
      previousPlaylistTracks.forEach(([key, data]) => {
        queryClient.setQueryData(key, flagInPlaylistCache(data, spotify_id, false))
      })

      return { previous, previousPlaylistTracks }
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(['recently-added'], context.previous)
      }
      if (context?.previousPlaylistTracks) {
        context.previousPlaylistTracks.forEach(([key, data]) => {
          queryClient.setQueryData(key, data)
        })
      }
    },
  })
}
