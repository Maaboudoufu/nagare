import {useEffect, useRef} from 'react';
import {currentStreak, dayKey, level, levelStart, stats} from '../lib/xp.js';
import {isDone, lessonPath, profile, store, useStore} from '../store.js';
import {AchievementRow, formatDate, useAchievements} from './Achievements.jsx';
import {Avatar, displayName, Topbar} from './Account.jsx';
import {Icon, Logo, Meter} from './ui.jsx';

const WEEKS = 53;
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const shade = xp => !xp ? 0 : xp < 25 ? 1 : xp < 75 ? 2 : xp < 150 ? 3 : 4;
const safeUrl = u => /^https?:\/\//i.test(u) ? u : 'https://' + u;

// XP per day for the last year, a column per week (Sunday on top), like GitHub's contribution graph.
function Heatmap({days}) {
  const scroller = useRef();
  useEffect(() => { scroller.current.scrollLeft = scroller.current.scrollWidth; }, []);  // narrow screens: show recent weeks
  const today = new Date(), start = new Date(today);
  start.setDate(today.getDate() - today.getDay() - 7 * (WEEKS - 1));
  const cells = [], months = [];
  for (let d = new Date(start), i = 0; d <= today; d.setDate(d.getDate() + 1), i++) {
    const key = dayKey(d), xp = days[key] || 0;
    if (d.getDate() === 1 || i === 0) months.push({col:Math.floor(i / 7) + 1, name:MONTHS[d.getMonth()]});
    cells.push(<span key={key} className={'day l' + shade(xp)} title={`${xp ? xp + ' XP' : 'No activity'} on ${formatDate(key)}`}/>);
  }
  const active = Object.values(days).filter(Boolean).length;
  return (
    <section className="card heat-card" aria-label="Activity over the last year">
      <div className="card-head"><h2>Activity</h2><span className="meta">{active} active day{active === 1 ? '' : 's'} this year</span></div>
      <div className="heat-scroll" ref={scroller}>
        <div className="heat">
          <div className="heat-months" aria-hidden="true">
            {months.filter((m, i) => i === 0 || m.col - months[i - 1].col > 2).map(m => <span key={m.col} style={{gridColumn:m.col}}>{m.name}</span>)}
          </div>
          <div className="heat-days" aria-hidden="true"><span/><span>Mon</span><span/><span>Wed</span><span/><span>Fri</span><span/></div>
          <div className="heat-grid">{cells}</div>
        </div>
      </div>
      <div className="heat-legend" aria-hidden="true">Less{[0, 1, 2, 3, 4].map(l => <span key={l} className={'day l' + l}/>)}More</div>
    </section>
  );
}

const Stat = ({icon, label, value, sub}) => (
  <div className="card stat">
    <span className="stat-label">{label}<Icon name={icon}/></span>
    <span className="stat-value">{value}</span>
    {sub && <span className="meta">{sub}</span>}
  </div>
);

function CourseList({title, courses, empty}) {
  return (
    <section className="card">
      <div className="card-head"><h2>{title}</h2><span className="meta">{courses.length}</span></div>
      {courses.length ? (
        <ul className="done-list">
          {courses.map(c => <li key={c.slug}><a href={lessonPath(c.slug)}><Logo course={c} size="sm"/>{c.title}</a></li>)}
        </ul>
      ) : <p className="empty">{empty}</p>}
    </section>
  );
}

export default function Profile() {
  useStore();
  const achievements = useAchievements();
  useEffect(() => { document.title = `${displayName()} · nagare`; }, []);
  const s = stats(), p = profile(), lvl = level(s.xp), from = levelStart(lvl), to = levelStart(lvl + 1);
  const lessons = Object.keys(store.progress).filter(isDone).length;
  const finished = store.catalog.courses.filter(c => c.lessons.length && c.lessons.every(isDone));
  const recent = (achievements || []).filter(a => a.unlocked).sort((a, b) => b.unlocked.localeCompare(a.unlocked)).slice(0, 3);
  const streak = currentStreak(s);

  return (
    <main id="home" className="page">
      <Topbar/>
      <section className="card hero">
        <Avatar size={96}/>
        <div className="hero-text">
          <h1>{displayName()}</h1>
          <ul className="hero-meta">
            {p.handle && <li><Icon name="at-sign"/>{p.handle}</li>}
            {p.location && <li><Icon name="map-pin"/>{p.location}</li>}
            {p.website && <li><Icon name="link"/><a href={safeUrl(p.website)} rel="noopener noreferrer" target="_blank">{p.website.replace(/^https?:\/\//i, '')}</a></li>}
            {p.github && <li><svg className="icon gh" aria-hidden="true"><use href="/vendor/brands.svg?v=4#github"/></svg>
              <a href={`https://github.com/${encodeURIComponent(p.github)}`} rel="noopener noreferrer" target="_blank">{p.github}</a></li>}
          </ul>
          {p.bio && <p className="hero-bio">{p.bio}</p>}
          <a className="btn ghost hero-edit" href="/settings"><Icon name="pen-line"/>Edit profile</a>
        </div>
        <div className="hero-level">
          <span className="stat-label">Level</span>
          <span className="level-num">{lvl}</span>
          <Meter n={s.xp - from} total={to - from} label="Progress to the next level"/>
          <span className="meta level-range"><span>{s.xp.toLocaleString()} XP</span><span>{to.toLocaleString()} XP</span></span>
        </div>
      </section>

      <div className="stats">
        <Stat icon="circle-check" label="Lessons done" value={lessons.toLocaleString()}/>
        <Stat icon="trending-up" label="XP earned" value={s.xp.toLocaleString()}/>
        <Stat icon="flame" label="Streak" value={`${streak} day${streak === 1 ? '' : 's'}`} sub={`Best: ${s.best || 0}`}/>
        <Stat icon="calendar" label="Joined" value={s.joined ? formatDate(s.joined) : '—'}/>
      </div>

      <Heatmap days={s.days || {}}/>

      <div className="profile-cols">
        <div className="col">
          <CourseList title="Courses completed" courses={finished.filter(c => !c.slug.startsWith('build-'))} empty={<>No finished courses… <em>yet</em>.</>}/>
          <CourseList title="Projects completed" courses={finished.filter(c => c.slug.startsWith('build-'))} empty={<>No finished projects… <em>yet</em>.</>}/>
        </div>
        <section className="card">
          <div className="card-head"><h2>Achievements</h2><a className="view-all" href="/achievements">View all</a></div>
          {recent.length ? <ul className="ach-list">{recent.map(a => <AchievementRow key={a.id} a={a}/>)}</ul>
            : <p className="empty">{achievements ? <>None unlocked… <em>yet</em>.</> : 'Loading…'}</p>}
        </section>
      </div>
    </main>
  );
}
