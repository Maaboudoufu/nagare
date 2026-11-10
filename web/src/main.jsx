import {createRoot} from 'react-dom/client';
import 'codemirror/lib/codemirror.css';  // before styles.css, which restyles the editor
import 'codemirror/addon/dialog/dialog.css';
import './styles.css';
import App from './App.jsx';
import SignIn from './components/SignIn.jsx';
import {BrandMark} from './components/ui.jsx';
import {lang, loadContent, t} from './lib/i18n.js';
import {applySettings, get, lessonPath, navigate, reward, save, store} from './store.js';

document.documentElement.lang = lang();
const root = createRoot(document.getElementById('root'));

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

const LoadError = () => (
  <main className="center">
    <BrandMark className="center-mark"/>
    <h1>{t('Can\'t reach the server')}</h1>
    <p className="meta">{t('Check that it\'s running and that you\'re online, then try again.')}</p>
    <button className="btn primary" onClick={() => location.reload()}>{t('Try again')}</button>
  </main>
);

async function start() {
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const [auth, catalog, progress] = await Promise.all([get('/auth/me'), get('/courses/index.json'), get(`/api/progress?tz=${encodeURIComponent(tz)}`)]);
  if (!auth || !catalog || !progress) throw new Error('the app\'s data didn\'t load');
  const {'app:events':events, ...rest} = progress;
  Object.assign(store, {user:auth.user, admin:auth.admin, catalog, progress:rest});
  document.documentElement.lang = lang();  // the saved setting wins once it's loaded
  await loadContent();  // translated course titles before the first render
  applySettings();
  root.render(<App/>);
  if (!rest['app:settings']?.tz) save('app:settings', {tz});  // streaks and the activity graph use your days
  reward(events);
}

// The Go gateway already sent signed-out visitors here; /signin needs no app data.
if (location.pathname === '/signin') {
  root.render(<SignIn/>);
} else {
  // Old links were #course/lesson: keep them working.
  const old = location.hash.match(/^#([a-z0-9-]+)(?:\/([\w-]+))?$/);
  if (old) navigate(lessonPath(old[1], old[2]), {replace:true});
  start().catch(() => root.render(<LoadError/>));
}
