import { useInfiniteQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { PlaylistTracksPage } from '@/types'

const PAGE_SIZE = 50

export function usePlaylistTracks(spotifyId: string | undefined) {
  return useInfiniteQuery({
    queryKey: ['playlist-tracks', spotifyId],
    queryFn: ({ pageParam = 0 }) =>
      api.get<PlaylistTracksPage>(
        `/playlists/${spotifyId}/tracks?limit=${PAGE_SIZE}&offset=${pageParam}`,
      ),
    initialPageParam: 0,
    getNextPageParam: (lastPage) => lastPage.next_offset ?? undefined,
    enabled: !!spotifyId,
    staleTime: 30_000,
  })
}
