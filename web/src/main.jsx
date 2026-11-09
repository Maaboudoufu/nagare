import {createRoot} from 'react-dom/client';
import App from './App.jsx';
import SignIn from './components/SignIn.jsx';
import {lang, loadContent} from './lib/i18n.js';
import {applySettings, lessonPath, navigate, reward, save, store} from './store.js';
import './lib/codemirror.js';  // its CSS first, so styles.css can override it
import './styles.css';

document.documentElement.lang = lang();
const root = createRoot(document.getElementById('root'));
const json = url => fetch(url, {cache:'no-store'}).then(r => {
  if (r.status === 401) location.assign('/signin');  // session ended
  return r.json();
});

// Clicks on app links (/, /learn/...) change the route in place instead of reloading the page.
// Everything else (/auth/login, external links, new-tab clicks) behaves like a normal link.
addEventListener('click', e => {
  const a = e.target.closest?.('a[href]');
  if (!a || e.defaultPrevented || e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || a.target || a.origin !== location.origin) return;
  if (!/^\/(learn\/|profile$|settings$|achievements$|leaderboard$|admin$|u\/|$)/.test(a.pathname)) return;
  if (a.pathname === location.pathname && a.hash) return;  // in-page anchors
  e.preventDefault();
  navigate(a.pathname);
});

// The Go gateway already sent signed-out visitors here; /signin needs no app data.
if (location.pathname === '/signin') {
  root.render(<SignIn/>);
} else {
  // Old links were #course/lesson: keep them working.
  const old = location.hash.match(/^#([a-z0-9-]+)(?:\/([\w-]+))?$/);
  if (old) navigate(lessonPath(old[1], old[2]), {replace:true});
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
  Promise.all([json('/auth/me'), json('/courses/index.json'), json(`/api/progress?tz=${encodeURIComponent(tz)}`)]).then(async ([auth, catalog, progress]) => {
    const {'app:events':events, ...rest} = progress;
    store.user = auth.user;
    store.admin = auth.admin;
    store.catalog = catalog;
    store.progress = rest;
    document.documentElement.lang = lang();  // the saved setting wins once it's loaded
    await loadContent();  // translated course titles before the first render
    applySettings();
    root.render(<App/>);
    if (!rest['app:settings']?.tz) save('app:settings', {tz});  // streaks and the activity graph use your days
    reward(events);
  });
}
