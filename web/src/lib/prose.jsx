/* Post-process a lesson's rendered markdown: highlighted code with copy buttons, callouts, safe external links. */
import {marked} from 'marked';
import {createRoot} from 'react-dom/client';
import {CALLOUTS, FENCE_MODES} from '../constants.js';
import {CopyButton} from '../components/ui.jsx';
import CodeMirror from './codemirror.js';

const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;'}[c]));
const iconHtml = name => `<svg class="icon" aria-hidden="true"><use href="/vendor/icons.svg?v=4#${name}"/></svg>`;

// Lesson markdown -> HTML. Videos are written as images (![title](clip.mp4){captions="captions.vtt"}): make them
// video players. The {captions=...} attribute is dropped: those caption files were never published.
const VIDEO = /!\[([^\]]*)\]\(\s*<?([^)\s>]+\.(?:mp4|webm|mov))>?\s*\)(\{[^}]*\})?/gi;
export function lessonHtml(md) {
  const html = marked.parse(md
    .replace(VIDEO, (_, title, src) => `<video class="lesson-video" controls preload="metadata" playsinline src="${esc(src)}" aria-label="${esc(title)}"></video>`)
    .replace(/(!\[[^\]]*\]\([^)]*\))\{[^}]*\}/g, '$1'));
  // Diagrams are linked relative ("courses/diagrams/..."); pages live under /learn/, so make them absolute.
  return html.replaceAll('src="courses/', 'src="/courses/');
}

export function enhanceProse(root) {
  const roots = [];  // a tiny React root per code block for its copy button
  root.querySelectorAll('pre > code').forEach(code => {
    const pre = code.parentElement, text = code.textContent;
    const mode = FENCE_MODES[code.className.match(/language-(\S+)/)?.[1].toLowerCase()];
    pre.classList.add('cm-s-material-darker');
    if (mode) CodeMirror.runMode(text, mode, code);
    const wrap = document.createElement('div');
    wrap.className = 'code-block';
    pre.replaceWith(wrap);
    wrap.append(pre);
    const btn = document.createElement('div');
    wrap.append(btn);
    const r = createRoot(btn);
    r.render(<CopyButton text={text}/>);
    roots.push(r);
  });
  root.querySelectorAll('blockquote').forEach(bq => {
    const m = bq.innerHTML.match(/\[!(\w+)\]\s*/);
    const kind = m?.[1].toLowerCase();
    const [ic, label, tone] = CALLOUTS[kind] || (m ? ['message-square', kind[0].toUpperCase() + kind.slice(1), 'person'] : [null, '', '']);
    if (m) {
      bq.innerHTML = bq.innerHTML.replace(m[0], '');
      const first = bq.querySelector('p');
      if (first && !first.textContent.trim()) first.remove();
    }
    bq.className = `callout ${tone}`;
    if (label) bq.insertAdjacentHTML('afterbegin', `<p class="callout-title">${iconHtml(ic)}${esc(label)}</p>`);
  });
  // Lessons' OS tabs mark headings like "[!linux][!windows] Linux / WSL": the text already says which OS.
  root.querySelectorAll('h1, h2, h3, h4').forEach(h => { if (/\[!\w+\]/.test(h.innerHTML)) h.innerHTML = h.innerHTML.replace(/\[!\w+\]\s*/g, ''); });
  root.querySelectorAll('a[href^="http"]').forEach(a => { a.target = '_blank'; a.rel = 'noopener'; });
  root.querySelectorAll('li > input[type=checkbox]').forEach(cb => cb.setAttribute('aria-label', cb.parentElement.textContent.trim().slice(0, 120)));
  // Media that isn't on this server (e.g. media/ not downloaded yet): say what it was instead of a broken icon.
  root.querySelectorAll('img, video').forEach(el => el.addEventListener('error', () => {
    const p = document.createElement('p'), title = el.alt || el.getAttribute('aria-label');
    p.className = 'img-missing';
    p.innerHTML = `${iconHtml('info')}<span>${el.tagName === 'VIDEO' ? 'Video' : 'Image'} not available${title ? `: ${esc(title)}` : ''}</span>`;
    el.replaceWith(p);
  }, {once:true}));
  return () => roots.forEach(r => setTimeout(() => r.unmount()));  // deferred: React can't unmount a root mid-render
}
