/* Catalog + progress, shared by every component. Saved to the server's progress.json. */
import {useEffect, useState, useSyncExternalStore} from 'react';
import {fx} from './lib/fx.js';
import {isTranslated, lang, localizeCourse} from './lib/i18n.js';

export const post = (url, body) => fetch(url, {method:'POST', body:JSON.stringify(body)}).then(r => {
  if (r.status === 401) location.assign('/signin');  // session ended
  return r.json();
});
export const signOut = () => fetch('/auth/logout', {method:'POST'}).then(() => location.assign('/signin'));
export const pct = (n, total) => total ? Math.round(100 * n / total) : 0;

export const store = {catalog:null, progress:{}, user:null, admin:false, toasts:[], version:0, listeners:new Set()};
const subscribe = fn => (store.listeners.add(fn), () => store.listeners.delete(fn));
export const useStore = () => useSyncExternalStore(subscribe, () => store.version);
export const bump = () => { store.version++; store.listeners.forEach(fn => fn()); };
export const isDone = uuid => !!store.progress[uuid]?.done;

let saving = Promise.resolve();
export function save(key, data) {
  Object.assign(store.progress[key] ??= {}, data);
  bump();
  // One request at a time: the server is threaded, so overlapping saves could land out of order.
  return saving = saving.catch(() => {}).then(() => post('/api/progress', {uuid:key, data})).then(res => {
    if (res.stats) store.progress['app:stats'] = res.stats;
    reward(res.events);
    return res;
  });
}

/* Settings (app:settings) and the profile people fill in (app:profile). */
export const ACCENTS = {blue:'#7AA7FF', violet:'#B8A6EE', teal:'#5CC8BE', green:'#62BE8C', amber:'#E2B66B', rose:'#F08A9C'};
export const settings = () => ({accent:'blue', codeSize:14, toasts:true, photo:true, leaderboard:true, sound:true, volume:60, effects:true,
                                 ...store.progress['app:settings']});
export const profile = () => store.progress['app:profile'] || {};
export function applySettings() {
  const s = settings(), hex = ACCENTS[s.accent] || ACCENTS.blue, n = parseInt(hex.slice(1), 16);
  const root = document.documentElement.style;
  root.setProperty('--accent', hex);
  root.setProperty('--accent-soft', `rgba(${n >> 16},${n >> 8 & 255},${n & 255},.14)`);
  root.setProperty('--code-size', `${s.codeSize}px`);
}

/* XP pop-ups for what the server just awarded: one XP total per save, plus each level-up and achievement. */
let toastId = 0;
export function toast(t) {
  const id = ++toastId;
  store.toasts = [...store.toasts, {id, ...t}];
  bump();
  setTimeout(() => { store.toasts = store.toasts.filter(x => x.id !== id); bump(); }, ['xp', 'note'].includes(t.kind) ? 3500 : 6000);
}
export function reward(events = []) {
  bump();
  if (events.some(e => e.kind === 'level')) fx.level();
  if (events.some(e => e.kind === 'achievement')) fx.achievement();
  if (!events.length || !settings().toasts) return;
  const xp = events.filter(e => e.kind === 'xp');
  if (xp.length) toast({kind:'xp', xp:xp.reduce((n, e) => n + e.xp, 0), first:xp[0], more:xp.length > 1});
  events.filter(e => e.kind !== 'xp').forEach(toast);
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

// A course in the current language: the English course, with its translation laid over it when there is one.
const courseCache = {}, english = {};
export function useCourse(slug) {
  const l = isTranslated(slug) ? lang() : 'en', key = `${slug}:${l}`;
  const [course, setCourse] = useState(courseCache[key]);
  useEffect(() => {
    if (courseCache[key]) return setCourse(courseCache[key]);
    let live = true;
    english[slug] ??= fetch(`/courses/${slug}.json`).then(r => r.json());
    const tr = l === 'en' ? null : fetch(`/courses/${l}/${slug}.json`).then(r => r.ok ? r.json() : null, () => null);
    Promise.all([english[slug], tr]).then(([c, t]) => {
      courseCache[key] = t ? localizeCourse(c, t, l) : c;
      if (live) setCourse(courseCache[key]);
    });
    return () => { live = false; };
  }, [key]);
  return course?.slug === slug ? course : null;
}
