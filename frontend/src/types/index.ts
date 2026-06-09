export interface Config {
  setup_required: boolean
  playlist_size: number
  cron_expr: string | null
  dynamic_playlist_id: string | null
}

export interface ConfigWrite {
  client_id: string
  client_secret: string
  playlist_size?: number
  cron_expr?: string | null
}

export interface ConfigPatch {
  playlist_size?: number
  cron_expr?: string | null
}

export interface AuthStatus {
  authenticated: boolean
  has_previous_auth?: boolean
  spotify_user_id?: string | null
}

export interface Playlist {
  spotify_id: string
  name: string
  is_included: boolean
  is_hidden: boolean
  image_url: string | null
  track_count: number
}

export interface SyncLog {
  id: number
  status: 'success' | 'failure'
  track_count: number | null
  error_message: string | null
  timestamp: string
}

export type SyncStatus = SyncLog | null

export interface SyncStreamEvent {
  level: string
  message: string
  timestamp: string
}

export interface RecentlyAddedTrack {
  spotify_id: string
  title: string
  artists: string[]
  album: string
  image_url: string | null
  added_at: string
  duration_ms: number
  explicit: boolean
  has_video: boolean
  is_blacklisted: boolean
}

export interface PlaylistTracksPage {
  items: RecentlyAddedTrack[]
  next_offset: number | null
  total: number
}
