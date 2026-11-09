import {store, usePath, useStore} from './store.js';
import CourseView from './components/CourseView.jsx';
import Home from './components/Home.jsx';

export default function App() {
  useStore();
  const [, section, slug, uuid] = usePath().split('/');  // /learn/{slug}/{uuid}
  return section === 'learn' && store.catalog.courses.some(c => c.slug === slug) ? <CourseView slug={slug} uuid={uuid}/> : <Home/>;
}
