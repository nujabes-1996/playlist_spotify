// Dashboard, Settings, Logs

function Dashboard({ density, accentCount, hiddenExpanded, onToggleInclude, onToggleHide, playlists }) {
  const target = playlists.filter(p => p.kind === 'target');
  const visible = playlists.filter(p => !p.hidden && p.kind !== 'target');
  const hidden = playlists.filter(p => p.hidden);

  return (
    <div data-screen-label="Dashboard">
      <h1>Good evening</h1>
      <div style={{ color: 'var(--text-secondary)', fontSize: 14, marginBottom: 4 }}>
        {accentCount} playlist{accentCount === 1 ? '' : 's'} feeding <span style={{ color: 'var(--accent)', fontWeight: 700 }}>Recent Adds</span> · next sync in 18 min
      </div>

      <div className="page-section">
        <div className="section-head">
          <h2>Sync target</h2>
        </div>
        <div className="grid cols-comfy" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(190px, 230px))' }}>
          {target.map(p => (
            <PlaylistCard key={p.id} p={p} onToggleInclude={onToggleInclude} onToggleHide={onToggleHide} />
          ))}
        </div>
      </div>

      <div className="page-section">
        <div className="section-head">
          <h2>Your playlists</h2>
          <span className="link">Show all</span>
        </div>
        {visible.length === 0 ? (
          <div className="empty">
            <I.Sparkles size={28} />
            <h3>No playlists yet</h3>
            <p>Connect your Spotify account in Settings to start picking source playlists.</p>
          </div>
        ) : (
          <PlaylistGrid list={visible} density={density}
                        onToggleInclude={onToggleInclude} onToggleHide={onToggleHide}/>
        )}
      </div>

      <HiddenAccordion hidden={hidden} defaultOpen={hiddenExpanded} density={density}
                       onToggleHide={onToggleHide} />
    </div>
  );
}

// ----- Settings -----

function Field({ label, hint, children }) {
  return (
    <div className="field">
      {label && <label>{label}</label>}
      {children}
      {hint && <div className="field-hint">{hint}</div>}
    </div>
  );
}

function SettingsPage() {
  const [dirty, setDirty] = useState(false);
  const [form, setForm] = useState({
    clientId: '7f3a9c2e1b4d5f6a7b8c9d0e1f2a3b4c',
    clientSecret: '••••••••••••••••••••••••••••••',
    size: 50,
    cron: '0 */1 * * *',
    target: 'Recent Adds',
  });
  function update(k, v) { setForm(f => ({ ...f, [k]: v })); setDirty(true); }
  const presets = [
    { cron: '0 */1 * * *', label: 'every hour' },
    { cron: '0 9,21 * * *', label: 'twice daily' },
    { cron: '0 6 * * *', label: 'every morning' },
    { cron: '*/15 * * * *', label: 'every 15 min' },
  ];

  return (
    <div data-screen-label="Settings">
      <h1>Settings</h1>
      <div style={{ color: 'var(--text-secondary)', marginBottom: 24 }}>
        Connect your Spotify account, choose how often syncs run, and pick a target playlist.
      </div>

      <div className="settings-grid">
        <div>
          <div className="settings-block">
            <h3>Spotify connection</h3>
            <p className="muted">Personal credentials, stored encrypted on your machine.</p>
          </div>
        </div>
        <div className="settings-block">
          <div className="connection-card" style={{ marginBottom: 16 }}>
            <div style={{ width: 40, height: 40, borderRadius: 8, background: 'var(--accent-soft)', display: 'grid', placeItems: 'center', color: 'var(--accent)' }}>
              <I.Spotify size={20}/>
            </div>
            <div style={{ flex: 1 }}>
              <div className="who">yl@ouidou.fr</div>
              <div className="sub"><span className="status-dot" style={{ display: 'inline-block', marginRight: 6 }}/>Healthy · refresh token rotated 2 days ago</div>
            </div>
            <button className="btn btn-secondary" style={{ padding: '8px 16px', fontSize: 12 }}>Reconnect</button>
          </div>
          <Field label="Client ID">
            <input className="input" value={form.clientId} onChange={(e) => update('clientId', e.target.value)} />
          </Field>
          <Field label="Client secret" hint="Required for refresh-token rotation. Never sent to the browser.">
            <input className="input" type="password" value={form.clientSecret} onChange={(e) => update('clientSecret', e.target.value)} />
          </Field>
        </div>

        <div>
          <div className="settings-block">
            <h3>Sync configuration</h3>
            <p className="muted">Controls when the harvester runs and how big the rolling playlist is.</p>
          </div>
        </div>
        <div className="settings-block">
          <Field label="Playlist size" hint="Older tracks rotate out once the playlist exceeds this many entries.">
            <input className="input" type="number" min="1" max="500" value={form.size} onChange={(e) => update('size', e.target.value)} style={{ width: 120 }}/>
          </Field>
          <Field label="Cron expression" hint="Standard 5-field cron, evaluated in your local timezone.">
            <input className="input" value={form.cron} onChange={(e) => update('cron', e.target.value)} style={{ fontFamily: 'var(--font-mono)' }}/>
            <div className="preset-row">
              {presets.map(p => (
                <div key={p.cron} className="preset-pill" onClick={() => update('cron', p.cron)}>
                  {p.label} · {p.cron}
                </div>
              ))}
            </div>
          </Field>
          <Field label="Target playlist name" hint="The harvester will create this playlist if it doesn't exist.">
            <input className="input" value={form.target} onChange={(e) => update('target', e.target.value)} />
          </Field>
        </div>

        <div>
          <div className="settings-block" style={{ borderBottom: 0 }}>
            <h3>Danger zone</h3>
            <p className="muted">Irreversible operations. The harvest playlist will be re-created on next sync if you delete it here.</p>
          </div>
        </div>
        <div className="settings-block" style={{ borderBottom: 0 }}>
          <button className="btn btn-danger" style={{ padding: '8px 16px', fontSize: 12 }}>Disconnect Spotify</button>
        </div>
      </div>

      {dirty && (
        <div className="save-bar">
          <I.Sparkles size={16} style={{ color: 'var(--accent)' }}/>
          <span className="grow">Unsaved changes — review before saving.</span>
          <button className="btn-ghost" onClick={() => setDirty(false)}>Discard</button>
          <button className="btn btn-primary" onClick={() => setDirty(false)}>Save changes</button>
        </div>
      )}
    </div>
  );
}

// ----- Logs -----

function LogRow({ log }) {
  const [open, setOpen] = useState(log.status === 'err');
  const delta = log.added + log.removed;
  return (
    <>
      <div className="log-row" onClick={() => setOpen(!open)} style={{ cursor: log.detail ? 'pointer' : 'default' }}>
        <div className="ts">{log.ts}</div>
        <div>
          <span className={'status-pill ' + (log.status === 'ok' ? 'ok' : log.status === 'err' ? 'err' : 'warn')}>
            {log.status === 'ok' ? 'success' : log.status === 'err' ? 'error' : 'warn'}
          </span>
        </div>
        <div style={{ color: 'var(--text-primary)' }}>{log.msg}</div>
        <div className="delta">
          {log.added > 0 && <span className="pos">+{log.added}</span>}
          {log.added > 0 && log.removed > 0 && ' '}
          {log.removed > 0 && <span className="neg">−{log.removed}</span>}
          {delta === 0 && <span style={{ color: 'var(--text-muted)' }}>—</span>}
        </div>
        <button className="expand-btn" style={{ visibility: log.detail ? 'visible' : 'hidden' }}>
          {open ? <I.ChevDown size={14}/> : <I.ChevRight size={14}/>}
        </button>
      </div>
      {open && log.detail && (
        <div className="log-detail">
          {log.detail.split('\n').map((ln, i) => (
            <div key={i} className={ln.startsWith('ERR') ? 'ln-err' : ''}>{ln}</div>
          ))}
        </div>
      )}
    </>
  );
}

function LogsPage() {
  return (
    <div data-screen-label="Logs">
      <h1>Logs</h1>
      <div style={{ color: 'var(--text-secondary)', marginBottom: 4 }}>
        Live event stream from the harvester · newest first
      </div>
      <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
        <button className="btn btn-secondary" style={{ padding: '6px 14px', fontSize: 12 }}>All</button>
        <button className="btn-ghost" style={{ padding: '6px 14px', fontSize: 12 }}>Errors only</button>
        <button className="btn-ghost" style={{ padding: '6px 14px', fontSize: 12 }}>Last 24h</button>
        <div style={{ flex: 1 }}/>
        <div style={{ color: 'var(--text-muted)', fontSize: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
          <span className="status-dot" />SSE connected
        </div>
      </div>
      <div className="logs">
        {window.logs.map(l => <LogRow key={l.id} log={l} />)}
      </div>
    </div>
  );
}

Object.assign(window, { Dashboard, SettingsPage, LogsPage });
