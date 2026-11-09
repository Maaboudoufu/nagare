/* Learning paths: All, the curated paths, and your Custom pick. */
import {SHORT_NAMES} from './constants.js';
import {t} from './lib/i18n.js';
import {store} from './store.js';

export function paths() {
  return [
    {id:'all', short:t('All courses'), title:t('All courses')},
    ...store.catalog.paths.map(p => ({id:p.slug, short:SHORT_NAMES[p.slug] ? t(SHORT_NAMES[p.slug]) : p.title, title:p.title, description:p.description, courses:p.courses})),
    {id:'custom', short:t('Custom'), title:t('Custom path'), description:t('Your own pick of courses.')},
  ];
}

export function currentPath() {
  const id = store.progress['app:path']?.id, all = paths();
  return all.find(p => p.id === id) || all.find(p => p.id === 'devops-python-golang') || all[0];
}

export function pathCourses(p) {
  const all = store.catalog.courses;
  if (p.id === 'all') return all;
  if (p.id === 'custom') {
    const picked = new Set(store.progress['app:path']?.custom || []);
    return all.filter(c => picked.has(c.slug));  // custom keeps the "All" order
  }
  return p.courses.map(s => all.find(c => c.slug === s)).filter(Boolean);
}
