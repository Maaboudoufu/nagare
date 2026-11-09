import {useEffect, useRef} from 'react';
import {save, store, useStore} from '../store.js';
import {Logo} from './ui.jsx';

export default function CustomPicker({onClose}) {
  useStore();
  const dlg = useRef();
  const picked = new Set(store.progress['app:path']?.custom || []);
  useEffect(() => { dlg.current.showModal(); }, []);
  const set = custom => save('app:path', {id:'custom', custom});
  const toggle = slug => set(store.catalog.courses.map(c => c.slug).filter(s => s === slug ? !picked.has(s) : picked.has(s)));
  return (
    <dialog id="picker" ref={dlg} aria-label="Custom path courses" onClose={onClose}>
      <form method="dialog">
        <header className="picker-head"><h2>Custom path</h2><p className="meta">Pick the courses to show. They stay in catalog order.</p></header>
        <ul className="picker-list">
          {store.catalog.courses.map((c, i) => (
            <li key={c.slug}><label className="pick">
              <input type="checkbox" autoFocus={i === 0} checked={picked.has(c.slug)} onChange={() => toggle(c.slug)}/>
              <Logo course={c} size="sm"/><span className="pick-title">{c.title}</span>
              <span className="meta">{c.lessons.length}</span>
            </label></li>
          ))}
        </ul>
        <footer className="picker-foot">
          <span className="meta">{picked.size} of {store.catalog.courses.length} courses</span>
          <button className="btn ghost" type="button" onClick={() => set([])}>Clear all</button>
          <button className="btn primary" value="done">Done</button>
        </footer>
      </form>
    </dialog>
  );
}
