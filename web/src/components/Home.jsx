import {useEffect, useState} from 'react';
import {lang, locale, t} from '../lib/i18n.js';
import {currentPath, pathCourses, paths} from '../paths.js';
import {isDone, lessonPath, pct, save, store, useStore} from '../store.js';
import {Topbar} from './Account.jsx';
import CustomPicker from './CustomPicker.jsx';
import Resume from './Resume.jsx';
import {Icon, Logo, Meter} from './ui.jsx';

export default function Home() {
  useStore();
  const [picking, setPicking] = useState(false);
  const path = currentPath(), list = pathCourses(path);
  useEffect(() => { document.title = `${path.title} · ${t('nagare')}`; }, [path.title, lang()]);
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
    <main id="home">
      <header>
        <Topbar/>
        <div className="path-tabs" role="group" aria-label={t('Learning path')}>
          {paths().map(p => (
            <button key={p.id} className="path-tab" aria-pressed={p.id === path.id} onClick={() => choose(p.id)}>{p.short}</button>
          ))}
        </div>
        <h1>{path.title}</h1>
        {path.description && <p className="path-desc">{path.description}</p>}
        {path.id === 'custom' && <button className="btn" id="edit-custom" onClick={() => setPicking(true)}><Icon name="pen-line"/>{t('Edit courses')}</button>}
        {list.length > 0 && (
          <div className="home-progress">
            <Meter n={done} total={total} label={t('Path progress')}/>
            <p className="meta">{t('{done} of {total} lessons · {pct}%', {done:<strong>{done.toLocaleString(locale())}</strong>, total:total.toLocaleString(locale()), pct:pct(done, total)})}</p>
          </div>
        )}
        <Resume list={list}/>
      </header>
      <h2 className="section-title">{list.length === 1 ? t('{n} course', {n:list.length}) : t('{n} courses', {n:list.length})}</h2>
      {!list.length && <p className="meta">{t('No courses in your custom path yet. Use {edit} to pick some.', {edit:<strong>{t('Edit courses')}</strong>})}</p>}
      <ol className="course-grid">
        {list.map((c, i) => {
          const d = c.lessons.filter(isDone).length, complete = d === c.lessons.length;
          return (
            <li key={c.slug}><a className={'course-card' + (complete ? ' complete' : '')} href={lessonPath(c.slug)}>
              <div className="card-top">
                <Logo course={c}/><span className="card-num">{String(i + 1).padStart(2, '0')}</span>
                {complete && <span className="badge"><Icon name="circle-check"/>{t('Done')}</span>}
              </div>
              <h3>{c.title}</h3>
              <p>{c.description}</p>
              <div className="card-foot">
                <Meter n={d} total={c.lessons.length} hidden/>
                <span className="meta"><span aria-hidden="true">{d}/{c.lessons.length}</span><span className="sr">{t('{n} of {total} lessons complete', {n:d, total:c.lessons.length})}</span></span>
              </div>
            </a></li>
          );
        })}
      </ol>
      {picking && <CustomPicker onClose={closePicker}/>}
    </main>
  );
}
