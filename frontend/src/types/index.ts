export interface Config {
  setup_required: boolean
  playlist_size: number
  cron_expr: string | null
}

export interface ConfigWrite {
  client_id: string
  client_secret: string
  playlist_size?: number
  cron_expr?: string | null
}

export interface AuthStatus {
  authenticated: boolean
  spotify_user_id?: string | null
}
