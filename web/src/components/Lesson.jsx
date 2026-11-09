import {useEffect, useMemo, useRef} from 'react';
import {t} from '../lib/i18n.js';
import {enhanceProse, lessonHtml} from '../lib/prose.jsx';
import {useShortcut} from '../lib/keys.js';
import {isDone, lessonPath, navigate, useStore} from '../store.js';
import {Icon} from './ui.jsx';

function Pager({to, label, tip, ic, href}) {
  return to
    ? <a className="icon-btn" href={href(to)} aria-label={label(to.title)} title={tip(to.title)}><Icon name={ic}/></a>
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
  useShortcut('next', next && (() => navigate(href(next))));  // used by Mod+Enter after a pass (lib/keys.js)
  return (
    <main id="lesson" tabIndex="-1" ref={focusRef}>
      <header className="lesson-bar">
        <button className="icon-btn menu-btn" id="menu" aria-label={t('Show lessons')} aria-controls="nav" onClick={onMenu}><Icon name="menu"/></button>
        <div className="crumbs">
          <span className="crumb-ch">{t('Chapter {n} · {title}', {n:ci + 1, title:ch.title})}</span>
          <span className="crumb-pos">{t('Lesson {n} of {total}', {n:ch.lessons.indexOf(cur) + 1, total:ch.lessons.length})}</span>
        </div>
        {isDone(cur.uuid) && <span className="badge done-badge"><Icon name="circle-check"/>{t('Completed')}</span>}
        <div className="pager">
          <Pager to={prev} label={title => t('Previous lesson: {title}', {title})} tip={title => t('Previous: {title}', {title})} ic="chevron-left" href={href}/>
          <Pager to={next} label={title => t('Next lesson: {title}', {title})} tip={title => t('Next: {title}', {title})} ic="chevron-right" href={href}/>
        </div>
      </header>
      {/* key: a fresh <article> per lesson, so React never diffs against the DOM enhanceProse rewrote */}
      <article key={cur.uuid} lang={course.lang || 'en'} className="prose" ref={article} dangerouslySetInnerHTML={body}></article>
      <nav className="lesson-foot" aria-label={t('Previous and next lesson')}>
        {prev && (
          <a className="foot-link" href={href(prev)}>
            <span className="foot-dir"><Icon name="chevron-left"/>{t('Previous')}</span><span className="foot-title">{prev.title}</span>
          </a>
        )}
        {next ? (
          <a className="foot-link next" href={href(next)}>
            <span className="foot-dir">{t('Next')}<Icon name="chevron-right"/></span><span className="foot-title">{next.title}</span>
          </a>
        ) : (
          <a className="foot-link next" href="/">
            <span className="foot-dir">{t('End of course')}<Icon name="chevron-right"/></span><span className="foot-title">{t('All courses')}</span>
          </a>
        )}
      </nav>
      <p className="kbd-caption">{t('Press {key} for keyboard shortcuts', {key:<kbd>?</kbd>})}</p>
    </main>
  );
}
