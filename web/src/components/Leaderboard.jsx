import {useEffect, useState} from 'react';
import {N_, lang, t} from '../lib/i18n.js';
import {Topbar} from './Account.jsx';
import {Icon} from './ui.jsx';

const PERIODS = [
  ['week', N_('This week'), N_('Ranked by XP earned this week. Lessons, streaks and achievements all count.')],
  ['month', N_('This month'), N_('Ranked by XP earned this month. Lessons, streaks and achievements all count.')],
  ['all', N_('All time'), N_('Ranked by XP. Lessons, streaks and achievements all count.')],
];
// A row links to the member's profile, unless they've hidden it.
const Row = ({href, children}) => href ? <a className="lb-row" href={href}>{children}</a> : <div className="lb-row">{children}</div>;
const nameOf = r => r.name || (r.you ? t('You') : t('Learner'));

const Face = ({row}) => row.picture
  ? <img className="avatar" src={row.picture} alt="" referrerPolicy="no-referrer"/>
  : <span className="avatar" aria-hidden="true">{nameOf(row)[0].toUpperCase()}</span>;

export default function Leaderboard() {
  const [period, setPeriod] = useState('week');
  const [rows, setRows] = useState(null);
  useEffect(() => { document.title = `${t('Leaderboard')} · ${t('nagare')}`; }, [lang()]);
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
      <h1>{t('Leaderboard')}</h1>
      <p className="path-desc">{t(PERIODS.find(p => p[0] === period)[2])}</p>
      <div className="path-tabs" role="group" aria-label={t('Period')}>
        {PERIODS.map(([id, label]) => <button key={id} className="path-tab" aria-pressed={id === period} onClick={() => setPeriod(id)}>{t(label)}</button>)}
      </div>
      {me?.hidden && <p className="meta lb-note"><Icon name="eye-off"/>{t('Only you can see your row: you\'re hidden in {settings}.', {settings:<a href="/settings">{t('Settings')}</a>})}</p>}
      {!rows ? <p className="empty">{t('Loading…')}</p> : !rows.length ? <p className="empty">{t('Nobody has earned XP yet.')}</p> : (
        <ol className="card lb">
          {rows.map(r => (
            <li key={r.rank + r.name} className={'lb-item' + (r.you ? ' you' : '') + (r.rank <= 3 ? ` top top-${r.rank}` : '')}>
              <Row href={r.id && `/u/${r.id}`}>
              <span className="lb-rank">{r.rank}</span>
              <Face row={r}/>
              <span className="lb-name">{nameOf(r)}{r.you && r.name && <span className="meta"> {t('(you)')}</span>}
                {r.handle && <span className="meta">@{r.handle}</span>}</span>
              <span className="level-chip">{t('Lv {n}', {n:r.level})}</span>
              <span className="lb-stat meta" title={t('Lessons done')}><Icon name="circle-check"/>{r.lessons}</span>
              <span className="lb-stat meta" title={t('Current streak')}><Icon name="flame"/>{r.streak}</span>
              <span className="lb-xp">{t('{n} XP', {n:r.xp.toLocaleString()})}</span>
              </Row>
            </li>
          ))}
        </ol>
      )}
    </main>
  );
}
