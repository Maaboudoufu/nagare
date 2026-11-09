import {useEffect, useState} from 'react';
import {N_, locale, t} from '../lib/i18n.js';
import {stats} from '../lib/xp.js';
import {useStore} from '../store.js';
import {Topbar} from './Account.jsx';
import {Icon, Meter} from './ui.jsx';

export const formatDate = iso => new Date(iso.length === 10 ? iso + 'T12:00' : iso).toLocaleDateString(locale(), {month:'short', day:'numeric', year:'numeric'});

// Every achievement with this user's progress toward it; fetched again whenever they earn XP.
export function useAchievements() {
  useStore();
  const [list, setList] = useState(null);
  const xp = stats().xp;
  useEffect(() => {
    let live = true;
    fetch('/api/achievements', {cache:'no-store'}).then(r => r.json()).then(l => live && setList(l));
    return () => { live = false; };
  }, [xp]);
  return list;
}

const TIER_XP = {bronze:25, silver:50, gold:100};
const TIERS = {bronze:N_('Bronze'), silver:N_('Silver'), gold:N_('Gold')};

// The achievement's icon on a plain tile; its border takes the tier's color once unlocked.
export const Badge = ({a, size = 40}) => (
  <span className={'ach-tile' + (a.unlocked ? ` tier-${a.tier}` : ' locked')} style={{width:size, height:size}}>
    <Icon name={a.icon}/>
  </span>
);

export function AchievementRow({a}) {
  return (
    <li className={'ach' + (a.unlocked ? '' : ' locked')}>
      <Badge a={a}/>
      <div className="ach-text">
        <span className="ach-name">{t(a.name)}</span>
        <span className="meta">{t(a.description)}</span>
        <span className="ach-tier"><span className={`tier-dot tier-${a.tier}`} aria-hidden="true"/>{t('{tier} · {xp} XP', {tier:t(TIERS[a.tier]), xp:TIER_XP[a.tier]})}</span>
      </div>
      <div className="ach-side">
        {a.unlocked ? <span className="meta">{formatDate(a.unlocked)}</span> : a.goal > 1 && <>
          <span className="meta">{t('{n} / {total}', {n:a.value, total:a.goal})}</span>
          <Meter n={a.value} total={a.goal} label={t('{name} progress', {name:t(a.name)})}/>
        </>}
      </div>
    </li>
  );
}

export default function Achievements() {
  const list = useAchievements();
  useEffect(() => { document.title = `${t('Achievements')} · ${t('nagare')}`; }, []);
  const got = (list || []).filter(a => a.unlocked).sort((a, b) => b.unlocked.localeCompare(a.unlocked));
  const left = (list || []).filter(a => !a.unlocked).sort((a, b) => b.value / b.goal - a.value / a.goal);  // closest first
  const group = (title, items) => items.length > 0 && (
    <section className="card ach-group">
      <div className="card-head"><h2>{title}</h2><span className="meta">{items.length}</span></div>
      <ul className="ach-list">{items.map(a => <AchievementRow key={a.id} a={a}/>)}</ul>
    </section>
  );
  return (
    <main id="home" className="page achievements">
      <Topbar/>
      <h1>{t('Achievements')}</h1>
      <p className="path-desc">{list ? t('{n} of {total} unlocked. Each one is worth bonus XP: bronze 25, silver 50, gold 100.', {n:got.length, total:list.length}) : t('Loading…')}</p>
      {group(t('Unlocked'), got)}
      {group(t('Locked'), left)}
    </main>
  );
}
