/* Catalog + progress, shared by every component. Saved to the server's progress.json. */
import {useEffect, useState, useSyncExternalStore} from 'react';

export const post = (url, body) => fetch(url, {method:'POST', body:JSON.stringify(body)}).then(r => {
  if (r.status === 401) location.assign('/signin');  // session ended
  return r.json();
});
export const signOut = () => fetch('/auth/logout', {method:'POST'}).then(() => location.assign('/signin'));
export const pct = (n, total) => total ? Math.round(100 * n / total) : 0;

export const store = {catalog:null, progress:{}, user:null, version:0, listeners:new Set()};
const subscribe = fn => (store.listeners.add(fn), () => store.listeners.delete(fn));
export const useStore = () => useSyncExternalStore(subscribe, () => store.version);
const bump = () => { store.version++; store.listeners.forEach(fn => fn()); };
export const isDone = uuid => !!store.progress[uuid]?.done;

let saving = Promise.resolve();
export function save(key, data) {
  Object.assign(store.progress[key] ??= {}, data);
  bump();
  // One request at a time: the server is threaded, so overlapping saves could land out of order.
  return saving = saving.catch(() => {}).then(() => post('/api/progress', {uuid:key, data}));
}
export const markDone = uuid => save(uuid, {done:true});

/* Routing: real paths (/, /learn/{course}/{lesson}), served by the Go gateway. Links are plain <a href>; main.jsx turns
   clicks on app links into navigate() so the page doesn't reload. */
const ROUTE_EVENT = 'app:navigate';
export function navigate(to, {replace = false} = {}) {
  history[replace ? 'replaceState' : 'pushState'](null, '', to);
  if (!replace) window.scrollTo(0, 0);
  dispatchEvent(new Event(ROUTE_EVENT));
}
const onRoute = cb => {
  addEventListener('popstate', cb);
  addEventListener(ROUTE_EVENT, cb);
  return () => { removeEventListener('popstate', cb); removeEventListener(ROUTE_EVENT, cb); };
};
export const usePath = () => useSyncExternalStore(onRoute, () => location.pathname);
export const lessonPath = (slug, uuid) => `/learn/${slug}` + (uuid ? `/${uuid}` : '');

const courseCache = {};
export function useCourse(slug) {
  const [course, setCourse] = useState(courseCache[slug]);
  useEffect(() => {
    if (courseCache[slug]) return setCourse(courseCache[slug]);
    let live = true;
    fetch(`/courses/${slug}.json`).then(r => r.json()).then(c => { courseCache[slug] = c; if (live) setCourse(c); });
    return () => { live = false; };
  }, [slug]);
  return course?.slug === slug ? course : null;
}
