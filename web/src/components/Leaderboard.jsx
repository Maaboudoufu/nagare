import {useState} from 'react';
import {N_, locale, t} from '../lib/i18n.js';
import {useFetch} from '../store.js';
import {Avatar, Page} from './Account.jsx';
import {Icon} from './ui.jsx';

const PERIODS = [
  ['week', N_('This week'), N_('Ranked by XP earned this week. Lessons, streaks and achievements all count.')],
  ['month', N_('This month'), N_('Ranked by XP earned this month. Lessons, streaks and achievements all count.')],
  ['all', N_('All time'), N_('Ranked by XP. Lessons, streaks and achievements all count.')],
];
// A row links to the member's profile, unless they've hidden it.
const Row = ({href, children}) => href ? <a className="lb-row" href={href}>{children}</a> : <div className="lb-row">{children}</div>;
const nameOf = r => r.name || (r.you ? t('You') : t('Learner'));

export default function Leaderboard() {
  const [period, setPeriod] = useState('week');
  const rows = useFetch(`/api/leaderboard?period=${period}`);
  const me = rows?.find(r => r.you);

  return (
    <Page title={t('Leaderboard')} className="narrow">
      <h1>{t('Leaderboard')}</h1>
      <p className="lede">{t(PERIODS.find(p => p[0] === period)[2])}</p>
      <div className="tabs" role="group" aria-label={t('Period')}>
        {PERIODS.map(([id, label]) => <button key={id} className="tab" aria-pressed={id === period} onClick={() => setPeriod(id)}>{t(label)}</button>)}
      </div>
      {me?.hidden && <p className="meta lb-note"><Icon name="eye-off"/>{t('Only you can see your row: you\'re hidden in {settings}.', {settings:<a href="/settings">{t('Settings')}</a>})}</p>}
      {rows === undefined ? <p className="empty">{t('Loading…')}</p> : !rows?.length ? <p className="empty">{t('Nobody has earned XP yet.')}</p> : (
        <ol className="lb">
          {rows.map(r => (
            <li key={r.id || r.rank} className={'lb-item' + (r.you ? ' you' : '') + (r.rank <= 3 ? ` top-${r.rank}` : '')}>
              <Row href={r.id && `/u/${r.id}`}>
                <span className="lb-rank">{r.rank}</span>
                <Avatar picture={r.picture} name={nameOf(r)}/>
                <span className="lb-name">{nameOf(r)}{r.you && r.name && <span className="meta"> {t('(you)')}</span>}
                  {r.handle && <span className="meta">@{r.handle}</span>}</span>
                <span className="lb-stat meta">{t('Lv {n}', {n:r.level})}</span>
                <span className="lb-stat meta" title={t('Lessons done')}><Icon name="circle-check"/>{r.lessons}</span>
                <span className="lb-stat meta" title={t('Current streak')}><Icon name="flame"/>{r.streak}</span>
                <span className="lb-xp">{t('{n} XP', {n:r.xp.toLocaleString(locale())})}</span>
              </Row>
            </li>
          ))}
        </ol>
      )}
    </Page>
  );
}
