import {useEffect, useRef, useState} from 'react';
import {TYPES} from '../constants.js';
import {isDone, lessonPath, store, useStore} from '../store.js';
import {Icon, Logo, Meter} from './ui.jsx';

const openChapters = new Set();  // chapters you expanded, remembered while the page is open

export default function Sidebar({course, cur, flat}) {
  useStore();
  const [, rerender] = useState(0);
  const ref = useRef();
  useEffect(() => { ref.current.querySelector('[aria-current]')?.scrollIntoView({block:'nearest'}); }, [cur.uuid]);
  const done = flat.filter(l => isDone(l.uuid)).length;
  const curCh = course.chapters.findIndex(ch => ch.lessons.includes(cur));
  const meta = store.catalog.courses.find(c => c.slug === course.slug);
  return (
    <nav id="nav" aria-label="Course lessons" ref={ref}>
      <div className="nav-head">
        <a className="back" href="/"><Icon name="arrow-left"/>All courses</a>
        <h2 className="course-title"><Logo course={meta} size="sm"/><span>{course.title}</span></h2>
        <Meter n={done} total={flat.length} label="Course progress"/>
        <p className="meta">{done} of {flat.length} lessons complete</p>
      </div>
      <div className="chapters">
        {course.chapters.map((ch, ci) => {
          const d = ch.lessons.filter(l => isDone(l.uuid)).length, key = course.slug + ci;
          return (
            <details key={key} className="chapter" open={ci === curCh || openChapters.has(key)}
                     onToggle={e => { e.currentTarget.open ? openChapters.add(key) : openChapters.delete(key); rerender(n => n + 1); }}>
              <summary>
                <span className="ch-num">{ci + 1}</span><span className="ch-title">{ch.title}</span>
                <span className={'ch-count' + (d === ch.lessons.length ? ' all' : '')}>{d}/{ch.lessons.length}</span>
                <Icon name="chevron-down" cls="chev"/>
              </summary>
              <ol className="lessons">
                {ch.lessons.map(l => {
                  const [ic, name] = TYPES[l.type] || ['book-open', 'Lesson'], ok = isDone(l.uuid);
                  return (
                    <li key={l.uuid}><a href={lessonPath(course.slug, l.uuid)} className={ok ? 'done' : ''} aria-current={l === cur ? 'page' : undefined}>
                      <Icon name={ok ? 'circle-check' : 'circle'} cls="status"/>{ok && <span className="sr">Completed: </span>}
                      <span className="l-title">{l.title}</span>
                      <span className="l-type" title={name}><Icon name={ic}/><span className="sr">, {name}</span></span>
                    </a></li>
                  );
                })}
              </ol>
            </details>
          );
        })}
      </div>
    </nav>
  );
}
