const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })
const dtf = new Intl.DateTimeFormat('en', { dateStyle: 'medium' })

export function formatRelative(iso?: string | null): string {
  if (!iso) return 'never'
  const diffMs = new Date(iso).getTime() - Date.now()
  const diffMin = Math.round(diffMs / 60000)
  if (Math.abs(diffMin) < 60) return rtf.format(diffMin, 'minute')
  const diffHr = Math.round(diffMin / 60)
  if (Math.abs(diffHr) < 48) return rtf.format(diffHr, 'hour')
  return rtf.format(Math.round(diffHr / 24), 'day')
}

export function formatAbsoluteDate(iso: string): string {
  return dtf.format(new Date(iso))
}
