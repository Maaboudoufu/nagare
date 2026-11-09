import {useEffect, useState} from 'react';
import {locale, t} from '../lib/i18n.js';
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

// A hexagon in the tier's metal, with the achievement's icon. Grey until unlocked.
export const Badge = ({a, size = 48}) => (
  <span className={`badge-hex tier-${a.unlocked ? a.tier : 'locked'}`} style={{width:size, height:size * 1.1}}>
    <Icon name={a.unlocked ? a.icon : 'lock'}/>
  </span>
);

export function AchievementRow({a}) {
  return (
    <li className={'ach' + (a.unlocked ? '' : ' locked')}>
      <Badge a={a}/>
      <div className="ach-text">
        <span className="ach-name">{t(a.name)} <span className={`tier-label tier-${a.tier}`}>{t(a.tier)}</span></span>
        <span className="meta">{t(a.description)}</span>
        {a.unlocked ? <span className="meta ach-date">{t('Unlocked {date}', {date:formatDate(a.unlocked)})}</span>
          : a.goal > 1 && <span className="ach-progress"><Meter n={a.value} total={a.goal} label={t('{name} progress', {name:t(a.name)})}/><span className="meta">{a.value}/{a.goal}</span></span>}
      </div>
    </li>
  );
}

export default function Achievements() {
  const list = useAchievements();
  useEffect(() => { document.title = `${t('Achievements')} · ${t('nagare')}`; }, []);
  const got = list?.filter(a => a.unlocked) || [];
  return (
    <main id="home" className="page">
      <Topbar/>
      <h1>{t('Achievements')}</h1>
      <p className="path-desc">{list ? t('{n} of {total} unlocked. Each one is worth bonus XP: bronze 25, silver 50, gold 100.', {n:got.length, total:list.length}) : t('Loading…')}</p>
      {list && (
        <ul className="ach-grid">
          {[...got.sort((a, b) => b.unlocked.localeCompare(a.unlocked)), ...list.filter(a => !a.unlocked)].map(a => <AchievementRow key={a.id} a={a}/>)}
        </ul>
      )}
    </main>
  );
}
