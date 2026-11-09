import {useEffect, useMemo, useRef} from 'react';
import {enhanceProse, lessonHtml} from '../lib/prose.jsx';
import {isDone, lessonPath, useStore} from '../store.js';
import {Icon} from './ui.jsx';

function Pager({to, dir, ic, href}) {
  return to
    ? <a className="icon-btn" href={href(to)} aria-label={`${dir} lesson: ${to.title}`} title={`${dir}: ${to.title}`}><Icon name={ic}/></a>
    : <span className="icon-btn" aria-disabled="true"><Icon name={ic}/></span>;
}

export default function Lesson({course, cur, flat, onMenu, focusRef}) {
  useStore();
  const article = useRef();
  const body = useMemo(() => ({__html:lessonHtml(cur.readme)}), [cur.uuid]);
  useEffect(() => {
    focusRef.current.scrollTop = 0;
    return enhanceProse(article.current);
  }, [cur.uuid]);
  const i = flat.indexOf(cur), prev = flat[i - 1], next = flat[i + 1];
  const ci = course.chapters.findIndex(ch => ch.lessons.includes(cur)), ch = course.chapters[ci];
  const href = l => lessonPath(course.slug, l.uuid);
  return (
    <main id="lesson" tabIndex="-1" ref={focusRef}>
      <header className="lesson-bar">
        <button className="icon-btn menu-btn" id="menu" aria-label="Show lessons" aria-controls="nav" onClick={onMenu}><Icon name="menu"/></button>
        <div className="crumbs">
          <span className="crumb-ch">Chapter {ci + 1} · {ch.title}</span>
          <span className="crumb-pos">Lesson {ch.lessons.indexOf(cur) + 1} of {ch.lessons.length}</span>
        </div>
        {isDone(cur.uuid) && <span className="badge done-badge"><Icon name="circle-check"/>Completed</span>}
        <div className="pager">
          <Pager to={prev} dir="Previous" ic="chevron-left" href={href}/>
          <Pager to={next} dir="Next" ic="chevron-right" href={href}/>
        </div>
      </header>
      {/* key: a fresh <article> per lesson, so React never diffs against the DOM enhanceProse rewrote */}
      <article key={cur.uuid} className="prose" ref={article} dangerouslySetInnerHTML={body}></article>
      <nav className="lesson-foot" aria-label="Previous and next lesson">
        {prev && (
          <a className="foot-link" href={href(prev)}>
            <span className="foot-dir"><Icon name="chevron-left"/>Previous</span><span className="foot-title">{prev.title}</span>
          </a>
        )}
        {next ? (
          <a className="foot-link next" href={href(next)}>
            <span className="foot-dir">Next<Icon name="chevron-right"/></span><span className="foot-title">{next.title}</span>
          </a>
        ) : (
          <a className="foot-link next" href="/">
            <span className="foot-dir">End of course<Icon name="chevron-right"/></span><span className="foot-title">All courses</span>
          </a>
        )}
      </nav>
    </main>
  );
}
