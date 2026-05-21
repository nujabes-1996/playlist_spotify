// PlaylistCard + Hidden accordion + cover

function Cover({ src, title, big }) {
  return (
    <div className="cover-abstract" style={{ background: `center / cover no-repeat url(${src})`, height: '100%', width: '100%' }}>
      <div className="ttl">{title}</div>
    </div>
  );
}

function PlaylistCard({ p, dimmed, onToggleInclude, onToggleHide }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const moreRef = useRef(null);
  return (
    <div className={'pcard' + (dimmed ? ' dimmed' : '') + (p.included ? ' included' : '')}>
      <div className="cover-wrap">
        <Cover src={p.cover} title={p.name} />
        {p.included && (
          <div className="include-badge" title="Included in sync">
            <I.Check size={12}/>
          </div>
        )}
      </div>
      <button ref={moreRef} className="more-btn" onClick={(e) => { e.stopPropagation(); setMenuOpen(true); }} aria-label="More">
        <I.More size={14}/>
      </button>
      <button className="play-fab" aria-label="Preview"><I.Play size={16} /></button>

      <h3 title={p.name}>{p.name}</h3>
      <div className="meta">
        <span>{p.tracks.toLocaleString()} tracks</span>
        {p.kind === 'target' && <><span className="sep">•</span><span style={{ color: 'var(--accent)', fontWeight: 700 }}>Sync target</span></>}
      </div>

      <Menu open={menuOpen} anchor={moreRef.current} onClose={() => setMenuOpen(false)}>
        {p.kind !== 'target' && (
          <MenuItem icon={p.included ? I.X : I.PlusCheck} onClick={() => onToggleInclude(p.id)}>
            {p.included ? 'Remove from sync' : 'Include in sync'}
          </MenuItem>
        )}
        <MenuItem icon={p.hidden ? I.Eye : I.EyeOff} onClick={() => onToggleHide(p.id)}>
          {p.hidden ? 'Unhide' : 'Hide playlist'}
        </MenuItem>
        <div className="menu-sep" />
        <MenuItem icon={I.External}>Open in Spotify</MenuItem>
      </Menu>
    </div>
  );
}

function PlaylistGrid({ list, density, dimmed, onToggleInclude, onToggleHide }) {
  return (
    <div className={'grid cols-' + density}>
      {list.map(p => (
        <PlaylistCard key={p.id} p={p} dimmed={dimmed}
                      onToggleInclude={onToggleInclude}
                      onToggleHide={onToggleHide} />
      ))}
    </div>
  );
}

function HiddenAccordion({ hidden, defaultOpen, density, onToggleHide }) {
  const [open, setOpen] = useState(!!defaultOpen);
  useEffect(() => { setOpen(!!defaultOpen); }, [defaultOpen]);
  if (hidden.length === 0) return null;
  return (
    <div className="accordion">
      <div className={'accordion-head' + (open ? ' open' : '')} onClick={() => setOpen(!open)}>
        <I.ChevRight size={16} className="chevron"/>
        <h2>Hidden playlists ({hidden.length})</h2>
      </div>
      {open && (
        <>
          <p className="accordion-help">
            Hidden playlists are excluded from sync and removed from the main grid. Unhide to bring them back.
          </p>
          <PlaylistGrid list={hidden} density={density} dimmed onToggleHide={onToggleHide} onToggleInclude={() => {}} />
        </>
      )}
    </div>
  );
}

Object.assign(window, { PlaylistCard, PlaylistGrid, HiddenAccordion, Cover });
