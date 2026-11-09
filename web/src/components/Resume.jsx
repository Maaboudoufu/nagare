/* The home page's "pick up where you left off": the lesson you were on, or the next unfinished one after it. */
import {t} from '../lib/i18n.js';
import {ago} from '../lib/time.js';
import {isDone, lessonPath, pct, store, useCourse} from '../store.js';
import {Icon, Logo, Meter} from './ui.jsx';

function target(list) {
  const last = store.progress['app:last'];
  const course = last && store.catalog.courses.find(c => c.slug === last.slug);
  if (course && !course.lessons.every(isDone)) {
    const from = Math.max(0, course.lessons.indexOf(last.uuid));
    const uuid = course.lessons.slice(from).find(u => !isDone(u)) ?? course.lessons.find(u => !isDone(u));
    return {course, uuid, kind:uuid === last.uuid ? 'resume' : 'next', at:last.at};
  }
  const c = list.find(c => c.lessons.some(isDone) && !c.lessons.every(isDone)) || list.find(c => !c.lessons.every(isDone));
  return c && {course:c, uuid:c.lessons.find(u => !isDone(u)), kind:c.lessons.some(isDone) ? 'next' : 'start'};
}

export default function Resume({list}) {
  const tg = target(list);
  const full = useCourse(tg?.course.slug);  // chapter and lesson titles; also warms the cache for the click
  const href = tg && lessonPath(tg.course.slug, tg.uuid);
  if (!tg) return <div className="resume-gap"></div>;

  const ci = full?.chapters.findIndex(ch => ch.lessons.some(l => l.uuid === tg.uuid)) ?? -1;
  const ch = full?.chapters[ci], lesson = ch?.lessons.find(l => l.uuid === tg.uuid);
  const done = tg.course.lessons.filter(isDone).length, total = tg.course.lessons.length;
  const label = {resume:t('Continue where you left off'), next:t('Up next'), start:t('Start here')}[tg.kind];
  const title = lesson?.title ?? (tg.kind === 'resume' ? store.progress['app:last'].title : '');

  return (
    <a className="resume" href={href}>
      <Logo course={tg.course}/>
      <span className="resume-text">
        <span className="resume-label">{label}{tg.at && <span className="meta"> · {ago(tg.at)}</span>}</span>
        <span className="resume-title">{title || ' '}</span>
        <span className="meta resume-where">
          {tg.course.title}{ch && <> · {t('Chapter {n} · {title}', {n:ci + 1, title:ch.title})}</>}
        </span>
        <span className="resume-progress">
          <Meter n={done} total={total} label={t('Course progress')}/>
          <span className="meta">{t('{n} of {total} lessons done', {n:done, total})} · {pct(done, total)}%</span>
        </span>
      </span>
      <span className="resume-go">
        <span className="btn primary">{tg.kind === 'start' ? t('Start') : t('Resume')}<Icon name="chevron-right"/></span>
      </span>
    </a>
  );
}
