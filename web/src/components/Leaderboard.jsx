import {useEffect, useState} from 'react';
import {Topbar} from './Account.jsx';
import {Icon} from './ui.jsx';

const PERIODS = [['week', 'This week'], ['month', 'This month'], ['all', 'All time']];

const Face = ({row}) => row.picture
  ? <img className="avatar" src={row.picture} alt="" referrerPolicy="no-referrer"/>
  : <span className="avatar" aria-hidden="true">{row.name[0].toUpperCase()}</span>;

export default function Leaderboard() {
  const [period, setPeriod] = useState('week');
  const [rows, setRows] = useState(null);
  useEffect(() => { document.title = 'Leaderboard · nagare'; }, []);
  useEffect(() => {
    let live = true;
    setRows(null);
    fetch(`/api/leaderboard?period=${period}`, {cache:'no-store'}).then(r => r.json()).then(r => live && setRows(r));
    return () => { live = false; };
  }, [period]);
  const me = rows?.find(r => r.you);

  return (
    <main id="home" className="page leaderboard">
      <Topbar/>
      <h1>Leaderboard</h1>
      <p className="path-desc">Ranked by XP{period === 'all' ? '' : ` earned ${PERIODS.find(p => p[0] === period)[1].toLowerCase()}`}. Lessons, streaks and achievements all count.</p>
      <div className="path-tabs" role="group" aria-label="Period">
        {PERIODS.map(([id, label]) => <button key={id} className="path-tab" aria-pressed={id === period} onClick={() => setPeriod(id)}>{label}</button>)}
      </div>
      {me?.hidden && <p className="meta lb-note"><Icon name="eye-off"/>Only you can see your row: you're hidden in <a href="/settings">Settings</a>.</p>}
      {!rows ? <p className="empty">Loading…</p> : !rows.length ? <p className="empty">Nobody has earned XP yet.</p> : (
        <ol className="card lb">
          {rows.map(r => (
            <li key={r.rank + r.name} className={'lb-row' + (r.you ? ' you' : '') + (r.rank <= 3 ? ` top top-${r.rank}` : '')}>
              <span className="lb-rank">{r.rank}</span>
              <Face row={r}/>
              <span className="lb-name">{r.name}{r.you && <span className="meta"> (you)</span>}
                {r.handle && <span className="meta">@{r.handle}</span>}</span>
              <span className="level-chip">Lv {r.level}</span>
              <span className="lb-stat meta" title="Lessons done"><Icon name="circle-check"/>{r.lessons}</span>
              <span className="lb-stat meta" title="Current streak"><Icon name="flame"/>{r.streak}</span>
              <span className="lb-xp">{r.xp.toLocaleString()} XP</span>
            </li>
          ))}
        </ol>
      )}
    </main>
  );
}
