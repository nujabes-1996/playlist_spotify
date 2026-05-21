// AppShell, Sidebar, Topbar, and small primitives (Menu, dot, etc).

const { useState, useEffect, useRef } = React;

function useOutsideClick(ref, handler, enabled = true) {
  useEffect(() => {
    if (!enabled) return;
    const onDown = (e) => {
      if (ref.current && !ref.current.contains(e.target)) handler(e);
    };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, [enabled, handler]);
}

function Sidebar({ route, onNav, hiddenCount }) {
  const items = [
    { id: 'dashboard',  label: 'Dashboard',      icon: I.Dashboard },
    { id: 'recent',     label: 'Recently Added', icon: I.Recent },
    { id: 'settings',   label: 'Settings',       icon: I.Settings },
    { id: 'logs',       label: 'Logs',           icon: I.Logs },
  ];

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark"><I.Spotify size={18}/></div>
        <div className="brand-name">playlist<em>_</em>spotify</div>
      </div>

      <div className="nav-section-label">Workspace</div>
      <nav className="nav">
        {items.map(it => (
          <div key={it.id}
               className={'nav-item' + (route === it.id ? ' active' : '')}
               onClick={() => onNav(it.id)}>
            <it.icon size={17} />
            <span>{it.label}</span>
            {it.id === 'dashboard' && hiddenCount > 0 && <span className="nav-count">{hiddenCount} hidden</span>}
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="avatar-dot">YL</div>
        <div style={{ minWidth: 0, lineHeight: 1.3 }}>
          <div style={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: 12 }}>Connected as</div>
          <div style={{ color: 'var(--text-primary)', fontWeight: 700, fontSize: 13, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>yl@ouidou.fr</div>
          <div className="connection-status"><span className="status-dot"/>Token healthy · expires in 47m</div>
        </div>
      </div>
    </aside>
  );
}

function Topbar({ title, scrolled, onSync, syncing, lastSync, syncOk, showSearch }) {
  return (
    <div className={'topbar' + (scrolled ? ' scrolled' : '')}>
      <button className="topbar-nav-btn" disabled><I.ChevLeft size={16}/></button>
      <button className="topbar-nav-btn" disabled><I.ChevRight size={16}/></button>
      {showSearch && (
        <div className="topbar-search" style={{ marginLeft: 6 }}>
          <I.Search size={15}/>
          <input placeholder="Filter playlists…" />
        </div>
      )}
      <div className="topbar-spacer" />
      <div className="topbar-right">
        <div className={'sync-badge' + (syncOk ? '' : ' error')}>
          <span className="dot"/>
          <span>{syncOk ? 'Last sync' : 'Last sync failed'} · {lastSync}</span>
        </div>
        <button className="btn btn-primary" onClick={onSync} disabled={syncing}>
          {syncing ? <I.RotateCw size={14} className="spin"/> : <I.RotateCw size={14}/>}
          {syncing ? 'Syncing…' : 'Sync now'}
        </button>
      </div>
    </div>
  );
}

// Floating menu (portal-less, simple)
function Menu({ open, anchor, onClose, children, align = 'right' }) {
  const ref = useRef(null);
  useOutsideClick(ref, onClose, open);
  if (!open) return null;
  const rect = anchor?.getBoundingClientRect?.();
  if (!rect) return null;
  const top = rect.bottom + 6;
  const left = align === 'right' ? rect.right - 220 : rect.left;
  return ReactDOM.createPortal(
    <div ref={ref} className="menu" style={{ top, left, position: 'fixed' }} onClick={onClose}>
      {children}
    </div>,
    document.body
  );
}
function MenuItem({ icon: Ic, danger, onClick, children }) {
  return (
    <div className={'menu-item' + (danger ? ' danger' : '')} onClick={(e) => { e.stopPropagation(); onClick?.(e); }}>
      {Ic ? <Ic size={15}/> : null}
      <span>{children}</span>
    </div>
  );
}

// Spinner via CSS animation injection
(function injectSpin() {
  if (document.getElementById('spin-style')) return;
  const s = document.createElement('style');
  s.id = 'spin-style';
  s.textContent = `.spin{animation: spin 1s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}`;
  document.head.appendChild(s);
})();

Object.assign(window, { Sidebar, Topbar, Menu, MenuItem, useOutsideClick });
