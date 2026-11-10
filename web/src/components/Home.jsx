import {useState} from 'react';
import {locale, t} from '../lib/i18n.js';
import {currentPath, pathCourses, paths} from '../paths.js';
import {isDone, lessonPath, pct, save, store, useStore} from '../store.js';
import {Page} from './Account.jsx';
import CustomPicker from './CustomPicker.jsx';
import Resume from './Resume.jsx';
import {Icon, Logo, Meter, Ring} from './ui.jsx';

// One course on the path. Its node on the line shows how far along you are: empty, a filling ring, then a check.
function Course({course: c}) {
  const done = c.lessons.filter(isDone).length, total = c.lessons.length, complete = done === total;
  return (
    <li className={complete ? 'complete' : ''}>
      <a className="course" href={lessonPath(c.slug)}>
        <span className="node">{complete ? <Icon name="check"/> : <Ring n={done} total={total} size={18} stroke={2}/>}</span>
        <Logo course={c}/>
        <span className="course-text">
          <span className="course-name">{c.title}</span>
          <span className="course-desc">{c.description}</span>
        </span>
        <span className="course-count" aria-hidden="true">{complete ? t('Done') : `${done}/${total}`}</span>
        <span className="sr">{t('{n} of {total} lessons complete', {n:done, total})}</span>
      </a>
    </li>
  );
}

export default function Home() {
  useStore();
  const [picking, setPicking] = useState(false);
  const path = currentPath(), list = pathCourses(path);
  const total = list.reduce((n, c) => n + c.lessons.length, 0);
  const done = list.reduce((n, c) => n + c.lessons.filter(isDone).length, 0);

  const choose = id => {
    const data = {id};
    // First time on Custom: start from the path you were on, so there's something to edit.
    if (id === 'custom' && !store.progress['app:path']?.custom) data.custom = pathCourses(currentPath()).map(c => c.slug);
    save('app:path', data);
    if (id === 'custom' && !pathCourses(currentPath()).length) setPicking(true);
  };
  const closePicker = () => { setPicking(false); setTimeout(() => document.getElementById('edit-custom')?.focus()); };

  return (
    <Page title={path.title} className="home">
      <div className="tabs" role="group" aria-label={t('Learning path')}>
        {paths().map(p => <button key={p.id} className="tab" aria-pressed={p.id === path.id} onClick={() => choose(p.id)}>{p.short}</button>)}
      </div>
      <header className="path-head">
        <div className="path-intro">
          <h1>{path.title}</h1>
          {path.description && <p className="lede">{path.description}</p>}
          {path.id === 'custom' && <button className="btn" id="edit-custom" onClick={() => setPicking(true)}><Icon name="pen-line"/>{t('Edit courses')}</button>}
          {list.length > 0 && (
            <div className="path-progress">
              <Meter n={done} total={total} label={t('Path progress')}/>
              <p className="meta">{t('{done} of {total} lessons · {pct}%', {done:<strong>{done.toLocaleString(locale())}</strong>, total:total.toLocaleString(locale()), pct:pct(done, total)})}</p>
            </div>
          )}
        </div>
        <Resume list={list}/>
      </header>
      <h2 className="stream-title">{list.length === 1 ? t('{n} course', {n:list.length}) : t('{n} courses', {n:list.length})}</h2>
      {list.length
        ? <ol className="stream">{list.map(c => <Course key={c.slug} course={c}/>)}</ol>
        : <p className="meta">{t('No courses in your custom path yet. Use {edit} to pick some.', {edit:<strong>{t('Edit courses')}</strong>})}</p>}
      {picking && <CustomPicker onClose={closePicker}/>}
    </Page>
  );
}
