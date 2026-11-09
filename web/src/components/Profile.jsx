import {useEffect, useRef, useState} from 'react';
import {lang, locale, t} from '../lib/i18n.js';
import {ago} from '../lib/time.js';
import {dayKey, levelStart, stats} from '../lib/xp.js';
import {lessonPath, pct, store, useStore} from '../store.js';
import {AchievementRow, formatDate} from './Achievements.jsx';
import {Avatar, Topbar} from './Account.jsx';
import {BRANDS} from '../constants.js';
import {Icon, Logo, Meter, Ring} from './ui.jsx';

const WEEKS = 53;
const shade = xp => !xp ? 0 : xp < 25 ? 1 : xp < 75 ? 2 : xp < 150 ? 3 : 4;
const safeUrl = u => /^https?:\/\//i.test(u) ? u : 'https://' + u;

// XP per day for the last year, a column per week (Sunday on top), like GitHub's contribution graph.
function Heatmap({days}) {
  const scroller = useRef();
  useEffect(() => { scroller.current.scrollLeft = scroller.current.scrollWidth; }, []);  // narrow screens: show recent weeks
  const today = new Date(), start = new Date(today);
  start.setDate(today.getDate() - today.getDay() - 7 * (WEEKS - 1));
  const month = new Intl.DateTimeFormat(locale(), {month:'short'}), weekday = new Intl.DateTimeFormat(locale(), {weekday:'short'});
  const wd = n => weekday.format(new Date(2023, 0, 1 + n));  // 2023-01-01 was a Sunday
  const cells = [], months = [];
  for (let d = new Date(start), i = 0; d <= today; d.setDate(d.getDate() + 1), i++) {
    const key = dayKey(d), xp = days[key] || 0;
    if (d.getDate() === 1 || i === 0) months.push({col:Math.floor(i / 7) + 1, name:month.format(d)});
    cells.push(<span key={key} className={'day l' + shade(xp)} title={xp ? t('{n} XP on {date}', {n:xp, date:formatDate(key)}) : t('No activity on {date}', {date:formatDate(key)})}/>);
  }
  const active = Object.values(days).filter(Boolean).length;
  return (
    <section className="card heat-card" aria-label={t('Activity over the last year')}>
      <div className="card-head"><h2>{t('Activity')}</h2><span className="meta">{active === 1 ? t('{n} active day this year', {n:active}) : t('{n} active days this year', {n:active})}</span></div>
      <div className="heat-scroll" ref={scroller}>
        <div className="heat">
          <div className="heat-months" aria-hidden="true">
            {months.filter((m, i) => i === 0 || m.col - months[i - 1].col > 2).map(m => <span key={m.col} style={{gridColumn:m.col}}>{m.name}</span>)}
          </div>
          <div className="heat-days" aria-hidden="true"><span/><span>{wd(1)}</span><span/><span>{wd(3)}</span><span/><span>{wd(5)}</span><span/></div>
          <div className="heat-grid">{cells}</div>
        </div>
      </div>
      <div className="heat-legend" aria-hidden="true">{t('Less')}{[0, 1, 2, 3, 4].map(l => <span key={l} className={'day l' + l}/>)}{t('More')}</div>
    </section>
  );
}

const Stat = ({label, value, sub}) => (
  <div className="stat">
    <dt className="meta">{label}</dt>
    <dd><span className="stat-value">{value}</span>{sub && <span className="meta">{sub}</span>}</dd>
  </div>
);

// Every course they've started, furthest along first; finished ones at the end.
function Courses({list}) {
  const catalog = Object.fromEntries(store.catalog.courses.map(c => [c.slug, c]));
  const rows = list.filter(c => catalog[c.slug]).map(c => ({...c, course:catalog[c.slug], p:pct(c.done, c.total)}))
    .sort((a, b) => (a.p === 100) - (b.p === 100) || b.p - a.p);
  const finished = rows.filter(r => r.p === 100).length;
  return (
    <section className="card">
      <div className="card-head"><h2>{t('Courses')}</h2>
        <span className="meta">{t('{n} started · {done} finished', {n:rows.length, done:finished})}</span></div>
      {rows.length ? (
        <ul className="course-progress">
          {rows.map(r => (
            <li key={r.slug}><a href={lessonPath(r.slug)}>
              <Logo course={r.course} size="sm"/>
              <span className="cp-text">
                <span className="cp-title">{r.course.title}</span>
                <span className="cp-bar"><Meter n={r.done} total={r.total} label={r.course.title}/>
                  <span className="meta">{r.p === 100 ? <><Icon name="circle-check"/>{t('Finished')}</> : t('{n} / {total} · {pct}%', {n:r.done, total:r.total, pct:r.p})}</span></span>
              </span>
            </a></li>
          ))}
        </ul>
      ) : <p className="empty">{t('No courses started… {yet}.', {yet:<em>{t('yet')}</em>})}</p>}
    </section>
  );
}

// Lessons done per language, as a share of all their lessons.
function Languages({langs}) {
  const rows = Object.entries(langs).sort((a, b) => b[1] - a[1]), total = rows.reduce((n, [, v]) => n + v, 0);
  if (!rows.length) return null;
  return (
    <section className="card">
      <div className="card-head"><h2>{t('Languages')}</h2></div>
      <ul className="langs">
        {rows.map(([lang, n]) => (
          <li key={lang}>
            <Logo course={{slug:'', language:lang}} size="sm"/>
            <span className="lang-name">{BRANDS[lang]?.[2] || lang}</span>
            <span className="lang-bar"><span style={{width:`${100 * n / rows[0][1]}%`}}/></span>
            <span className="meta">{t('{n} lessons', {n})} · {pct(n, total)}%</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Recent({items}) {
  if (!items.length) return null;
  return (
    <section className="card">
      <div className="card-head"><h2>{t('Recent activity')}</h2></div>
      <ul className="recent">
        {items.slice(0, 6).map(r => (
          <li key={r.uuid}><a href={lessonPath(r.slug, r.uuid)}>
            <Icon name="circle-check"/>
            <span className="recent-title">{r.title}</span>
            <span className="meta recent-when" title={store.catalog.courses.find(c => c.slug === r.slug)?.title}>
              {r.at.length > 10 ? ago(Date.parse(r.at)) : formatDate(r.at)}</span>
          </a></li>
        ))}
      </ul>
    </section>
  );
}

// /profile is yours; /u/<id> is another member's, if they share it. Everything comes from the server's public view.
export default function Profile({id = 'me'}) {
  useStore();
  const [p, setP] = useState();
  const xp = stats().xp;
  useEffect(() => {
    let live = true;
    fetch(`/api/profile/${encodeURIComponent(id)}?lang=${lang()}`, {cache:'no-store'}).then(r => r.ok ? r.json() : null).then(d => live && setP(d));
    return () => { live = false; };
  }, [id, id === 'me' && xp, lang()]);
  const name = p && (p.name || (p.self ? t('You') : t('Learner')));
  useEffect(() => { if (name) document.title = `${name} · ${t('nagare')}`; }, [name]);

  if (p === undefined) return <main id="home" className="page"><Topbar/><p className="empty">{t('Loading…')}</p></main>;
  if (p === null) return <main id="home" className="page"><Topbar/><h1>{t('Profile not available')}</h1>
    <p className="path-desc">{t('This member hid their profile, or it doesn\'t exist.')}</p></main>;

  const from = levelStart(p.level), to = levelStart(p.level + 1);
  const unlocked = p.achievements.filter(a => a.unlocked).sort((a, b) => b.unlocked.localeCompare(a.unlocked));
  return (
    <main id="home" className="page">
      <Topbar/>
      <section className="card hero">
        {p.self ? <Avatar size={96}/> : <Avatar size={96} picture={p.picture} name={name}/>}
        <div className="hero-text">
          <h1>{name}</h1>
          <ul className="hero-meta">
            {p.handle && <li><Icon name="at-sign"/>{p.handle}</li>}
            {p.location && <li><Icon name="map-pin"/>{p.location}</li>}
            {p.website && <li><Icon name="link"/><a href={safeUrl(p.website)} rel="noopener noreferrer nofollow" target="_blank">{p.website.replace(/^https?:\/\//i, '')}</a></li>}
            {p.github && <li><svg className="icon gh" aria-hidden="true"><use href="/vendor/brands.svg?v=5#github"/></svg>
              <a href={`https://github.com/${encodeURIComponent(p.github)}`} rel="noopener noreferrer nofollow" target="_blank">{p.github}</a></li>}
          </ul>
          {p.bio && <p className="hero-bio">{p.bio}</p>}
          {p.self && <a className="btn ghost hero-edit" href="/settings"><Icon name="pen-line"/>{t('Edit profile')}</a>}
        </div>
        <div className="hero-level">
          <Ring n={p.xp - from} total={to - from} size={72} label={t('Progress to the next level')}><span className="level-num">{p.level}</span></Ring>
          <div className="level-text">
            <span className="level-title">{t('Level {n}', {n:p.level})}</span>
            <span className="meta">{t('{n} XP to level {next}', {n:(to - p.xp).toLocaleString(), next:p.level + 1})}</span>
            <span className="meta">{t('{n} / {total} XP', {n:p.xp.toLocaleString(), total:to.toLocaleString()})}</span>
          </div>
        </div>
      </section>

      <dl className="card stats">
        <Stat label={t('Lessons done')} value={p.lessons.toLocaleString()}/>
        <Stat label={t('XP earned')} value={p.xp.toLocaleString()}/>
        <Stat label={t('Streak')} value={p.streak === 1 ? t('{n} day', {n:p.streak}) : t('{n} days', {n:p.streak})} sub={t('Best: {n}', {n:p.best || 0})}/>
        <Stat label={t('Joined')} value={p.joined ? formatDate(p.joined) : '—'}/>
      </dl>

      <Heatmap days={p.days || {}}/>

      <div className="profile-cols">
        <div className="col">
          <Courses list={p.courses}/>
          <Recent items={p.recent}/>
        </div>
        <div className="col">
          <Languages langs={p.languages}/>
          <section className="card">
            <div className="card-head"><h2>{t('Achievements')}</h2>
              {p.self ? <a className="view-all" href="/achievements">{t('View all')}</a>
                : <span className="meta">{t('{n} of {total}', {n:unlocked.length, total:p.achievements.length})}</span>}</div>
            {unlocked.length ? <ul className="ach-list">{unlocked.slice(0, p.self ? 3 : 6).map(a => <AchievementRow key={a.id} a={a}/>)}</ul>
              : <p className="empty">{t('None unlocked… {yet}.', {yet:<em>{t('yet')}</em>})}</p>}
          </section>
        </div>
      </div>
    </main>
  );
}
