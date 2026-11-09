/* The signed-in person: avatar, the menu behind it, and the top bar every page shares. */
import {useEffect, useRef, useState} from 'react';
import {level, stats} from '../lib/xp.js';
import {profile, settings, signOut, store, useStore} from '../store.js';
import {Brand, Icon} from './ui.jsx';

export const displayName = () => profile().name || store.user?.name || store.user?.email.split('@')[0] || 'You';

// The Google profile photo, or the name's first letter if there isn't one (or it fails to load).
export function Avatar({size = 32}) {
  const [broken, setBroken] = useState(false);
  const pic = settings().photo && store.user?.picture;
  const style = {width:size, height:size, fontSize:size * .42};
  if (pic && !broken) return <img className="avatar" style={style} src={pic} alt="" referrerPolicy="no-referrer" onError={() => setBroken(true)}/>;
  return <span className="avatar" style={style} aria-hidden="true">{displayName()[0].toUpperCase()}</span>;
}

function AccountMenu() {
  useStore();
  const [open, setOpen] = useState(false);
  const ref = useRef();
  useEffect(() => {
    if (!open) return;
    const close = e => { if (e.type === 'keydown' ? e.key === 'Escape' : !ref.current.contains(e.target)) setOpen(false); };
    addEventListener('pointerdown', close);
    addEventListener('keydown', close);
    return () => { removeEventListener('pointerdown', close); removeEventListener('keydown', close); };
  }, [open]);
  const item = (href, icon, label) => <a role="menuitem" href={href} onClick={() => setOpen(false)}><Icon name={icon}/>{label}</a>;
  return (
    <div className="account" ref={ref}>
      <button className="account-btn" aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen(!open)}>
        <span className="level-chip" title={`${stats().xp.toLocaleString()} XP`}>Lv {level(stats().xp)}</span>
        <Avatar/>
        <span className="account-name">{displayName()}</span>
        <Icon name="chevron-down"/>
      </button>
      {open && (
        <div className="menu" role="menu">
          {item('/profile', 'user', 'Profile')}
          {item('/achievements', 'award', 'Achievements')}
          {item('/leaderboard', 'trophy', 'Leaderboard')}
          {item('/settings', 'settings', 'Settings')}
          {store.admin && item('/admin', 'shield', 'Admin')}
          {store.user && <><hr/><button role="menuitem" onClick={signOut}><Icon name="log-out"/>Sign out</button></>}
        </div>
      )}
    </div>
  );
}

export const Topbar = () => <div className="topbar"><Brand/><AccountMenu/></div>;
