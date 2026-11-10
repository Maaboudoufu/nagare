/* The signed-in person: avatar, the menu behind it, and the frame every page outside a lesson shares. */
import {useEffect, useRef, useState} from 'react';
import {LANGS, contentPct, lang, setLang, t} from '../lib/i18n.js';
import {level, levelStart, stats} from '../lib/xp.js';
import {profile, settings, signOut, store, useStore} from '../store.js';
import {Brand, Icon, Ring} from './ui.jsx';

const displayName = () => profile().name || store.user?.name || store.user?.email.split('@')[0] || t('You');

// The Google profile photo, or the name's first letter if there isn't one (or it fails to load).
// Yours by default; pass picture and name for someone else's.
export function Avatar({size = 32, picture, name}) {
  const [broken, setBroken] = useState(false);
  const self = picture === undefined;
  const pic = self ? settings().photo && store.user?.picture : picture;
  const label = (self ? displayName() : name) || '?';
  const style = {width:size, height:size, fontSize:size * .42};
  if (pic && !broken) return <img className="avatar" style={style} src={pic} alt="" referrerPolicy="no-referrer" onError={() => setBroken(true)}/>;
  return <span className="avatar" style={style} aria-hidden="true">{label[0].toUpperCase()}</span>;
}

// Open/closed state for a dropdown that closes on Escape or a click outside it.
function useMenu() {
  const [open, setOpen] = useState(false);
  const ref = useRef();
  useEffect(() => {
    if (!open) return;
    const close = e => { if (e.type === 'keydown' ? e.key === 'Escape' : !ref.current.contains(e.target)) setOpen(false); };
    addEventListener('pointerdown', close);
    addEventListener('keydown', close);
    return () => { removeEventListener('pointerdown', close); removeEventListener('keydown', close); };
  }, [open]);
  return [open, setOpen, ref];
}

// Globe button with the UI languages. Language names stay in their own language.
export function LangMenu() {
  useStore();
  const [open, setOpen, ref] = useMenu();
  const cur = lang();
  if (LANGS.length < 2) return null;
  return (
    <div className="lang-menu" ref={ref}>
      <button className="icon-btn" aria-label={t('Language')} title={t('Language')} aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen(!open)}>
        <Icon name="globe"/>
      </button>
      {open && (
        <div className="menu" role="menu">
          {LANGS.map(([code, name]) => (
            <button key={code} role="menuitemradio" aria-checked={code === cur} lang={code} onClick={() => { setLang(code); setOpen(false); }}>
              <Icon name="check" cls={code === cur ? '' : 'off'}/>{name}
              {code !== 'en' && <span className="menu-meta" title={t('{pct}% of lessons translated', {pct:contentPct(code)})}>{contentPct(code)}%</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function AccountMenu() {
  useStore();
  const [open, setOpen, ref] = useMenu();
  const xp = stats().xp, lvl = level(xp);
  const item = (href, icon, label) => <a role="menuitem" href={href} onClick={() => setOpen(false)}><Icon name={icon}/>{label}</a>;
  return (
    <div className="account" ref={ref}>
      <button className="account-btn" aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen(!open)}>
        <span className="level-chip">{t('Lv {n}', {n:lvl})}</span>
        <Ring n={xp - levelStart(lvl)} total={levelStart(lvl + 1) - levelStart(lvl)} size={38} stroke={2}><Avatar/></Ring>
        <span className="account-name">{displayName()}</span>
        <Icon name="chevron-down"/>
      </button>
      {open && (
        <div className="menu" role="menu">
          {item('/profile', 'user', t('Profile'))}
          {item('/achievements', 'award', t('Achievements'))}
          {item('/leaderboard', 'trophy', t('Leaderboard'))}
          {item('/settings', 'settings', t('Settings'))}
          {store.admin && item('/admin', 'shield', t('Admin'))}
          {store.user && <><hr/><button role="menuitem" onClick={signOut}><Icon name="log-out"/>{t('Sign out')}</button></>}
        </div>
      )}
    </div>
  );
}

// A page: the top bar, then its content. title also names the browser tab.
export function Page({title, className = '', children}) {
  useEffect(() => { if (title) document.title = `${title} · ${t('nagare')}`; }, [title]);
  return (
    <main className={'page ' + className}>
      <div className="topbar"><Brand/><div className="topbar-end"><LangMenu/><AccountMenu/></div></div>
      {children}
    </main>
  );
}
