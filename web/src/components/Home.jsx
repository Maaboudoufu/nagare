import {useEffect, useState} from 'react';
import {currentPath, pathCourses, paths} from '../paths.js';
import {isDone, lessonPath, pct, save, signOut, store, useStore} from '../store.js';
import CustomPicker from './CustomPicker.jsx';
import {Brand, Icon, Logo, Meter} from './ui.jsx';

function resumeLink(list, done) {
  const last = store.progress['app:last'];
  const started = list.find(c => c.lessons.some(isDone) && !c.lessons.every(isDone));
  const next = started || list.find(c => !c.lessons.every(isDone));
  if (last && list.some(c => c.slug === last.slug))
    return {href:lessonPath(last.slug, last.uuid), label:'Continue where you left off', title:last.title, sub:last.course};
  if (started)
    return {href:lessonPath(started.slug), label:'Continue', title:started.title,
            sub:`${started.lessons.filter(isDone).length} of ${started.lessons.length} lessons done`};
  if (next) return {href:lessonPath(next.slug), label:done ? 'Up next' : 'Start the path', title:next.title, sub:`Course ${list.indexOf(next) + 1}`};
  return null;
}

// The Google profile photo, or the name's first letter if there isn't one (or it fails to load).
function Avatar({user}) {
  const [broken, setBroken] = useState(false);
  if (user.picture && !broken)
    return <img className="avatar" src={user.picture} alt="" referrerPolicy="no-referrer" onError={() => setBroken(true)}/>;
  return <span className="avatar" aria-hidden="true">{(user.name || user.email)[0].toUpperCase()}</span>;
}

export default function Home() {
  useStore();
  const [picking, setPicking] = useState(false);
  const path = currentPath(), list = pathCourses(path);
  useEffect(() => { document.title = `${path.title} · nagare`; }, [path.title]);
  const total = list.reduce((n, c) => n + c.lessons.length, 0);
  const done = list.reduce((n, c) => n + c.lessons.filter(isDone).length, 0);
  const resume = resumeLink(list, done);

  const choose = id => {
    const data = {id};
    // First time on Custom: start from the path you were on, so there's something to edit.
    if (id === 'custom' && !store.progress['app:path']?.custom) data.custom = pathCourses(currentPath()).map(c => c.slug);
    save('app:path', data);
    if (id === 'custom' && !pathCourses(currentPath()).length) setPicking(true);
  };
  const closePicker = () => { setPicking(false); setTimeout(() => document.getElementById('edit-custom')?.focus()); };

  return (
    <main id="home">
      <header>
        <div className="topbar">
          <Brand/>
          {store.user && (
          <div className="account">
            <Avatar user={store.user}/>
            <span className="account-name">{store.user.name || store.user.email.split('@')[0]}</span>
            <button className="btn ghost" onClick={signOut}>Sign out</button>
          </div>
          )}
        </div>
        <div className="path-tabs" role="group" aria-label="Learning path">
          {paths().map(p => (
            <button key={p.id} className="path-tab" aria-pressed={p.id === path.id} onClick={() => choose(p.id)}>{p.short}</button>
          ))}
        </div>
        <h1>{path.title}</h1>
        {path.description && <p className="path-desc">{path.description}</p>}
        {path.id === 'custom' && <button className="btn" id="edit-custom" onClick={() => setPicking(true)}><Icon name="pen-line"/>Edit courses</button>}
        {list.length > 0 && (
          <div className="home-progress">
            <Meter n={done} total={total} label="Path progress"/>
            <p className="meta"><strong>{done.toLocaleString()}</strong> of {total.toLocaleString()} lessons · {pct(done, total)}%</p>
          </div>
        )}
        {resume ? (
          <a className="resume" href={resume.href}>
            <span className="resume-icon"><Icon name="play"/></span>
            <span className="resume-text">
              <span className="resume-label">{resume.label}</span>
              <span className="resume-title">{resume.title}</span><span className="meta">{resume.sub}</span>
            </span>
            <Icon name="chevron-right" cls="resume-chev"/>
          </a>
        ) : <div className="resume-gap"></div>}
      </header>
      <h2 className="section-title">{list.length} course{list.length === 1 ? '' : 's'}</h2>
      {!list.length && <p className="meta">No courses in your custom path yet. Use <strong>Edit courses</strong> to pick some.</p>}
      <ol className="course-grid">
        {list.map((c, i) => {
          const d = c.lessons.filter(isDone).length, complete = d === c.lessons.length;
          return (
            <li key={c.slug}><a className={'course-card' + (complete ? ' complete' : '')} href={lessonPath(c.slug)}>
              <div className="card-top">
                <Logo course={c}/><span className="card-num">{String(i + 1).padStart(2, '0')}</span>
                {complete && <span className="badge"><Icon name="circle-check"/>Done</span>}
              </div>
              <h3>{c.title}</h3>
              <p>{c.description}</p>
              <div className="card-foot">
                <Meter n={d} total={c.lessons.length} hidden/>
                <span className="meta">{d}/{c.lessons.length}<span className="sr"> lessons complete</span></span>
              </div>
            </a></li>
          );
        })}
      </ol>
      {picking && <CustomPicker onClose={closePicker}/>}
    </main>
  );
}
