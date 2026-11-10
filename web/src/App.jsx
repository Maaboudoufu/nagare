import {Suspense, lazy, useEffect} from 'react';
import {store, usePath, useStore} from './store.js';
import Achievements from './components/Achievements.jsx';
import Admin from './components/Admin.jsx';
import Leaderboard from './components/Leaderboard.jsx';
import Home from './components/Home.jsx';
import Profile from './components/Profile.jsx';
import Settings from './components/Settings.jsx';
import Toasts from './components/Toasts.jsx';

// Lessons bring the editor and the markdown renderer: their own chunk, so the other pages load without them.
const loadCourseView = () => import('./components/CourseView.jsx');
const CourseView = lazy(loadCourseView);
const PAGES = {profile:Profile, settings:Settings, achievements:Achievements, leaderboard:Leaderboard, admin:Admin};

function Route() {
  const [, section, slug, uuid] = usePath().split('/');  // /learn/{slug}/{uuid}
  const Page = PAGES[section];
  if (Page) return <Page/>;
  if (section === 'u' && slug) return <Profile key={slug} id={slug}/>;  // /u/{member id}
  if (section === 'learn' && store.catalog.courses.some(c => c.slug === slug)) return <CourseView slug={slug} uuid={uuid}/>;
  return <Home/>;
}

export default function App() {
  useStore();
  useEffect(() => { loadCourseView(); }, []);  // fetched in the background, so the first lesson opens at once
  return <><Suspense><Route/></Suspense><Toasts/></>;
}
