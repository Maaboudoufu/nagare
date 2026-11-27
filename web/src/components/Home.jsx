import {useState} from 'react';
import {locale, t} from '../lib/i18n.js';
import {currentPath, pathCourses, paths} from '../paths.js';
import {isDone, lessonPath, pct, save, store, useStore} from '../store.js';
import {Page} from './Account.jsx';
import CustomPicker from './CustomPicker.jsx';
import Resume from './Resume.jsx';
import {Beta, BrandIcon, Icon, Logo, Meter, Ring, TechMark} from './ui.jsx';
import {BRANDS, PATH_STACKS, brandOf} from '../constants.js';
import AsciiWave from './AsciiWave.jsx';
import Shortcuts from './Shortcuts.jsx';

// One course on the path. Its node on the line shows how far along you are: empty, a filling ring, then a check.
function Course({course: c}) {
  const done = c.lessons.filter(isDone).length, total = c.lessons.length, complete = done === total;
  return (
    <li className={complete ? 'complete' : ''}>
      <a className="course" href={lessonPath(c.slug)}>
        <span className="node">{complete ? <Icon name="check"/> : <Ring n={done} total={total} size={18} stroke={2}/>}</span>
        <Logo course={c}/>
        <span className="course-text">
          <span className="course-name">{c.title}{c.beta && <Beta/>}</span>
          <span className="course-desc">{c.description}</span>
        </span>
        <span className="course-count" aria-hidden="true">{complete ? t('Done') : `${done}/${total}`}</span>
        <span className="sr">{t('{n} of {total} lessons complete', {n:done, total})}</span>
      </a>
    </li>
  );
}

// The path's three main technologies, by how many of its courses use each (lessons break ties). Projects don't count.
// None for All courses: it's every technology.
function topStacks(path, list) {
  if (path.id === 'all') return [];
  if (PATH_STACKS[path.id]) return PATH_STACKS[path.id].map(k => BRANDS[k]);
  const by = new Map();
  for (const c of list) {
    const b = brandOf(c);
    if (b === BRANDS.any) continue;
    const e = by.get(b) || {brand:b, courses:0, lessons:0};
    e.courses++; e.lessons += c.lessons.length; by.set(b, e);
  }
  return [...by.values()].sort((a, b) => b.courses - a.courses || b.lessons - a.lessons).slice(0, 3).map(e => e.brand);
}

export default function Home() {
  useStore();
  const [picking, setPicking] = useState(false), [help, setHelp] = useState(false);
  const path = currentPath(), list = pathCourses(path), stacks = topStacks(path, list);
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
      <div className="path-top">
        <AsciiWave className="path-wave"/>
        <div className="tabs" role="group" aria-label={t('Learning path')}>
          {paths().map(p => <button key={p.id} className="tab" aria-pressed={p.id === path.id} onClick={() => choose(p.id)}>{p.short}</button>)}
        </div>
        <header className="path-head">
          <div className="path-intro">
            {path.logo && <span className="path-logo"><img src={path.logo.src} alt={path.logo.alt}/></span>}
            <h1>{path.title}</h1>
            {path.description && <p className="lede">{path.description}</p>}
            {stacks.length > 0 && (
              <ul className="stacks" aria-label={t('Top tech stacks')}>
                {stacks.map(b => <li key={b.name}><TechMark brand={b}/>{t(b.name)}</li>)}
              </ul>
            )}
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
      </div>
      <h2 className="stream-title">{list.length === 1 ? t('{n} course', {n:list.length}) : t('{n} courses', {n:list.length})}</h2>
      {list.length
        ? <ol className="stream">{list.map(c => <Course key={c.slug} course={c}/>)}</ol>
        : <p className="meta">{t('No courses in your custom path yet. Use {edit} to pick some.', {edit:<strong>{t('Edit courses')}</strong>})}</p>}
      <footer className="home-foot">
        {__COMMIT__ === 'dev' ? <span className="commit">dev</span>
          : <a className="commit" href={`https://github.com/Maaboudoufu/nagare/commit/${__COMMIT__}`} target="_blank" rel="noopener noreferrer"
               title={t('Version')}>{__COMMIT__.slice(0, 7)}</a>}
        <button type="button" onClick={() => setHelp(true)}><Icon name="keyboard"/>{t('Keyboard shortcuts')}</button>
        <span className="home-foot-end">{t('Found a bug or have an idea?')}</span>
        <a href="https://github.com/Maaboudoufu/nagare/issues" target="_blank" rel="noopener noreferrer">
          <BrandIcon name="github"/>{t('Open an issue')}<Icon name="arrow-up-right"/>
        </a>
      </footer>
      {picking && <CustomPicker onClose={closePicker}/>}
      {help && <Shortcuts onClose={() => setHelp(false)}/>}
    </Page>
  );
}
