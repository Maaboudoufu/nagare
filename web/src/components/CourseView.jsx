import {useEffect, useMemo, useRef, useState} from 'react';
import {t} from '../lib/i18n.js';
import {useShortcut} from '../lib/keys.js';
import {isDone, lessonPath, navigate, save, useCourse} from '../store.js';
import Lesson from './Lesson.jsx';
import Shortcuts from './Shortcuts.jsx';
import Sidebar from './Sidebar.jsx';
import Workspace from './workspaces/Workspace.jsx';

export default function CourseView({slug, uuid}) {
  const course = useCourse(slug);
  const [navOpen, setNavOpen] = useState(false);
  const [help, setHelp] = useState(false);
  useShortcut('help', () => setHelp(h => !h));
  const lessonRef = useRef(), mounted = useRef(false);
  const flat = useMemo(() => course ? course.chapters.flatMap(ch => ch.lessons) : [], [course]);
  const cur = course && (flat.find(l => l.uuid === uuid) || flat.find(l => !isDone(l.uuid)) || flat[0]);

  useEffect(() => {
    if (!cur) return;
    if (cur.uuid !== uuid) navigate(lessonPath(slug, cur.uuid), {replace:true});
    document.title = `${cur.title} · ${course.title}`;
    setNavOpen(false);
    save('app:last', {slug, uuid:cur.uuid, title:cur.title, course:course.title});
    if (mounted.current) lessonRef.current?.focus({preventScroll:true});  // move focus to the new lesson, not on first load
    mounted.current = true;
  }, [cur?.uuid]);

  useEffect(() => {
    if (!navOpen) return;
    setTimeout(() => document.querySelector('#nav [aria-current]')?.focus(), 50);
    const onKey = e => { if (e.key === 'Escape') { setNavOpen(false); document.getElementById('menu')?.focus(); } };
    addEventListener('keydown', onKey);
    return () => removeEventListener('keydown', onKey);
  }, [navOpen]);

  if (!cur) return null;
  return (
    <>
      <a className="skip" href="#lesson" onClick={e => { e.preventDefault(); lessonRef.current.focus(); }}>{t('Skip to lesson')}</a>
      <div className={'app' + (navOpen ? ' nav-open' : '')}>
        <Sidebar course={course} cur={cur} flat={flat}/>
        <Lesson course={course} cur={cur} flat={flat} focusRef={lessonRef} onMenu={() => setNavOpen(true)}/>
        <Workspace key={cur.uuid} lesson={cur} courseSlug={slug}/>
      </div>
      {navOpen && <div className="scrim" onClick={() => setNavOpen(false)}></div>}
      {help && <Shortcuts onClose={() => setHelp(false)}/>}
    </>
  );
}
