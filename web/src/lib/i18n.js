/* UI languages. The English text is the key: t('Run') shows the Japanese from ja.json, or the English as-is.
   {name} placeholders take strings, numbers or React elements, so each language can order them its own way.
   Keep keys plain string literals (t("...") style calls, or N_ for text stored in data), so tools/check_i18n.py can find them. */
import {Fragment, createElement} from 'react';
// Japanese is switched off for now. To bring it back, uncomment the three marked spots below.
// import JA from './ja.json';
import {bump, save, store} from '../store.js';

const DICTS = {/* ja:JA */};
export const LANGS = [['en', 'English'] /* , ['ja', '日本語'] */];  // one language: the switchers hide themselves
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
