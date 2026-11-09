import {store, usePath, useStore} from './store.js';
import Achievements from './components/Achievements.jsx';
import Admin from './components/Admin.jsx';
import Leaderboard from './components/Leaderboard.jsx';
import CourseView from './components/CourseView.jsx';
import Home from './components/Home.jsx';
import Profile from './components/Profile.jsx';
import Settings from './components/Settings.jsx';
import Toasts from './components/Toasts.jsx';

const PAGES = {profile:Profile, settings:Settings, achievements:Achievements, leaderboard:Leaderboard, admin:Admin};

export default function App() {
  useStore();
  const [, section, slug, uuid] = usePath().split('/');  // /learn/{slug}/{uuid}
  const Page = PAGES[section];
  if (section === 'u' && slug) return <><Profile key={slug} id={slug}/><Toasts/></>;  // /u/{member id}
  return (
    <>
      {Page ? <Page/> : section === 'learn' && store.catalog.courses.some(c => c.slug === slug) ? <CourseView slug={slug} uuid={uuid}/> : <Home/>}
      <Toasts/>
    </>
  );
}
