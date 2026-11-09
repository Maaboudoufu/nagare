import {useEffect, useState} from 'react';
import {stats} from '../lib/xp.js';
import {useStore} from '../store.js';
import {Topbar} from './Account.jsx';
import {Icon, Meter} from './ui.jsx';

export const formatDate = iso => new Date(iso.length === 10 ? iso + 'T12:00' : iso).toLocaleDateString(undefined, {month:'short', day:'numeric', year:'numeric'});

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
        <span className="ach-name">{a.name} <span className={`tier-label tier-${a.tier}`}>{a.tier}</span></span>
        <span className="meta">{a.description}</span>
        {a.unlocked ? <span className="meta ach-date">Unlocked {formatDate(a.unlocked)}</span>
          : a.goal > 1 && <span className="ach-progress"><Meter n={a.value} total={a.goal} label={`${a.name} progress`}/><span className="meta">{a.value}/{a.goal}</span></span>}
      </div>
    </li>
  );
}

export default function Achievements() {
  const list = useAchievements();
  useEffect(() => { document.title = 'Achievements · nagare'; }, []);
  const got = list?.filter(a => a.unlocked) || [];
  return (
    <main id="home" className="page">
      <Topbar/>
      <h1>Achievements</h1>
      <p className="path-desc">{list ? `${got.length} of ${list.length} unlocked. Each one is worth bonus XP: bronze 25, silver 50, gold 100.` : 'Loading…'}</p>
      {list && (
        <ul className="ach-grid">
          {[...got.sort((a, b) => b.unlocked.localeCompare(a.unlocked)), ...list.filter(a => !a.unlocked)].map(a => <AchievementRow key={a.id} a={a}/>)}
        </ul>
      )}
    </main>
  );
}
