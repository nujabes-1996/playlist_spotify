// Track row + Recently Added page

function TrackRow({ track, index }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const moreRef = useRef(null);
  const [tooltip, setTooltip] = useState(false);
  return (
    <div className={'trow' + (track.isActive ? ' active' : '')}>
      <div className="trow-index">
        <span className="num">{index + 1}</span>
        <span className="play">{track.isActive ? <I.Pause size={14}/> : <I.Play size={12}/>}</span>
      </div>
      <div className="trow-title">
        <div className="thumb" style={{ background: `center/cover url(${track.art})` }} />
        <div className="trow-title-text">
          <div className="trow-title-main">{track.title}{track.isNew ? <span className="tag-new" style={{ marginLeft: 8 }}>NEW</span> : null}</div>
          <div className="trow-title-sub">
            {track.explicit ? <span className="e-tag">E</span> : null}
            {track.hasVideo ? <I.External size={12} style={{ marginRight: 3, opacity: 0.7 }} /> : null}
            <a>{track.artist}</a>
          </div>
        </div>
      </div>
      <div className="trow-album">{track.album}</div>
      <div className="trow-added" style={{ position: 'relative' }}
           onMouseEnter={() => setTooltip(true)} onMouseLeave={() => setTooltip(false)}>
        {track.addedAgo}
        {tooltip && (
          <span style={{
            position: 'absolute', left: 0, top: '110%',
            background: 'var(--bg-elevated-2)', border: '1px solid var(--border-soft)',
            padding: '4px 8px', borderRadius: 4, fontSize: 11, color: 'var(--text-primary)',
            whiteSpace: 'nowrap', zIndex: 10
          }}>{track.addedAbs}</span>
        )}
      </div>
      <div className="trow-duration">{track.duration}</div>
      <button ref={moreRef} className="more-icon" onClick={(e) => { e.stopPropagation(); setMenuOpen(true); }}>
        <I.More size={14}/>
      </button>
      <Menu open={menuOpen} anchor={moreRef.current} onClose={() => setMenuOpen(false)}>
        <MenuItem icon={I.EyeOff}>Hide from Recent Adds</MenuItem>
        <MenuItem icon={I.External}>Open in Spotify</MenuItem>
      </Menu>
    </div>
  );
}

function RecentlyAdded() {
  // total duration
  const totalSeconds = window.tracks.reduce((acc, t) => {
    const [m, s] = t.duration.split(':').map(Number);
    return acc + m * 60 + s;
  }, 0);
  const totalMin = Math.round(totalSeconds / 60);

  const targetPlaylist = window.playlists.find(p => p.kind === 'target');

  return (
    <div data-screen-label="Recently Added">
      <div className="hero">
        <div className="hero-cover">
          <Cover src={targetPlaylist.cover} title={targetPlaylist.name} big />
        </div>
        <div className="hero-meta">
          <div className="hero-kicker">Auto-synced playlist</div>
          <h1 className="hero-title">Recent Adds</h1>
          <div className="hero-sub">
            <strong>yl@ouidou.fr</strong>
            <span>•</span>
            <span>{window.tracks.length} of 50 tracks</span>
            <span>•</span>
            <span>about {Math.floor(totalMin / 60)} hr {totalMin % 60} min</span>
            <span>•</span>
            <span>updated 21 hours ago from 8 source playlists</span>
          </div>
        </div>
      </div>
      <div className="hero-actions">
        <button className="btn btn-primary"><I.RotateCw size={14}/> Sync now</button>
        <button className="btn btn-secondary"><I.External size={14}/> Open in Spotify</button>
        <button className="btn-icon" title="More options"><I.More size={18}/></button>
      </div>

      <div className="tracklist">
        <div className="tracklist-header">
          <div style={{ textAlign: 'center' }}>#</div>
          <div>Title</div>
          <div>Album</div>
          <div>Date added</div>
          <div style={{ textAlign: 'right' }}><I.Clock size={13}/></div>
          <div></div>
        </div>
        {window.tracks.map((t, i) => <TrackRow key={t.id} track={t} index={i} />)}
      </div>
    </div>
  );
}

Object.assign(window, { TrackRow, RecentlyAdded });
