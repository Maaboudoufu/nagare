/* UI languages. The English text is the key: t('Run') shows the Japanese from ja.json, or the English as-is.
   {name} placeholders take strings, numbers or React elements, so each language can order them its own way.
   Keep keys plain string literals (t("...") style calls, or N_ for text stored in data), so tools/check_i18n.py can find them. */
import {Fragment, createElement} from 'react';
import JA from './ja.json';
import {bump, save, store} from '../store.js';

const DICTS = {ja:JA};
export const LANGS = [['en', 'English'], ['ja', '日本語']];  // with only one, the switchers hide themselves
export const N_ = s => s;  // marks text kept in data structures, translated where it's shown with t()

function stored() {
  try { return localStorage.getItem('lang'); } catch { return null; }
}
export function lang() {
  const l = store.progress['app:settings']?.lang || stored() || (navigator.language?.startsWith('ja') ? 'ja' : 'en');
  return DICTS[l] || l === 'en' ? l : 'en';
}
export const locale = () => lang() === 'ja' ? 'ja-JP' : undefined;

export function setLang(l) {
  try { localStorage.setItem('lang', l); } catch { /* private mode: the saved setting still works once signed in */ }
  document.documentElement.lang = l;
  localizeCatalog();
  if (store.catalog) save('app:settings', {lang:l});
  else bump();
}

export function t(key, vars) {
  const s = DICTS[lang()]?.[key] ?? key;
  if (!vars) return s;
  const parts = s.split(/\{(\w+)\}/);
  const out = parts.map((p, i) => i % 2 ? vars[p] ?? `{${p}}` : p);
  return out.some(p => p !== null && typeof p === 'object')
    ? out.map((p, i) => createElement(Fragment, {key:i}, p))
    : out.join('');
}

/* Translated course content, per language: courses/<lang>/index.json lists the translated courses
   ({courses: {slug: {title, description}}}), and courses/<lang>/<slug>.json holds each one's lesson text. */
const content = {};
export async function loadContent() {
  await Promise.all(LANGS.filter(([code]) => code !== 'en').map(([code]) =>
    fetch(`/courses/${code}/index.json`).then(r => r.ok ? r.json() : null).then(ix => { if (ix) content[code] = ix; }, () => {})));
  localizeCatalog();
}
export const isTranslated = slug => !!content[lang()]?.courses?.[slug];

// Course titles and descriptions in the catalog (Home, profile) follow the language; the English is kept to switch back.
function localizeCatalog() {
  for (const c of store.catalog?.courses || []) {
    c.en ??= {title:c.title, description:c.description};
    const tr = content[lang()]?.courses?.[c.slug];
    c.title = tr?.title ?? c.en.title;
    c.description = tr?.description ?? c.en.description;
  }
}

// Share of all lessons available in a language (the interface itself is fully translated).
export function contentPct(code) {
  const all = store.catalog?.courses || [], total = all.reduce((n, c) => n + c.lessons.length, 0);
  const done = all.filter(c => content[code]?.courses?.[c.slug]).reduce((n, c) => n + c.lessons.length, 0);
  return total ? Math.round(100 * done / total) : 0;
}

// A course with a translation laid over it. Quiz answers keep their English value (that's what's saved and graded);
// the translation only changes what's shown (q.labels).
export function localizeCourse(c, tr, code) {
  const out = structuredClone(c);
  out.lang = code;
  out.title = content[code]?.courses?.[c.slug]?.title ?? out.title;
  out.chapters.forEach((ch, i) => {
    ch.title = tr.chapters?.[i] ?? ch.title;
    for (const l of ch.lessons) {
      const tl = tr.lessons?.[l.uuid];
      if (!tl) continue;
      Object.assign(l, {title:tl.title || l.title, readme:tl.readme || l.readme, prompt:tl.prompt ?? l.prompt});
      (l.questions || []).forEach((q, qi) => {
        const tq = tl.questions?.[qi];
        if (tq) { q.question = tq.question; q.labels = tq.answers; }
      });
    }
  });
  return out;
}
